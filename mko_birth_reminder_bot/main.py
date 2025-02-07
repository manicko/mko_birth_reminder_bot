import click
import logging
import asyncio
import signal
from mko_birth_reminder_bot.core.config import PATHS
from mko_birth_reminder_bot.core.config_utils import save_config
from mko_birth_reminder_bot.core import DBHandler, TGUsers

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
        click.echo(f"File {config} successfully exported to '{PATHS.user_settings / config}'")
    else:
        raise ValueError(f"Config name {config_name} not found.")


def initialize_database():
    """Initializes the database by creating the required table."""
    with DBHandler() as db_handler:
        db_handler.create_table(TGUsers.TABLE_NAME, TGUsers.TABLE_FIELDS)


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


@cli.command()
def run_bot() -> None:
    """
    Starts the Telegram bot and its scheduler.

    This function initializes and runs the Telegram bot using the Telethon library.
    It also starts the scheduled tasks associated with the bot. If an error occurs
    during execution, an error message is displayed.

    Raises:
        Exception: If an error occurs while launching the bot.
    """

    try:
        from mko_birth_reminder_bot.tgbot import run_tg_bot
        click.echo("Launching the bot... Press Ctrl+C to stop.")
        click.echo("To verify, contact the bot via Telegram using its username (starting with '@') "
                   "and send the '/start' command.")
        asyncio.run(run_tg_bot())  # Безопасный запуск и завершение event loop

    except KeyboardInterrupt:
        from mko_birth_reminder_bot.tgbot import stop_tg_bot
        click.echo("Stopping the bot...")
        asyncio.run(stop_tg_bot())  # Корректное завершение
    except Exception as e:
        click.echo(f"Error launching the bot: {e}", err=True)


def handle_signal(signal_number, frame):
    """
    Handles SIGINT (Ctrl+C) and SIGTERM (kill).
    """
    try:
        from mko_birth_reminder_bot.tgbot import stop_tg_bot
        click.echo(f"Received signal {signal_number}. Stopping the bot...")
        logger.info(f"Received signal {signal_number}. Stopping the bot...")
        asyncio.create_task(stop_tg_bot())  # Stops the bot asynchronously
    except Exception as e:
        click.echo(f"Error stopping the bot: {e}", err=True)


# Register signal handlers **before** running CLI
signal.signal(signal.SIGINT, handle_signal)  # Ctrl+C
signal.signal(signal.SIGTERM, handle_signal)  # kill

if __name__ == "__main__":
    cli()
