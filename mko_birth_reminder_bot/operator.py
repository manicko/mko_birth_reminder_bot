import logging
from mko_birth_reminder_bot.core import *
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


class Operator:
    """
    Class for managing user operations.
    """
    RECORDS_LIMIT = CONFIG.DATABASE.records_limit
    USERS_LIMIT = CONFIG.DATABASE.users_limit

    def __init__(self, user_id: int):
        """
        Initializes the Operator class.

        Args:
            user_id (int): The Telegram user ID.
        """
        self.user_id = int(user_id)
        self.user = TGUser(self.user_id)
        self.user_data = TGUserData(self.user_id)
        self.csv_handler = CSVHandler()
        self.user_init()

        self.records_count = self.user_data.count_records()

    def user_init(self):
        """
        Initializes user data if the user does not exist.
        """
        if not self.user.is_exist:
            self.user.add_info()

    def import_data(self, csv_file: str | Path) -> str:
        """
        Imports data from a CSV file.

        Args:
            csv_file (str | Path): Path to the CSV file.

        Returns:
            str: A success message or an error message if an exception occurs.
        """
        try:

            df = self.csv_handler.read_csv(csv_file=csv_file)
            df = self.csv_handler.prepare_dataframe(df)
            df_count = len(df) # number of rows
            if self.records_count + df_count > Operator.USERS_LIMIT:
                return ("Unable to load records due to the maximum record limit being reached."
                        f"\nThe file contains {df_count} records, and you already have {self.records_count} in the database."
                        f"\nThe allowed maximum is {Operator.USERS_LIMIT}.")
            if df_count > 0:
                self.user_data.add_data(df)
            return f"Data successfully imported. Number of rows: {df_count}."

        except Exception as e:
            return f"Unexpected error occurred while importing the file: {str(e)}"

    def export_data(self) -> str | Path:
        """
        Exports user data to a CSV file.

        Returns:
            Path: The path to the exported CSV file.
        """
        file_name = utils.generate_random_filename()
        df = self.user_data.get_all_records()
        return self.csv_handler.export_to_csv(df, file_name)

    def add_record(self, **data) -> str:
        """
        Adds a new record to the database.

        Args:
            **data: Record data.

        Returns:
            str: A success message or an error message if an exception occurs.
        """
        try:
            if self.records_count + 1 > Operator.USERS_LIMIT:
                return f"Maximum record limit reached: {Operator.USERS_LIMIT}."

            self.user_data.add_record(**data)
            return "Record successfully added."

        except Exception as e:
            return str(e)

    def get_record_by_id(self, record_id: int) -> Optional[Dict[str, Any]]:

        """
        Retrieves a record by its ID.

        Args:
            record_id (int): Record ID.

        Returns:
            Retrieved record or None if not found.
        """
        return self.user_data.get_record_by_id(record_id)

    def update_record_by_id(self, record_id: int, **data) -> str:
        """
        Updates a record by its ID.

        Args:
            record_id (int): Record ID.
            **data: Updated record data.

        Returns:
            str: Success message or error message if an exception occurs.
        """
        try:
            self.user_data.update_record_by_id(record_id=record_id, **data)
            return "Record successfully updated."
        except Exception as e:
            return str(e)

    def delete_record_by_id(self, record_id: int) -> str:
        """
        Deletes a record by its ID.

        Args:
            record_id (int): Record ID.

        Returns:
            str: Success message or error message if an exception occurs.
        """
        try:
            self.user_data.del_record_by_id(record_id=record_id)
            return "Record was successfully deleted."
        except Exception as e:
            return str(e)

    def flush_data(self):
        """
        Clears all user data from the database.
        """
        self.user_data.flush_data()

    def del_info(self):
        """
        Deletes user information and associated records.
        """
        self.user.del_info()

    def remove_tmp_file(self, file: Path) -> None:
        """
        Deletes a temporary file.

        Args:
            file (Path): Path to the file to be deleted.
        """
        self.csv_handler.safe_file_delete(file)
