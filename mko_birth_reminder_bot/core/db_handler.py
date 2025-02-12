import sqlite3
from typing import List, Tuple, Optional, Any, Dict, Literal, Union
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from .config import CONFIG
from .utils import validate_data, rows_to_dict_list
import logging
from .errors import *

logger = logging.getLogger(__name__)

def db_connect() -> sqlite3.Connection:
    """
    Establishes a connection to the SQLite database.

    Returns:
        sqlite3.Connection: Database connection.
    """
    try:
        db_settings = CONFIG.DATABASE
        db_file = Path(db_settings.path, db_settings.db_file)
        db_con = sqlite3.connect(db_file, check_same_thread=False)
        db_con.row_factory = sqlite3.Row

        # Allows using the connection in multiple threads
        db_con.execute("PRAGMA journal_mode=WAL;")  # Improves multithreaded access
        db_con.execute("PRAGMA synchronous=NORMAL;")
        db_con.execute("PRAGMA foreign_keys=ON;")
        logging.info("Database initialized.")

        return db_con
    except sqlite3.Error as e:
        logger.error(f"Database connection error: {e}")
        raise e


# Global database connection
DB_CONNECTION = db_connect()


class DBHandler:
    """
    Class for working with the SQLite database.
    """
    DATA_TO_SQL_PARAMS = {
        'if_exists': 'append',
        'index': False,
        'method': 'multi',
    }

    def __init__(self):
        """
        Initializes a DBHandler instance.
        """
        self.db_settings = CONFIG.DATABASE
        self.logger = logger
        self.db_con = DB_CONNECTION

    def perform_query(
            self,
            query: str,
            term: Optional[Tuple | List] = tuple(),
            fetch: Literal['all', 'one', None] = None,
            raise_exceptions: bool = False
    ) -> Optional[Union[List[sqlite3.Row], sqlite3.Row]]:
        """
        Executes an SQL query.

        Args:
            query (str): SQL query.
            term (Optional[Tuple | List]): Query parameters.
            fetch (Literal['all', 'one', None]): Type of result to return.
            raise_exceptions (bool): Whether to raise exceptions on errors.

        Returns:
            Optional[Union[List[sqlite3.Row], sqlite3.Row]]: Query results.
        """
        cursor = self.db_con.cursor()
        try:
            cursor.execute(query, term)
            match fetch:
                case "all":
                    result = cursor.fetchall()
                case "one":
                    result = cursor.fetchone()
                case _:
                    result = None
            self.db_con.commit()
            self.logger.debug(f"Query executed: {query}, parameters: {term}, result: {result}")
            return result
        except sqlite3.Error as err:
            self.logger.error(f"Query execution error: '{query}' with parameters {term}. Error: {err}")
            if raise_exceptions:
                raise
        finally:
            cursor.close()

    def create_table(self, tbl_name: str, columns: Dict[str, str]):
        """
        Creates a table with the specified columns.

        Args:
            tbl_name (str): Table name.
            columns (Dict[str, str]): Dictionary where keys are column names and values are their data types.
        """
        column_definitions = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {tbl_name} ({column_definitions});"
        self.perform_query(query)

    def drop_table(self, table_name: str) -> bool:
        """
        Drops a table from the database.

        Args:
            table_name (str): Table name.

        Returns:
            bool: True if the table was successfully deleted, otherwise False.
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        if self.perform_query(query):
            self.logger.debug(f"Table '{table_name}' successfully dropped.")
            return True
        return False

    def close(self):
        """
        Closes the database connection.
        """
        if self.db_con:
            try:
                self.db_con.close()
            except sqlite3.Error as e:
                self.logger.error(f"Error closing the connection: {e}")
            else:
                self.logger.info("Connection successfully closed.")

    def __enter__(self):
        """
        Supports the context manager protocol.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Closes the connection when exiting the context.
        """
        # self.close()
        pass


class TGUserData(DBHandler):
    """
    Class for handling user data.

    Attributes:
        columns (dict): Database column definitions.
        column_names (list): List of column names.
        date_column (str): Name of the date column.
        date_format (str): Date format string.
        default_notice (Any): Default notice value.
        _data_tbl_name (str): Internal table name.
        notice_before_days_column (str): Column name for custom notices.
    """

    def __init__(self, tg_user_id: Optional[int]):
        """
        Initializes TGUserData.

        Args:
            tg_user_id (Optional[int]): Telegram user ID.
        """
        super().__init__()
        self.columns = self.db_settings.columns
        self.column_names = list(self.columns.keys())
        self.date_column = self.db_settings.date_column
        self.date_format = self.db_settings.date_format  # %d/%m/%y
        self.default_notice = self.db_settings.default_notice
        self._data_tbl_name = None
        self.notice_before_days_column = self.db_settings.custom_notice_column

        if tg_user_id:
            self.data_tbl_name = tg_user_id

    @property
    def data_tbl_name(self) -> str:
        """Gets the data table name."""
        return self._data_tbl_name

    @data_tbl_name.setter
    def data_tbl_name(self, tg_user_id: int) -> None:
        """
        Sets the data table name.

        Args:
            tg_user_id (int): Telegram user ID.
        """
        try:
            self._data_tbl_name = 'id_' + str(tg_user_id)
        except TypeError as e:
            self.logger.error(f"Parameter tg_user_id should be integer. {e}")

    def add_data(self, prepared_data: pd.DataFrame, sql_loader_settings: Optional[Dict[str, Any]] = None) -> int:
        """
        Adds data to the table.

        Args:
            prepared_data (pd.DataFrame): Data to be added.
            sql_loader_settings (Optional[Dict[str, Any]]): SQL loading settings.

        Returns:
            int: Number of records added.
        """
        if sql_loader_settings is None:
            sql_loader_settings = self.DATA_TO_SQL_PARAMS
        prepared_data.to_sql(
            **sql_loader_settings,
            name=self._data_tbl_name,
            con=self.db_con
        )
        self.logger.info(f"Added {prepared_data.shape[0]} records.")
        return prepared_data.shape[0]

    def flush_data(self) -> None:
        """Flushes data by dropping and recreating the table."""
        self.drop_table(self._data_tbl_name)
        self.create_table(self._data_tbl_name, self.columns)

    def add_record(self, **data) -> None:
        """
        Inserts a new record into the database.

        Parameters:
        ----------
        data : dict
            Key-value pairs representing column names and their corresponding values
            to be inserted into the database.

        Returns:
        -------
        None

        Behavior:
        --------
        - Validates the provided data using the `validate_data` function.
        - Ensures the mandatory date column is provided in the data.
        - Dynamically constructs and executes an SQL INSERT query.
        - Logs a warning if the mandatory date column is missing.
        - Logs any errors that occur during query execution.

        Raises:
        ------
        None, but logs any errors internally.
        """
        if self.date_column not in data:
            # Log a warning if the mandatory date column is missing
            self.logger.warning(f"No date column found. '{self.date_column}' is mandatory.")
            return

        try:
            # Validate the data
            valid_data = validate_data(self.column_names, self.date_column, self.date_format, data)

            if valid_data:
                # Construct the SQL INSERT query dynamically
                key_str = ', '.join(valid_data.keys())
                q_str = ', '.join(['?'] * len(valid_data.keys()))
                values = tuple(valid_data.values())
                query = f"INSERT INTO {self._data_tbl_name} ({key_str}) VALUES ({q_str})"

                # Execute the query
                self.perform_query(query, values)
        except Exception as e:
            # Log any errors that occur
            self.logger.error(f"Error inserting record: {e}")

    def count_records(self) -> int:
        query = f"""SELECT COUNT(*) FROM {self._data_tbl_name}"""
        count = self.perform_query(query, fetch='one', raise_exceptions=False)
        return count[0] if isinstance(count, list | tuple | sqlite3.Row) else 0

    def get_all_records(self) -> pd.DataFrame:
        """
        Retrieves all records from the user data table.

        Returns:
            pd.DataFrame: Data from the table.
        """
        try:
            query = f"""SELECT * FROM {self._data_tbl_name}"""
            return pd.read_sql(query, self.db_con)
        except Exception as e:
            self.logger.warning(f"Failed to retrieve data from '{self._data_tbl_name}', due to error: '{e}' ")
            return pd.DataFrame()

    def get_record_by_id(self, record_id: int) -> Optional[Union[List[sqlite3.Row], sqlite3.Row]]:
        """
        Retrieves a record from the user data table by ID.

        Args:
            record_id (int): Record ID.

        Returns:
            Optional[Union[List[sqlite3.Row], sqlite3.Row]]: Retrieved record(s) or None if invalid.
        """
        try:
            row_id = int(record_id)
            query = f"""SELECT * FROM {self._data_tbl_name} WHERE id = ?"""
            return self.perform_query(query, (row_id,), fetch='one')
        except ValueError:
            self.logger.warning(f"Invalid record ID: '{record_id}', ID must be an integer.")
            return None

    def update_record_by_id(self, record_id: int, **fields) -> None:
        """
        Validates the input and updates a record in the user data table by its ID.

        Args:
            record_id (int): Record ID.
            **fields: Fields to update.
        """
        try:
            # Validate the input fields
            validated_data = validate_data(self.column_names, self.date_column, self.date_format, fields)

            # Construct the field assignment part of the SQL query dynamically
            fields_assignment = ', '.join([f"{key} = ?" for key in validated_data.keys()])
            values = list(validated_data.values())
            values.append(record_id)  # Append the record ID as the last parameter

            query = f"UPDATE {self._data_tbl_name} SET {fields_assignment} WHERE id = ?"
            self.perform_query(query, values, fetch=None)
        except (ValueError, AttributeError) as e:
            self.logger.error(f"Error updating record with ID {record_id}: {e}")

    def del_record_by_id(self, record_id: int) -> None:
        """
        Deletes a record from the database table by its ID.

        Args:
            record_id (int): Record ID.

        Raises:
            WrongInput: If record_id is not an integer.
        """
        try:
            # Ensure the record ID is a valid integer
            record_id = int(record_id)
        except ValueError as e:
            self.logger.error(f"Invalid record ID: must be an integer. Error: {e}, Provided: {record_id}")
            raise WrongInput(f"Invalid record ID: must be an integer. Provided: {record_id}")
        else:
            try:
                query = f"DELETE FROM {self._data_tbl_name} WHERE id = ?"
                self.perform_query(query, (record_id,), raise_exceptions=True)
                self.logger.info(f"Record with ID {record_id} successfully deleted.")
            except Exception as e:
                self.logger.error(f"Error deleting record with ID {record_id}: {e}")
                raise f"Error deleting record with ID {record_id}"

    def _get_data_in_dates_interval(self, start_date: str, end_date: str) -> Optional[
        Union[List[sqlite3.Row], sqlite3.Row]]:
        """
        Returns data within a date range.

        Args:
            start_date (str): Start date.
            end_date (str): End date.

        Returns:
            Optional[Union[List[sqlite3.Row], sqlite3.Row]]: Retrieved records.
        """
        # Convert input dates to datetime objects
        start_date = datetime.strptime(start_date, self.date_format)
        end_date = datetime.strptime(end_date, self.date_format)
        # Extract month and day
        start_month_day = (start_date.month, start_date.day)
        end_month_day = (end_date.month, end_date.day)
        # SQL query for range selection
        query = f"SELECT {', '.join(self.column_names)} FROM {self._data_tbl_name} WHERE "
        if start_month_day <= end_month_day:
            # Range within a single year
            query += f"strftime('%m-%d', {self.date_column}) BETWEEN ? AND ?"
            params = (
                f"{start_month_day[0]:02d}-{start_month_day[1]:02d}",
                f"{end_month_day[0]:02d}-{end_month_day[1]:02d}",
            )
        else:
            # Range crossing the year boundary
            query += (
                f"(strftime('%m-%d', {self.date_column}) BETWEEN ? AND '12-31' OR "
                f"strftime('%m-%d', {self.date_column}) BETWEEN '01-01' AND ?)"
            )
            params = (
                f"{start_month_day[0]:02d}-{start_month_day[1]:02d}",
                f"{end_month_day[0]:02d}-{end_month_day[1]:02d}",
            )
        """
        #    SELECT * FROM {self._data_tbl_name}
        #    WHERE 
        #        (strftime('%m-%d', DATE({self.date_column})) BETWEEN strftime('%m-%d', ?) AND strftime('%m-%d', ?))
        #        OR 
        #        (strftime('%m-%d', DATE({self.date_column})) < strftime('%m-%d', ?) AND strftime('%m-%d', ?) < strftime('%m-%d', ?))
        #    """
        # (query, (start_date, end_date, end_date, start_date, end_date))
        return self.perform_query(query, params, fetch='all')

    def _get_upcoming_dates(self, notice_period_days: int = 0, date: datetime | None = None) -> Optional[
        Union[List[sqlite3.Row], sqlite3.Row]]:
        """
        Fetch users whose birthdays match their 'notice_period_days' days from the current date.
        :return: List of users with matching birthdays.
        """
        try:
            current_date = date or datetime.now()
            target_date = current_date + timedelta(days=int(notice_period_days))

            target_date_str = target_date.strftime('%m-%d')
        except ValueError as err:
            self.logger.error(f"Invalid value for notice_period_days: {err}")
            return []
        else:
            query = f"""
                    SELECT * FROM {self._data_tbl_name}
                    WHERE strftime('%m-%d', {self.date_column}) = ?
                    """
            return self.perform_query(query, (target_date_str,), fetch='all')

    def _get_upcoming_dates_custom_column(self, date: datetime | None = None):
        """
        Fetch users whose birthdays match their 'notice_before' days from the current date.
        :return: List of users with matching birthdays.
        """

        current_date = date or datetime.now()
        current_date = current_date.strftime('%Y-%m-%d')
        # SQL query with dynamic table and column names
        query = f"""
        SELECT * FROM {self._data_tbl_name}
        WHERE 
            strftime('%m-%d', {self.date_column}) = 
            strftime('%m-%d', DATE(?, '+' || {self.notice_before_days_column} || ' days'))
        """

        return self.perform_query(query, (current_date,), fetch='all')

    def get_default_reminders(self, date: datetime | None = None) -> list:
        default_reminders = []
        for i in self.default_notice:
            if row := self._get_upcoming_dates(notice_period_days=i, date=date):
                default_reminders.extend(rows_to_dict_list(row))
        return default_reminders

    def get_custom_reminders(self, date: datetime | None = None) -> list:
        return rows_to_dict_list(self._get_upcoming_dates_custom_column(date))

    def get_all_reminders(self, date: datetime | None = None) -> dict:
        all_reminders = {}
        reminders = self.get_default_reminders(date) + self.get_custom_reminders(date)
        if reminders:
            all_reminders["header"] = list(reminders[0].keys())
            all_reminders['items'] = list(set(tuple(row.values()) for row in reminders))

        return all_reminders


class TGUsers(DBHandler):
    TABLE_NAME = 'tg_users'
    TABLE_FIELDS = {
        'tg_user_id': 'INTEGER PRIMARY KEY',
        'last_interaction_date': 'TEXT',
        'notify_before_days': 'INTEGER',
    }

    def __init__(self):
        super().__init__()
        self._id_column = 'tg_user_id'

    def _get_all_tg_ids(self):
        """
        Получает все id из таблицы пользователей.
        """
        query = f"""SELECT {self._id_column} FROM {self.TABLE_NAME}"""
        return self.perform_query(query, fetch='all', raise_exceptions=False)

    def iter_ids(self):
        for record in self._get_all_tg_ids():
            yield record['tg_user_id']


class TGUser(DBHandler):
    # TABLE_NAME = 'tg_users'
    # TABLE_FIELDS = {
    #     'tg_user_id': 'INTEGER PRIMARY KEY',
    #     'last_interaction_date': 'TEXT',
    #     'notify_before_days': 'INTEGER',
    # }

    def __init__(self, tg_user_id: int):
        super().__init__()
        self.date_format = self.db_settings.date_format
        self._tg_user_id = int(tg_user_id)
        self._info = self.get_info()
        self.is_exist = False
        if self._info:
            self.is_exist = True
            self._last_interaction_date = self._info['last_interaction_date']
            self._notify_before_days = self._info['notify_before_days']
        else:
            self._last_interaction_date = None
            self._notify_before_days = 0

    @property
    def tg_user_id(self):
        return self._tg_user_id

    @property
    def notify_before_days(self):
        return self._notify_before_days

    @notify_before_days.setter
    def notify_before_days(self, notify_before_days: int):
        try:
            self._notify_before_days = int(notify_before_days)
            self._update_field('notify_before_days', self._notify_before_days)
        except ValueError:
            self.logger.error(f"Неверный формат данных {notify_before_days}. "
                              f"Количество дней должно быть целым числом.")

    @property
    def last_interaction_date(self):
        return self._last_interaction_date

    def _get_field(self, field_name: str) -> Any:
        """
        Извлекает значение указанного поля для пользователя.

        :param field_name: Название столбца, значение которого нужно получить.
        :return: Значение указанного поля или None, если данных нет.
        """
        if field_name not in TGUsers.TABLE_FIELDS:
            self.logger.error(f"Попытка получить недопустимое поле: {field_name}")
            return None

        query = f"SELECT {field_name} FROM {TGUsers.TABLE_NAME} WHERE tg_user_id = ?"
        result = self.perform_query(query, (self._tg_user_id,), fetch='one')
        return result[field_name]

    def _update_field(self, field_name: str, field_value: Any) -> None:
        """
        Обновляет значение поля в базе данных для текущего пользователя.

        :param field_name: Название столбца, который нужно обновить.
        :param field_value: Новое значение для столбца.
        :return: True, если обновление прошло успешно, иначе False.
        """
        if field_name not in TGUsers.TABLE_FIELDS:
            self.logger.error(f"Попытка обновить недопустимое поле: {field_name}")
            return None
        query = f"""UPDATE {TGUsers.TABLE_NAME} SET {field_name} = ? WHERE tg_user_id = ?"""
        return self.perform_query(query, (field_value, self._tg_user_id), fetch=None)

    def update_last_interaction_date(self):
        self._last_interaction_date = datetime.now().strftime(self.date_format)
        self._update_field('last_interaction_date', self._last_interaction_date)

    def add_info(self) -> None:
        """
        Добавляет строку с информацией о пользователе в таблицу пользователей
        и создает пустую таблицу в базе для данных загружаемых пользователем.
       """
        # SQL-запрос для вставки данных
        query = f"""INSERT INTO {TGUsers.TABLE_NAME} 
                     (tg_user_id, last_interaction_date, notify_before_days)
                     VALUES (?, ?, ?)
                """
        self.perform_query(query, (self._tg_user_id, self.last_interaction_date, self.notify_before_days))
        self.add_data_table()

    def get_info(self) -> Optional[Union[List[sqlite3.Row], sqlite3.Row]]:
        """
        Проверяет наличие строки в базе данных по tg_user_id и возвращает эту строку.
        :return: Кортеж с данными строки, если строка найдена. None, если строки нет.
        """
        query = f"SELECT * FROM {TGUsers.TABLE_NAME} WHERE tg_user_id = ?"
        return self.perform_query(query, (self._tg_user_id,), fetch='one')

    def add_data_table(self):
        """
        Добавляет в базу таблицу для загрузки данных пользователя.
       """
        self.create_table(f'id_{str(self._tg_user_id)}', self.db_settings.columns)

    def del_info(self):
        """
        Удаляет запись о пользователе из таблицы пользователей,
         а также удаляет связанную с ним таблицу с данными
       """
        query = f"DELETE FROM {TGUsers.TABLE_NAME} WHERE tg_user_id = ?"
        self.perform_query(query, (self._tg_user_id,), fetch='one')
        self.drop_table(f'id_{str(self._tg_user_id)}')

    def __del__(self):
        self.update_last_interaction_date()
