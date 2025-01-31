from pathlib import Path
from symtable import Class
from typing import Any, Dict, Optional
import yaml
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from mko_birth_reminder_bot.core.utils import resolve_nested_paths, resolve_path

# Пути к файлам конфигурации

ROOT_DIR = Path(__file__).resolve().parent.parent

USER_SETTINGS_FOLDER = 'settings/user'
DEFAULT_SETTINGS_FOLDER = 'settings/default'

CONFIG_FILE = 'config.yaml'
LOG_CONFIG_FILE = 'log_config.yaml'
SECRETS_FILE = 'secrets.yaml'

DEFAULT_CONFIG_PATH = Path.joinpath(ROOT_DIR, DEFAULT_SETTINGS_FOLDER, CONFIG_FILE)
DEFAULT_LOG_CONFIG_PATH = Path.joinpath(ROOT_DIR, DEFAULT_SETTINGS_FOLDER, LOG_CONFIG_FILE)
DEFAULT_SECRETS_PATH = Path.joinpath(ROOT_DIR, DEFAULT_SETTINGS_FOLDER, SECRETS_FILE)

USER_CONFIG_PATH = Path.joinpath(ROOT_DIR, USER_SETTINGS_FOLDER, 'user_config.yaml')
USER_LOG_CONFIG_PATH = Path.joinpath(ROOT_DIR, USER_SETTINGS_FOLDER, 'user_log_config.yaml')
USER_SECRETS_PATH = Path.joinpath(ROOT_DIR, USER_SETTINGS_FOLDER, 'user_secrets.yaml')



class YamlConfigSettingsSource:
    """
    Load YAML files.
    """

    @classmethod
    def load_config(cls, path: Path) -> Dict[str, Any]:
        if path.exists():
            with path.open("r", encoding="utf-8") as f:
                return yaml.safe_load(f) or {}
        return {}

    @staticmethod
    def merge_dicts(dict1, dict2):
        """ Recursively merges dict2 into dict1 """
        if not isinstance(dict1, dict) or not isinstance(dict2, dict):
            return dict2
        for k in dict2:
            if k in dict1:
                dict1[k] = YamlConfigSettingsSource.merge_dicts(dict1[k], dict2[k])
            else:
                dict1[k] = dict2[k]
        return dict1

class DatabaseSettings(BaseModel):
    path: Path | str = Field(default=Path("data"))
    db_file: Path | str = Field(default=Path("birthdays.db"))
    columns: Dict[str, str] = {
        'id': 'INTEGER PRIMARY KEY AUTOINCREMENT',
        'company': 'TEXT',
        'last_name': 'TEXT',
        'first_name': 'TEXT',
        'position': 'TEXT',
        'gift_category': 'TEXT',
        'birth_date': 'TEXT NOT NULL',
        'notice_before_days': 'INTEGER',
    }
    default_notice: list[int] = [0, 1, 2, 3, 5, 7, 14]
    custom_notice_column: str = "notice_before_days"
    date_column: str = "birth_date"
    date_format: str = "%Y-%m-%d"

    # noinspection PyNestedDecorators
    @field_validator("path", mode="before")
    @classmethod
    def validate_paths(cls, v):
        return resolve_path(v)

class CsvSettings(BaseModel):
    class ReadDataSettings(BaseModel):
        path: Path | str  = Field(default=Path("tmp"))
        delete_after: int = 3
        from_csv: Dict[str, Any]

        # noinspection PyNestedDecorators
        @field_validator("path", mode="before")
        @classmethod
        def validate_paths(cls, v):
            return resolve_path(v)

    class ExportDataSettings(BaseModel):
        path: Path | str  = Field(default=Path("tmp"))
        to_csv: Dict[str, Any]

        # noinspection PyNestedDecorators
        @field_validator("path", mode="before")
        @classmethod
        def validate_paths(cls, v):
            return resolve_path(v)

    READ_DATA: ReadDataSettings
    EXPORT_DATA: ExportDataSettings



class TelethonApiSettings(BaseModel):
    start_menu: list[list[dict[str, str]]]
    add_record_menu: list[list[dict[str, str]]]
    bot_token: str
    client: Dict[str, Any]


class ReminderSettings(BaseModel):
    timezone: str = "Europe/Moscow"
    trigger: Dict[str, int]
    state_file: Path | str  = Field(default=Path("reminder_state.yaml"))


class LoggingSettings(BaseModel):
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: Dict[str, Any]
    handlers: Dict[str, Any]
    loggers: Dict[str, Any]
    root: Dict[str, Any]


class Config(BaseSettings):
    DATABASE: DatabaseSettings
    CSV: CsvSettings
    TELETHON_API: TelethonApiSettings
    REMINDER: ReminderSettings
    LOGGING: LoggingSettings

    model_config = SettingsConfigDict(env_prefix="app_", env_nested_delimiter="__")

    @classmethod
    def load(cls) -> "Config":
        default_config = YamlConfigSettingsSource.load_config(DEFAULT_CONFIG_PATH)
        user_config = YamlConfigSettingsSource.load_config(USER_CONFIG_PATH)
        YamlConfigSettingsSource.merge_dicts(default_config, user_config)  # Объединение конфигураций

        # LOGGING
        default_log_config = YamlConfigSettingsSource.load_config(DEFAULT_LOG_CONFIG_PATH)
        user_log_config = YamlConfigSettingsSource.load_config(USER_LOG_CONFIG_PATH)
        YamlConfigSettingsSource.merge_dicts(default_log_config, user_log_config)

        default_config["LOGGING"] = default_log_config

        # TELETHON SECRETS
        default_secrets = YamlConfigSettingsSource.load_config(DEFAULT_SECRETS_PATH)
        user_secrets = YamlConfigSettingsSource.load_config(USER_SECRETS_PATH)

        YamlConfigSettingsSource.merge_dicts(default_secrets, user_secrets)
        YamlConfigSettingsSource.merge_dicts(default_config, default_secrets)

        # CHECKING PATHS
        merged_config = resolve_nested_paths(default_config)

        return cls.model_validate(merged_config)


# Выгружаем
CONFIG = Config.load()

# print(CONFIG.CSV)
