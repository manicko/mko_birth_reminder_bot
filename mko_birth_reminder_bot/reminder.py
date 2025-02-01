import pytz
import asyncio
import yaml
import logging
from random import randint
from prettytable import PrettyTable
from telethon import TelegramClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from typing import Optional, Union
from mko_birth_reminder_bot.core import CONFIG, TGUsers, TGUserData

logger = logging.getLogger(__name__)

STATE_FILE = CONFIG.REMINDER.state_file
TIMEZONE = CONFIG.REMINDER.timezone
TRIGGER_ARGS = CONFIG.REMINDER.trigger
COLUMNS_TO_SEND = CONFIG.REMINDER.columns_to_send


def save_state(last_run: datetime) -> None:
    """
    Saves the scheduler state.

    Args:
        last_run (datetime): The last execution time.
    """
    state = {"last_run": last_run.isoformat()}
    STATE_FILE.write_text(yaml.dump(state), encoding="utf-8")
    logging.info(f"State saved: {state}")


def load_state() -> Optional[datetime]:
    """
    Loads the last execution state.

    Returns:
        Optional[datetime]: The last execution time or None if not found.
    """
    if STATE_FILE.exists():
        state = yaml.safe_load(STATE_FILE.read_text(encoding="utf-8"))
        if "last_run" in state:
            return datetime.fromisoformat(state["last_run"])
    logging.info("State not found or corrupted.")
    return None


def beautify_table(data: dict, columns: tuple = COLUMNS_TO_SEND) -> Optional[str]:
    """
    Formats the data into a PrettyTable.

    Args:
        data (dict): Data to be formatted.
        columns (tuple, optional): Columns to include. Defaults to COLUMNS_TO_SEND.

    Returns:
        Optional[str]: Formatted table as a string, or None if data is empty.
    """
    if data:
        table = PrettyTable()
        table.field_names = data["header"]
        table.align = "l"

        for row in sorted(data["items"], key=lambda x: x[-2][-5:]):
            table.add_row(row)

        return f"``` \n{table.get_string(fields=columns)} ```"
    return None


async def generate_msgs(queue: asyncio.Queue, date: Union[datetime, None] = None):
    """
    Generates messages for users and adds them to the queue.

    Args:
        queue (asyncio.Queue): The queue to store messages.
        date (Optional[datetime], optional): Specific date for reminders. Defaults to None.
    """
    tg_users: TGUsers = TGUsers()
    for user_id in tg_users.iter_ids():
        user_data: TGUserData = TGUserData(user_id)
        data = user_data.get_all_reminders(date=date)
        msg = beautify_table(data)
        if msg:
            await queue.put((user_id, msg))


async def process_msgs(client: TelegramClient, queue: asyncio.Queue) -> None:
    """
    Processes and sends messages from the queue.

    Args:
        client (TelegramClient): The Telegram client.
        queue (asyncio.Queue): The queue containing messages.
    """
    while True:
        user_id, msg = await queue.get()
        await send_message(client, user_id, msg)
        queue.task_done()
        await asyncio.sleep(randint(5, 15))


async def send_message(client: TelegramClient, chat_id: str, message: str) -> None:
    """
    Sends a message to a specified Telegram chat.

    Args:
        client (TelegramClient): The Telegram client.
        chat_id (str): The chat ID to send the message to.
        message (str): The message content.
    """
    try:
        await client.send_message(chat_id, message)
    except Exception as e:
        logging.error(f"Error sending message to {chat_id}: {e}", exc_info=True)


async def main_reminder(client: TelegramClient, date: Optional[datetime] = None) -> None:
    """
    Main reminder function that generates and processes messages.

    Args:
        client (TelegramClient): The Telegram client.
        date (Optional[datetime], optional): Specific date for reminders. Defaults to None.
    """
    queue = asyncio.Queue()
    task = asyncio.create_task(process_msgs(client, queue))
    await generate_msgs(queue, date=date)
    await queue.join()
    task.cancel()


async def check_missed_run(client: TelegramClient) -> None:
    """
    Checks for missed reminder runs and executes them if necessary.

    Args:
        client (TelegramClient): The Telegram client.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_run = load_state() or now
    delta = (now - last_run).days
    if delta:
        next_run_time = last_run + timedelta(days=delta)
        logging.info("Missed task detected. Running it now.")
        await main_reminder(client, date=next_run_time)
        save_state(next_run_time)
        logging.info(f"Missed task completed at {next_run_time}.")


async def task_to_run(client: TelegramClient) -> None:
    """
    Executes the scheduled reminder task.

    Args:
        client (TelegramClient): The Telegram client.
    """
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    await main_reminder(client)
    save_state(now)
    logging.info("Messages sent successfully.")


async def start_scheduler(client: TelegramClient) -> None:
    """
    Starts the reminder scheduler.

    Args:
        client (TelegramClient): The Telegram client.
    """
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    trigger = CronTrigger(**TRIGGER_ARGS)
    scheduler.add_job(task_to_run, trigger, args=[client])
    scheduler.start()
    logging.info(f"Scheduler started. Next message at {TRIGGER_ARGS['hour']}:{TRIGGER_ARGS['minute']} ({TIMEZONE}).")
