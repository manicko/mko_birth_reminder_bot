import sqlite3
from typing import List, Tuple, Optional, Any, Dict, Literal, Union
from datetime import datetime
from pathlib import Path

from .config_reader import ConfigReader
from .logger import Logger


class DBWorker:
    DATA_TO_SQL_PARAMS = {
        'if_exists': 'append',
        'index': True,
        'index_label': 'id',
    }

    def __init__(self, config: ConfigReader, logger: Logger):
        self.db_settings = config
        self.logger = logger
        self.db_con = self._db_connect()

        self.db_con.row_factory = sqlite3.Row

    def _db_connect(self):
        """Подключается к базе данных SQLite."""
        try:
            self.db_file = Path(self.db_settings['path'], self.db_settings['db_file'])
            db_con = sqlite3.connect(self.db_file)
            self.logger.info("Инициализация базы данных.")
            return db_con
        except sqlite3.Error as e:
            self.logger.error(f"Не удалось подключиться к базе данных: {e}")
            raise e

    def perform_query(
            self,
            query: str,
            term: Optional[Tuple] = tuple(),
            fetch: Literal['all', 'one', None] = None,
            raise_exceptions: bool = False
    ) -> Optional[Union[List[sqlite3.Row], sqlite3.Row]]:
        """Выполняет SQL-запрос.

        :param query: SQL-запрос.
        :param term: Параметры для запроса.
        :param fetch: Literal['all', 'one', None] - какой тип результата возвращать.
        :param raise_exceptions: Поднимать ли исключения при ошибках.
        :return: Результаты запроса в виде строки или списка строк.
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
            self.logger.info(f"Запрос выполнен: {query}, параметры: {term}, результат: {result}")
            return result
        except sqlite3.Error as err:
            self.logger.error(f"Ошибка при выполнении запроса: '{query}' с параметрами {term}. Ошибка: {err}")
            if raise_exceptions:
                raise
        finally:
            cursor.close()

    def create_table(self, tbl_name: str, columns: Dict[str, str]):
        """Создаёт таблицу с указанными колонками.

        :param tbl_name: Название таблицы.
        :param columns: Словарь, где ключи — названия колонок, значения — их типы.
        """
        column_definitions = ", ".join(f"{col} {dtype}" for col, dtype in columns.items())
        query = f"CREATE TABLE IF NOT EXISTS {tbl_name} ({column_definitions});"
        self.perform_query(query)

    def drop_table(self, table_name: str) -> bool:
        """Удаляет таблицу из базы данных.

        :param table_name: Название таблицы.
        :return: True, если удаление прошло успешно, иначе False.
        """
        query = f"DROP TABLE IF EXISTS {table_name}"
        if self.perform_query(query):
            self.logger.info(f"Таблица '{table_name}' успешно удалена.")
            return True
        return False

    def close(self):
        """Закрывает соединение с базой данных."""
        if self.db_con:
            try:
                self.db_con.close()
            except sqlite3.Error as e:
                self.logger.error(f"Ошибка при закрытии соединения: {e}")
            else:
                self.logger.info("Соединение успешно закрыто.")

    def __enter__(self):
        """Поддержка контекстного менеджера."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Закрытие соединения при выходе из контекста."""
        self.close()


class TGUserData(DBWorker):
    """Класс для работы с данными пользователей."""

    def __init__(self, config: ConfigReader, logger: Logger, data_tbl_name: Optional[str] = None):
        super().__init__(config, logger)
        self.columns = self.db_settings['columns']
        self.column_names = list(self.columns.keys())
        self.date_column = self.db_settings['date_column']
        self.notice_before_days_column = self.db_settings['notice_before_days']
        self.date_format = self.db_settings["date_format"] # %d/%m/%y
        self.data_tbl_name = data_tbl_name

    def get_data_in_dates_interval(self, start_date: str, end_date: str) -> List[Tuple[Any, ...]]:
        """Возвращает данные в диапазоне дат.

        :param start_date: Начальная дата (DD/MM/YYYY).
        :param end_date: Конечная дата (DD/MM/YYYY).
        :return: Список данных.
        """
        # Преобразуем входные даты в объекты datetime
        start_date = datetime.strptime(start_date, self.date_format)
        end_date = datetime.strptime(end_date, self.date_format)
        # Извлекаем месяц и день
        start_month_day = (start_date.month, start_date.day)
        end_month_day = (end_date.month, end_date.day)
        # SQL-запрос для выборки по диапазону
        query = f"SELECT {', '.join(self.column_names)} FROM {self.data_tbl_name} WHERE "
        if start_month_day <= end_month_day:
            # Диапазон в пределах одного года
            query += f"strftime('%m-%d', {self.date_column}) BETWEEN ? AND ?"
            params = (
                f"{start_month_day[0]:02d}-{start_month_day[1]:02d}",
                f"{end_month_day[0]:02d}-{end_month_day[1]:02d}",
            )
        else:
            # Диапазон пересекает границу года
            query += (
                f"(strftime('%m-%d', {self.date_column}) BETWEEN ? AND '12-31' OR "
                f"strftime('%m-%d', {self.date_column}) BETWEEN '01-01' AND ?)"
            )
            params = (
                f"{start_month_day[0]:02d}-{start_month_day[1]:02d}",
                f"{end_month_day[0]:02d}-{end_month_day[1]:02d}",
            )

        return self.perform_query(query, params, fetch='all')

    def get_upcoming_birthdays(self, current_date=None):
        """
        Fetch users whose birthdays match their 'notice_before' days from the current date.

        :param connection: SQLite database connection object.
        :param current_date: Optional, current date as a string in 'YYYY-MM-DD' format. Defaults to today.
        :return: List of users with matching birthdays.
        """
        if current_date is None:
            current_date = datetime.now().strftime(self.date)

        today = datetime.strptime(current_date, self.date_format)
        query = f"""SELECT * FROM {self.data_tbl_name}
                    WHERE 
                  (strftime('%m-%d', {self.date_column}) = strftime('%m-%d', DATE(?, '+' || {self.notice_before_days_column} || ' days')))
                """

        return self.perform_query(query, (current_date,),fetch='all')


    def add_data(self, prepared_data, sql_loader_settings: Optional[Dict[str, Any]] = None) -> int:
        """Добавляет данные в таблицу."""
        if sql_loader_settings is None:
            sql_loader_settings = DBWorker.DATA_TO_SQL_PARAMS
        prepared_data.to_sql(
            **sql_loader_settings,
            name=self.data_tbl_name,
            con=self.db_con
        )
        self.logger.info(f"Добавлено {prepared_data.shape[0]} записей.")
        return prepared_data.shape[0]

    def flush_data(self):
        # TODO: добавить update_full
        pass

    def add_record(self):
        # TODO: добавить update_by_id
        pass

    def update_record_by_id(self, record_id):
        # TODO: добавить update_by_id
        pass

    def del_record_by_id(self, record_id):
        # TODO: добавить update_by_id
        pass


class TGUser(DBWorker):
    TABLE_NAME = 'tg_users'
    TABLE_FIELDS = {
        'tg_user_id': 'INTEGER PRIMARY KEY',
        'last_interaction_date': 'TEXT',
        'notify_before_days': 'INTEGER',
    }

    def __init__(self, config: ConfigReader, logger: Logger, tg_user_id: int):
        super().__init__(config, logger)
        self._tg_user_id = int(tg_user_id)
        self._info = self.get_info()
        if self._info:
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
        if field_name not in TGUser.TABLE_FIELDS:
            self.logger.error(f"Попытка получить недопустимое поле: {field_name}")
            return None

        query = f"SELECT {field_name} FROM {TGUser.TABLE_NAME} WHERE tg_user_id = ?"
        result = self.perform_query(query, (self._tg_user_id,), fetch='one')
        return result[field_name]

    def _update_field(self, field_name: str, field_value: Any) -> None:
        """
        Обновляет значение поля в базе данных для текущего пользователя.

        :param field_name: Название столбца, который нужно обновить.
        :param field_value: Новое значение для столбца.
        :return: True, если обновление прошло успешно, иначе False.
        """
        if field_name not in TGUser.TABLE_FIELDS:
            self.logger.error(f"Попытка обновить недопустимое поле: {field_name}")
            return None
        query = f"""UPDATE {TGUser.TABLE_NAME} SET {field_name} = ? WHERE tg_user_id = ?"""
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
        query = f"""INSERT INTO {TGUser.TABLE_NAME} 
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
        query = f"SELECT * FROM {TGUser.TABLE_NAME} WHERE tg_user_id = ?"
        return self.perform_query(query, (self._tg_user_id,), fetch='one')

    def add_data_table(self):
        """
        Добавляет в базу таблицу для загрузки данных пользователя.
       """
        self.create_table(f'id_{str(self._tg_user_id)}', TGUser.TABLE_FIELDS)

    def del_info(self):
        """
        Удаляет запись о пользователе из таблицы пользователей,
         а также удаляет связанную с ним таблицу с данными
       """
        query = f"DELETE FROM {TGUser.TABLE_NAME} WHERE tg_user_id = ?"
        self.perform_query(query, (self._tg_user_id,), fetch='one')
        self.drop_table(f'id_{str(self._tg_user_id)}')
