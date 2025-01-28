# python 3.x
from .utils import (yaml_to_dict)
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

SETTINGS_FOLDER = 'settings'
CONFIG_NAME = 'config.yaml'
LOG_CONFIG_NAME = 'log_config.yaml'
SECRETS_NAME = 'secrets.yaml'


class ConfigReader:
    def __init__(self, config_folder: str = SETTINGS_FOLDER):
        # super(ConfigReader, self).__init__()

        self.config_file = Path.joinpath(ROOT_DIR, Path(config_folder), CONFIG_NAME)
        self.log_config_file = Path.joinpath(ROOT_DIR, Path(config_folder), LOG_CONFIG_NAME)
        self.secrets_file = Path.joinpath(ROOT_DIR, Path(config_folder), SECRETS_NAME)

        self.settings = yaml_to_dict(self.config_file)
        self.db_settings = self.settings.get('DATABASE')
        self.csv_settings = self.settings.get('CSV')
        self.reminder_settings = self.settings.get('REMINDER')

        # Logger Settings
        self.log_settings = yaml_to_dict(self.log_config_file)
        # Telethon settings
        self.secrets = yaml_to_dict(self.secrets_file)
        self.telethon_api_settings = self.secrets.get('TELETHON_API')


    def __setitem__(self, setting, data):
        self.settings[setting] = data

    def __getitem__(self, setting):
        if setting in self.settings:
            return self.settings[setting]

    def get(self, setting, default=None):
            return self.__getitem__(setting) or default

CONFIG = ConfigReader()

