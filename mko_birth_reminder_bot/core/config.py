from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from platformdirs import user_config_dir
from mko_birth_reminder_bot.core.config_worker import (load_config,
                                                       resolve_nested_paths,
                                                       resolve_path, merge_dicts)


ROOT_DIR = Path(__file__).resolve().parent.parent
DEFAULT_SETTINGS_FOLDER = Path.joinpath(ROOT_DIR, "settings/default")

MODULE_NAME = str(Path(__file__).resolve().parent.parent.name)
USER_SETTINGS_FOLDER = Path.joinpath(Path(user_config_dir(MODULE_NAME)), "settings")


CONFIG_FILES = {
    "config": 'config.yaml',
    "log_config": 'log_config.yaml',
    "secrets": 'secrets.yaml',
}

class DatabaseSettings(BaseModel):
    path: Path | str = Field(default=Path("data"))
    db_file: Path | str = Field(default=Path("birthdays.db"))
    columns: dict[str, str] = {
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
        path: Path | str = Field(default=Path("tmp"))
        delete_after: int = 3
        from_csv: dict[str, Any]

        # noinspection PyNestedDecorators
        @field_validator("path", mode="before")
        @classmethod
        def validate_paths(cls, v):
            return resolve_path(v)

    class ExportDataSettings(BaseModel):
        path: Path | str = Field(default=Path("tmp"))
        to_csv: dict[str, Any]

        # noinspection PyNestedDecorators
        @field_validator("path", mode="before")
        @classmethod
        def validate_paths(cls, v):
            return resolve_path(v)

    READ_DATA: ReadDataSettings
    EXPORT_DATA: ExportDataSettings


class TelethonApiSettings(BaseModel):
    menu: dict[str, list[list[dict[str, str]]]]
    bot_token: str
    client: dict[str, Any]


class ReminderSettings(BaseModel):
    timezone: str = "Europe/Moscow"
    trigger: dict[str, int]
    state_file: Path | str = Field(default=Path("reminder_state.yaml"))
    columns_to_send: list[str]


class LoggingSettings(BaseModel):
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict[str, Any]
    handlers: dict[str, Any]
    loggers: dict[str, Any]
    root: dict[str, Any]


class Config(BaseSettings):
    DATABASE: DatabaseSettings
    CSV: CsvSettings
    TELETHON_API: TelethonApiSettings
    REMINDER: ReminderSettings
    LOGGING: LoggingSettings

    model_config = SettingsConfigDict(env_prefix="app_", env_nested_delimiter="__")

    @classmethod
    def load(cls) -> "Config":

        merged_config = {}
        for folder in (DEFAULT_SETTINGS_FOLDER, USER_SETTINGS_FOLDER):
            for file in CONFIG_FILES.values():
                path = Path.joinpath(folder, file)
                data = load_config(path)
                merge_dicts(merged_config, data)

        merged_config = resolve_nested_paths(merged_config)
        return cls.model_validate(merged_config)


# Выгружаем
CONFIG = Config.load()

# print(CONFIG.CSV)
