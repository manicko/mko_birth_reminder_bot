# python 3.x
from .utils import (yaml_to_dict)
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent

SETTINGS_FOLDER = 'settings'
CONFIG_NAME = 'config.yaml'
LOG_CONFIG_NAME = 'log_config.yaml'


class ConfigReader:
    def __init__(self, config_folder: str = SETTINGS_FOLDER):
        # super(ConfigReader, self).__init__()
        self.config_file = Path.joinpath(ROOT_DIR, Path(config_folder), CONFIG_NAME)
        self.log_config_file = Path.joinpath(ROOT_DIR, Path(config_folder), LOG_CONFIG_NAME)
        self.settings = yaml_to_dict(self.config_file)

        # Logger Settings
        self.log_settings = yaml_to_dict(self.log_config_file)
        # Telethon settings
        self.telethon_api_settings = self.settings.get('TELETHON_API')
        self.db_settings = self.settings.get('DATABASE')
        self.csv_settings = self.settings.get('CSV')

    def __setitem__(self, setting, data):
        self.settings[setting] = data

    def __getitem__(self, setting):
        if setting in self.settings:
            return self.settings[setting]

    def get(self, setting, default=None):
            return self.__getitem__(setting) or default

CONFIG = ConfigReader()

