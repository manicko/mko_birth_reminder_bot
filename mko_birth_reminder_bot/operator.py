import logging
from mko_birth_reminder_bot.core import *
from pathlib import Path
from typing import Optional, Dict,Any
logger = logging.getLogger(__name__)


class Operator:
    """
    Class for managing user operations.
    """

    def __init__(self, user_id: int):
        """
        Initializes the Operator class.

        Args:
            user_id (int): The Telegram user ID.
        """
        self.user_id = int(user_id)
        self.user = TGUser(self.user_id)
        self.user_data = TGUserData(self.user_id)
        self.csv_worker = CSVWorker()
        self.user_init()

    def user_init(self):
        """
        Initializes user data if the user does not exist.
        """
        if not self.user.is_exist:
            self.user.add_info()

    def import_data(self, csv_file: str|Path) -> str:
        """
        Imports data from a CSV file.

        Args:
            csv_file (Path): Path to the CSV file.

        Returns:
            str: Success message or error message if an exception occurs.
        """
        try:
            df = self.csv_worker.read_csv(csv_file=csv_file)
            df = self.csv_worker.prepare_dataframe(df)
            self.user_data.add_data(df)
            return "Data successfully imported."
        except Exception as e:
            return str(e)

    def export_data(self) -> Path:
        """
        Exports user data to a CSV file.

        Returns:
            Path: Path to the exported CSV file.
        """
        file_name = utils.generate_random_filename()
        df = self.user_data.get_all_records()
        return self.csv_worker.export_to_csv(df, file_name)

    def add_record(self, **data) -> str:
        """
        Adds a new record to the database.

        Args:
            **data: Record data.

        Returns:
            str: Success message or error message if an exception occurs.
        """
        try:
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
        self.csv_worker.safe_file_delete(file)
