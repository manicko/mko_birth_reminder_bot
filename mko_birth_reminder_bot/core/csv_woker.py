import logging
from pathlib import Path
from typing import List, Tuple, Optional
import pandas as pd

from .errors import *
from .utils import (get_date, get_text)
from .config_reader import CONFIG


class CSVWorker:
    """
    CSVWorker class provides functionality to read, clean, and export CSV data.
    It includes methods for data validation and text cleaning.
    """

    def __init__(self, keep_files: bool = True) -> None:
        """
        Initialize the CSVWorker with configuration and logger.
        :param keep_files: Boolean to determine if temporary files should be retained.
        """
        self.config = CONFIG
        self.logger = logging.getLogger(__name__)
        self.keep_files = keep_files

        self.data_column_names: List[str] = self._get_columns(self.config.db_settings["columns"])

        self.date_column: str = self.config.db_settings["date_column"]
        self.date_format: str = self.config.db_settings["date_format"]

        self.import_path: Path = Path(self.config.csv_settings["READ_DATA"]["path"])
        self.reader_settings: dict = self.config.csv_settings["READ_DATA"]["from_csv"]

        self.export_path: Path = Path(self.config.csv_settings["EXPORT_DATA"]["path"])
        self.export_settings: dict = self.config.csv_settings["EXPORT_DATA"]["to_csv"]

    def read_csv(self, csv_file: str) -> pd.DataFrame:
        """
        Reads a CSV file into a pandas DataFrame.

        :param csv_file: Name of the CSV file to read.
        :return: DataFrame with the CSV data or raises an exception on failure.
        """
        file_path = Path(csv_file)
        try:
            # Read only the header row to validate column count

            if not file_path.is_file():
                file_path = Path(self.import_path, csv_file)

            first_row = pd.read_csv(file_path, nrows=1, **self.reader_settings)
            actual_columns = len(first_row.columns)
            expected_columns = len(self.data_column_names)

            if actual_columns != expected_columns:
                error_message = (
                    f"Column count mismatch in the uploaded file. "
                    f"\n Expected {expected_columns} columns, but got {actual_columns} columns."
                )
                raise ColumnMismatch(error_message)  # Raised here, not caught by the same try block

            # If column count matches, read the full file
            df = pd.read_csv(filepath_or_buffer=file_path,
                             names=self.data_column_names,
                             **self.reader_settings)
            self.logger.info(f"Successfully read CSV file: {file_path.name}")
            return df

        except FileNotFoundError as e:
            self.logger.error(f"CSV file not found: {csv_file}: {e}")
            raise ReadCSVError(f"CSV file not found")
        except pd.errors.ParserError as e:
            self.logger.error(f"Failed to parse CSV file {file_path.name}: {e}")
            raise ReadCSVError(f"Failed to parse CSV file {file_path.name}: {e}")
        except pd.errors.DataError as e:
            self.logger.error(f"Data error while reading CSV file {csv_file}: {e}")
            raise ReadCSVError(f"Data error while reading CSV file {file_path.name}: {e}")
        except ColumnMismatch as e:
            self.logger.error(f"Column count mismatch in file {file_path.name}: {e}")
            raise ColumnMismatch(str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error occurred while reading {file_path.name}: {e}")
            raise ReadCSVError(f"Unexpected error occurred while reading {file_path.name}: {e}")

    def export_to_csv(self, df: pd.DataFrame, file_name: str) -> Optional[Path]:
        """
        Exports a DataFrame to a CSV file.

        :param df: DataFrame to export.
        :param file_name: Name of the output CSV file.
        :return: Path to the exported CSV file, or None if an error occurred.
        """
        try:
            file = self.export_path / file_name
            file.parent.mkdir(parents=True, exist_ok=True)  # Ensure the directory exists
            df.to_csv(path_or_buf=file, **self.export_settings)
            self.logger.info(f"Data exported successfully to {file}")
            return file
        except Exception as err:
            self.logger.error(f"Failed to export data to CSV: {err}")
            return None

    ####################         data processing            ####################
    @staticmethod
    def _get_columns(columns:dict) -> List[str]:
                return [col_name for col_name, col_type in columns.items() if 'PRIMARY' not in col_type]


    def _clean_date_column(self, dataframe: pd.DataFrame, date_column: str) -> pd.DataFrame:
        """
        Validates and converts dates in the specified column, removing invalid rows.

        :param dataframe: DataFrame containing the data.
        :param date_column: Column name with date values.
        :return: DataFrame with valid date values.
        """
        valid_rows = []
        for _, row in dataframe.iterrows():
            res = get_date(row[date_column])
            if res is None:
                self.logger.warning(f"Invalid date format: {row[date_column]}. Row skipped.")
            else:
                row[date_column] = res.strftime(self.date_format)  # Convert date format
                valid_rows.append(row)
        return pd.DataFrame(valid_rows)

    @staticmethod
    def _clean_text_columns(dataframe: pd.DataFrame, column_names: List[str], date_column: str) -> pd.DataFrame:
        """
        Cleans text data in specified columns.

        :param dataframe: DataFrame containing the data.
        :param column_names: List of all column names.
        :param date_column: Column name with date values.
        :return: DataFrame with cleaned text data.
        """
        for col in column_names:
            if col != date_column:
                dataframe[col] = dataframe[col].astype(str).apply(get_text)
        return dataframe

    def prepare_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Cleans and validates the input DataFrame before exporting or storing.

        :param dataframe: Input DataFrame with raw data.
        :return: Cleaned DataFrame ready for use.
        """
        if len(dataframe.columns) != len(self.data_column_names):
            self.logger.error("Column count mismatch. Data loading aborted.")
            return pd.DataFrame()  # Return an empty DataFrame

        len_raw_data = len(dataframe)
        dataframe.columns = self.data_column_names

        # Step 1: Clean date column
        dataframe = self._clean_date_column(dataframe, self.date_column)

        # Step 2: Clean text columns
        dataframe = self._clean_text_columns(dataframe, self.data_column_names, self.date_column)

        # Log results
        self.logger.info(f"Data successfully cleaned. Loaded rows: {len(dataframe)}.")
        self.logger.info(f"Skipped rows: {len_raw_data - len(dataframe)}.")
        return dataframe

    def cleanup(self) -> None:
        """
        Removes files from the export directory if 'keep_files' is False.
        """
        if not self.keep_files:
            for file in self.export_path.glob("*"):
                try:
                    file.unlink()
                    self.logger.info(f"File {file} deleted successfully.")
                except Exception as e:
                    self.logger.error(f"Failed to delete file {file}: {e}")

    def __enter__(self) -> "CSVWorker":
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.cleanup()
