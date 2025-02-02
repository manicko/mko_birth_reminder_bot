import click
import logging
from mko_birth_reminder_bot.core.config import PATHS
from mko_birth_reminder_bot.core.config_utils import save_config
from mko_birth_reminder_bot.core import DBWorker, TGUsers

# Logging setup
logger = logging.getLogger(__name__)


@click.group()
def cli():
    """Main CLI command group."""
    pass


def export_single_config(config_name: str) -> None:
    """
    Exports a single configuration file.

    Args:
        config_name (str): The name of the configuration file to export.

    Raises:
        ValueError: If the specified config name is not found.
    """
    if config_name in PATHS.config_files:
        config = PATHS.config_files[config_name]
        save_config(file_from=PATHS.default_settings / config,
                    file_to=PATHS.user_settings / config)
        click.echo(f"File {config} successfully exported.")
    else:
        raise ValueError(f"Config name {config_name} not found.")


def initialize_database():
    """Initializes the database by creating the required table."""
    with DBWorker() as db_worker:
        db_worker.create_table(TGUsers.TABLE_NAME, TGUsers.TABLE_FIELDS)


@cli.command()
@click.option('--config-name',
              type=click.Choice(list(PATHS.config_files.keys()) + ['all'], case_sensitive=False),
              default="all",
              show_default=True,
              help="Name of the configuration file to export.")
def export_config(config_name: str) -> None:
    """
    Exports configuration files.

    Args:
        config_name (str): The name of the configuration file to export. Use "all" to export all configurations.
    """
    if config_name == "all":
        for name in PATHS.config_files.keys():
            export_single_config(name)
    else:
        export_single_config(config_name)


@cli.command()
def init_db() -> None:
    """
    Initializes the database.

    This function attempts to create the necessary database tables.
    If an error occurs during initialization, it is displayed to the user.
    """
    try:
        initialize_database()  # Calls the database initialization function
        click.echo("Database successfully initialized.")
    except Exception as e:
        click.echo(f"Error initializing database: {e}", err=True)


if __name__ == "__main__":
    cli()
