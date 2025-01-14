import os
from pathlib import Path
from typing import List, Tuple, Optional
import pandas as pd

from .utils import (get_date, get_text)
from .config_reader import ConfigReader
from .logger import Logger


class CSVWorker:
    def __init__(self, config: ConfigReader, logger: Logger):

        self.config = config
        self.logger = logger


        self.data_column_names = self.config.db_settings["column_names"]
        self.date_column = self.config.db_settings["date_column"]

        self.import_path = Path(self.config.csv_settings["READ_DATA"]["path"])
        self.reader_settings = self.config.csv_settings["READ_DATA"]["from_csv"]

        self.export_path = Path(self.config.csv_settings["EXPORT_DATA"]["path"])
        self.export_settings = self.config.csv_settings["EXPORT_DATA"]["to_csv"]



    def read_csv(self, csv_file) -> pd.DataFrame:
        try:
            df = pd.read_csv(
                filepath_or_buffer=Path(self.import_path, csv_file),
                names=self.data_column_names,
                **self.reader_settings)
        except (pd.errors.ParserError, pd.errors.DataError) as err:
            self.logger.warning('Данные не могут быть загружены')
            self.logger.error(err)
            return pd.DataFrame()
        else:
            return df

    def export_to_csv(self, df: pd.DataFrame, file_name)->Path:
        try:
            file = Path(self.export_path, file_name)
        except FileNotFoundError as err:
            self.logger.error(err)
        else:
            try:
                df.to_csv(path_or_buf=file,
                          **self.export_settings)
            except pd.errors.DataError as err:
                self.logger.error(err)
            else:
                return file

    ####################         data processing            ####################

    def _clean_date_column(self, dataframe: pd.DataFrame, date_column: str) -> pd.DataFrame:
        """
        Проверяет и преобразует даты в указанной колонке. Удаляет строки с некорректными датами.

        :param dataframe: Входной DataFrame с данными.
        :param date_column: Название колонки, содержащей дату.
        :return: DataFrame с валидными датами.
        """
        valid_rows = []
        for _, row in dataframe.iterrows():
            # Получаем дату
            res = get_date(row[date_column])
            if res is False:
                self.logger.warning(f"Неверный формат даты: {row[date_column]}. "
                                    f"Строка пропущена.")
            else:
                # Преобразуем дату в формат dd/mm/yyyy
                row[date_column] = res.strftime("%d/%m/%Y")
                valid_rows.append(row)
        return pd.DataFrame(valid_rows)

    def _clean_text_columns(self, dataframe: pd.DataFrame, column_names: list, date_column: str) -> pd.DataFrame:
        """
        Проверяет и очищает текстовые данные в DataFrame.

        :param dataframe: DataFrame с данными.
        :param column_names: Список всех колонок.
        :param date_column: Название колонки с датой.
        :return: Очищенный DataFrame с текстовыми данными.
        """
        for col in column_names:
            if col != date_column:
                # Очищаем текстовые данные, оставляя только буквы и пробелы
                dataframe[col] = dataframe[col].astype(str).apply(get_text)
        return dataframe

    def prepare_dataframe(self, dataframe: pd.DataFrame) -> pd.DataFrame:
        """
        Проверяет и очищает данные в DataFrame перед загрузкой в базу данных.

        :param dataframe: Входной DataFrame с данными.
        :return: Очищенный DataFrame.
        """
        column_names: list = self.data_column_names
        date_column: str = self.date_column
        # Проверка количества столбцов
        if len(dataframe.columns) != len(column_names):
            self.logger.error("Количество столбцов не соответствует ожидаемому. Загрузка данных отменена.")
            return pd.DataFrame()  # Возвращаем пустой DataFrame

        len_raw_data = len(dataframe)
        # Переименование столбцов
        dataframe.columns = column_names

        # Шаг 1: Очистка даты
        dataframe = self._clean_date_column(dataframe, date_column)

        # Шаг 2: Очистка текстовых данных
        dataframe = self._clean_text_columns(dataframe, column_names, date_column)

        # Логирование результатов
        self.logger.info(f"Данные успешно очищены. Загружено строк: {len(dataframe)}.")
        self.logger.info(f"Пропущено строк: {len_raw_data - len(dataframe)}.")

        return dataframe

#################################################################################
