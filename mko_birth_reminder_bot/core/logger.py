import logging
from pathlib import Path
from .config_reader import ConfigReader
from logging.handlers import RotatingFileHandler

class Logger:
    """
    A simple logger class for logging information and errors to a file.

    Usage:
    logger = Logger()
    logger.info("This is an information message.")
    logger.error("This is an error message.")
    """

    def __init__(self, config: ConfigReader):
        self.logger = logging.getLogger(__name__)


        # Получаем настройки из конфигурации
        log_path = config.get("path", "")
        log_file = config.get("file", f"{__name__}.log")

        log_level = getattr(logging, config["log_level"].upper(), logging.INFO)
        max_log_size = int(config.get("max_log_size", 5 ))* 1024 * 1024  # Размер файла в байтах (по умолчанию 5 MB)
        backup_count = int(config.get("backup_count", 2))  # Количество архивных файлов
        # Настройка обработчика с ротацией

        self.logger.setLevel(log_level)

        try:
            log_file_path = Path(log_path, log_file)
            # Настройка обработчика с ротацией
            handler = RotatingFileHandler(
                log_file_path, maxBytes=max_log_size, backupCount=backup_count, encoding='utf-8'
            )
            handler.setFormatter(
                logging.Formatter("%(asctime)s - %(levelname)s - %(message)s", datefmt='%d-%m-%y %I:%M:%S %p')
            )

            # Настройка логгера
            self.logger = logging.getLogger(__name__)
            self.logger.setLevel(log_level)
            self.logger.addHandler(handler)
            handler.close()
        except FileNotFoundError:
            print("Logging file not found")

    def info(self, message):
        """
        Log an information message.

        Parameters:
        - message: The information message to be logged.
        """
        self.logger.info(message)

    def error(self, message):
        """
        Log an error message.

        Parameters:
        - message: The error message to be logged.
        """
        self.logger.error(message)

    def warning(self, message):
        """
        Log an information message.

        Parameters:
        - message: The information message to be logged.
        """
        self.logger.warning(message)
