import pytz
from pathlib import Path
import yaml
import logging
from telethon import TelegramClient
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from datetime import datetime, timedelta
from mko_birth_reminder_bot.core import CONFIG

logger = logging.getLogger(__name__)

CHAT_ID = "chat_id"
MESSAGE = "Ну привет тебе землянин"
STATE_FILE = Path(CONFIG.reminder_settings["state_file"])

TIMEZONE = CONFIG.reminder_settings["timezone"]
TRIGGER_ARGS = CONFIG.reminder_settings["trigger"]


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


# Функция отправки сообщения
async def send_message(client: TelegramClient, chat_id: str, message: str):
    try:
        await client.send_message(chat_id, message)
        logging.info(f"Сообщение отправлено: {message}")
    except Exception as e:
        logging.info(f"Ошибка при отправке сообщения: {e}")


# Основная задача для планировщика
async def task_to_run(client: TelegramClient, chat_id: str = CHAT_ID, message: str = MESSAGE):
    tz = pytz.timezone(TIMEZONE)
    now = datetime.now(tz)
    last_run = load_state()

    if last_run:
        next_run_time = last_run + timedelta(days=1)
        if now > next_run_time:
            logging.info("Пропущено задание. Выполняем с задержкой.")
            await send_message(client, chat_id, message)
    else:
        logging.info("Первый запуск задачи.")

    await send_message(client, chat_id, message)
    save_state(now)


# Настройка планировщика
async def start_scheduler(client):
    scheduler = AsyncIOScheduler(timezone=TIMEZONE)
    trigger = CronTrigger(**TRIGGER_ARGS)
    scheduler.add_job(task_to_run, trigger, args=[client])
    scheduler.start()
    logging.info(f"Планировщик запущен. Следующее сообщение в 11:45 ({TIMEZONE}).")
