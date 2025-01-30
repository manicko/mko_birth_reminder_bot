# python 3.x
from .utils import (yaml_to_dict, resolve_path, resolve_nested_paths)
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

        # Main settings
        self.settings = yaml_to_dict(self.config_file)
        resolve_nested_paths(self.settings)

        # Logger Settings
        self.log_settings = yaml_to_dict(self.log_config_file)
        resolve_nested_paths(self.log_settings)

        ## subsections
        self.db_settings = self.settings.get('DATABASE')
        self.csv_settings = self.settings.get('CSV')
        self.reminder_settings = self.settings.get('REMINDER')


        # Telethon settings
        self.secrets = yaml_to_dict(self.secrets_file)
        self.telethon_api_settings = self.secrets.get('TELETHON_API')

    @staticmethod
    def get_correct_paths(settings: dict, path_names: str|tuple = ('path','filename')) -> dict:
        """
        Try to resolve paths inplace in settings using names pattern
        Args:
            settings: dict,
            Dictionary to search keys having
            path_names: str|tuple,
            Keys to search for in settings dictionary

        Returns:
            Settings with correct paths
        """

        def get_level_value(d:dict, lvl:list)->str|dict:
            """
            Returns the last item of the dictionary using the path
            """
            start = d
            for k in lvl:
                start=start[k]
            return start

        items = [(k,[]) for k in settings.keys()]

        while items:
            key, level = items.pop()
            val = get_level_value(settings, level)
            if key in path_names:
                val[key] = resolve_path(val[key])
                continue
            if isinstance(val[key], dict):
                level.append(key)
                level.extend([(k,[]) for k in val[key].keys()])



    def __setitem__(self, setting, data):
        self.settings[setting] = data

    def __getitem__(self, setting):
        if setting in self.settings:
            return self.settings[setting]

    def get(self, setting, default=None):
            return self.__getitem__(setting) or default

CONFIG = ConfigReader()

