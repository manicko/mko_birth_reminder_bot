import pytz
import asyncio
import yaml
import logging
from random import randint
from pathlib import Path
from prettytable import PrettyTable
from telethon import TelegramClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from mko_birth_reminder_bot.core import CONFIG, TGUsers, TGUserData

logger = logging.getLogger(__name__)

STATE_FILE = Path(CONFIG.reminder_settings["state_file"])

TIMEZONE = CONFIG.reminder_settings["timezone"]
TRIGGER_ARGS = CONFIG.reminder_settings["trigger"]
COLUMNS = (
    'id',
    # 'company',
    'last_name',
    'first_name',
    # 'gift_category',
    'birth_date')


# Функция для сохранения состояния планировщика
def save_state(last_run: datetime):
    state = {"last_run": last_run.isoformat()}
    STATE_FILE.write_text(yaml.dump(state), encoding="utf-8")
    logging.info(f"Состояние сохранено: {state}")


# Функция для загрузки состояния планировщика
def load_state():
    if STATE_FILE.exists():
        state = yaml.safe_load(STATE_FILE.read_text(encoding="utf-8"))
        if "last_run" in state:
            return datetime.fromisoformat(state["last_run"])
    logging.info("Состояние не найдено или повреждено.")
    return None


def beautify_table(data: dict, columns: tuple = COLUMNS) -> str | None:
    if data:
        table = PrettyTable()
        table.field_names = data["header"]
        table.align = "l"

        for row in sorted(data["items"], key=lambda x: x[-2][-5:]):
            table.add_row(row)

        return f"``` \n{table.get_string(fields=columns)} ```"
    return None


async def generate_msgs(queue:asyncio.Queue, date: datetime|None = None):
    tg_users: TGUsers = TGUsers()
    for user_id in tg_users.iter_ids():
        user_data: TGUserData = TGUserData(user_id)
        data = user_data.get_all_reminders(date=date)
        msg = beautify_table(data)
        if msg:
            await queue.put((user_id, msg))


async def process_msgs(client: TelegramClient, queue: asyncio.Queue):
    while True:
        user_id, msg = await queue.get()
        await send_message(client, user_id, msg)
        queue.task_done()
        await asyncio.sleep(randint(5, 15))


# Функция отправки сообщения
async def send_message(client: TelegramClient, chat_id: str, message: str):
    try:
        await client.send_message(chat_id, message)
        logging.info(f"Сообщение отправлено")
    except Exception as e:
        logging.error(f"Ошибка при отправке сообщения {chat_id}: {e}")


async def main_reminder(client: TelegramClient,date: datetime | None = None):
    queue = asyncio.Queue()
    task = asyncio.create_task(process_msgs(client, queue))
    await generate_msgs(queue,date=date)
    await queue.join()
    task.cancel()


# # Основная задача для планировщика
# async def OLD_task_to_run(client: TelegramClient):
#     tz = pytz.timezone(TIMEZONE)
#     now = datetime.now(tz)
#     last_run = load_state() or now
#     delta = (now - last_run).days
#     if delta:
#         next_run_time = last_run + timedelta(days=delta)
#         logging.info("Пропущено задание. Выполняем с задержкой.")
#         await main_reminder(client,date=next_run_time)
#         save_state(next_run_time)
#         logging.info(f"Пропущенное задание выполнено {next_run_time}.")
#     await main_reminder(client)
#     save_state(now)


async def check_missed_run(client: TelegramClient):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_run = load_state() or now
    delta = (now - last_run).days
    if delta:
        next_run_time = last_run + timedelta(days=delta)
        logging.info("Пропущено задание. Выполняем с задержкой.")
        await main_reminder(client,date=next_run_time)
        save_state(next_run_time)
        logging.info(f"Пропущенное задание выполнено {next_run_time}.")


async def task_to_run(client: TelegramClient):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    await main_reminder(client)
    save_state(now)
    logging.info("Сообщения отправлены.")

# Настройка планировщика
async def start_scheduler(client):
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    trigger = CronTrigger(**TRIGGER_ARGS)
    scheduler.add_job(task_to_run, trigger, args=[client])
    scheduler.start()
    logging.info(f"Планировщик запущен."
                 f" Следующее сообщение в "
                 f"{TRIGGER_ARGS['hour']}:{TRIGGER_ARGS['minute']} ({TIMEZONE}).")
