from pathlib import Path
from typing import Any
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings
from platformdirs import user_config_dir

from mko_birth_reminder_bot.core.config_utils import (
    load_config, resolve_path, merge_dicts
)

class WorkingPaths(BaseSettings):
    """
    Defines essential working paths for configuration and user data.
    """
    root_dir: Path = Path(__file__).resolve().parent.parent
    module_name: str = root_dir.name
    user_folder: Path = Path(user_config_dir(module_name))

    default_settings: Path = Path.joinpath(root_dir, 'settings')
    user_settings: Path = Path.joinpath(user_folder, 'settings')

    config_files: dict[str, str] = {
        "config": "config.yaml",
        "log_config": "log_config.yaml",
        "secrets": "secrets.yaml",
    }

    model_config = {
        "env_prefix": "APP_",
        "env_nested_delimiter": "__",
        "extra": "ignore"
    }

PATHS = WorkingPaths()

# Database settings
class DatabaseSettings(BaseModel):
    """
    Configuration settings for the SQLite database.
    """
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

    @field_validator("path", mode="before")
    @classmethod
    def validate_paths(cls, v: str | Path) -> Path:
        return resolve_path(v, PATHS.user_folder)

# CSV settings
class CsvSettings(BaseModel):
    """
    Configuration settings for CSV file handling.
    """
    class ReadDataSettings(BaseModel):
        path: Path | str = Field(default=Path("tmp"))
        delete_after: int = 3
        from_csv: dict[str, Any]

        @field_validator("path", mode="before")
        @classmethod
        def validate_paths(cls, v: str | Path) -> Path:
            return resolve_path(v, PATHS.user_folder)

    class ExportDataSettings(BaseModel):
        path: Path | str = Field(default=Path("tmp"))
        to_csv: dict[str, Any]

        @field_validator("path", mode="before")
        @classmethod
        def validate_paths(cls, v: str | Path) -> Path:
            return resolve_path(v, PATHS.user_folder)

    READ_DATA: ReadDataSettings
    EXPORT_DATA: ExportDataSettings

# Telethon API settings
class TelethonApiSettings(BaseModel):
    """
    Configuration for the Telethon API.
    """
    menu: dict[str, list[list[dict[str, str]]]]
    bot_token: str
    client: dict[str, Any]

# Reminder settings
class ReminderSettings(BaseModel):
    """
    Configuration settings for reminders.
    """
    timezone: str = "Europe/Moscow"
    trigger: dict[str, int]
    state_file: Path | str = Field(default=Path("reminder_state.yaml"))
    columns_to_send: list[str]

    @field_validator("state_file", mode="before")
    @classmethod
    def validate_paths(cls, v: str | Path) -> Path:
        return resolve_path(v, PATHS.user_folder)

# Logging settings
class LoggingSettings(BaseModel):
    """
    Logging configuration.
    """
    version: int = 1
    disable_existing_loggers: bool = False
    formatters: dict[str, Any]
    handlers: dict[str, Any]
    loggers: dict[str, Any]
    root: dict[str, Any]

    @field_validator("handlers", mode="before")
    @classmethod
    def validate_paths(cls, handlers: dict[str, Any]) -> dict[str, Any]:
        """
        Ensures log file paths exist before validation.
        """
        for handler in handlers.values():
            if isinstance(handler, dict) and "filename" in handler:
                filename = handler["filename"]
                handler["filename"] = resolve_path(filename, PATHS.user_folder / "logs")
        return handlers

# Main configuration class
class Config(BaseSettings):
    """
    Main configuration class that loads and merges all configurations.
    """
    DATABASE: DatabaseSettings
    CSV: CsvSettings
    TELETHON_API: TelethonApiSettings
    REMINDER: ReminderSettings
    LOGGING: LoggingSettings

    model_config = {
        "env_prefix": "APP_",
        "env_nested_delimiter": "__",
        "extra": "ignore"
    }

    @classmethod
    def load(cls) -> "Config":
        """
        Loads and merges configurations from `DEFAULT_SETTINGS_FOLDER` and `USER_SETTINGS_FOLDER`.
        """
        merged_config = {}
        for folder in (PATHS.root_dir, PATHS.user_folder):
            for file in PATHS.config_files.values():
                path = Path.joinpath(folder, 'settings', file)
                data = load_config(path)  # Load YAML
                merge_dicts(merged_config, data)  # Merge configs

        return cls.model_validate(merged_config)

# Load the final configuration
CONFIG = Config.load()
