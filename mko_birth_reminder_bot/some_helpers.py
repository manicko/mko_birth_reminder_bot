from tgbot import get_prompt_from_config
from mko_birth_reminder_bot.core import CONFIG
print(CONFIG.TELETHON_API.menu)
a = get_prompt_from_config('company', CONFIG.TELETHON_API.menu)
print(a)