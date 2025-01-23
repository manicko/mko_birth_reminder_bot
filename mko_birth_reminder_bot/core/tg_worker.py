import logging
from telethon import TelegramClient, events, Button
from pathlib import Path
from typing import Dict, Any
from mko_birth_reminder_bot.core.utils import generate_random_filename
from mko_birth_reminder_bot.core.config_reader import CONFIG

logger = logging.getLogger(__name__)

client = TelegramClient(**CONFIG.telethon_api_settings['client'])
# Словарь для временного хранения данных пользователей
user_data = {}

TELETHON_API = {
    "start_menu": [
        [{"add_record": "Добавить запись"}],
        [{"update_record_by_id": "Исправить по id"},
         {"delete_record_by_id": "Удалить по id"}],
        [{"import_csv": "Импорт из CSV"}, {"export_csv": "Экспорт в CSV"}],
        [{"delete_user": "Отписаться"}],
    ],
    "add_record_menu": [
        [{"back_to_start": "Назад"}],
        [{"first_name": "Имя"}, {"last_name": "Фамилия"}],
        [{"company": "Компания"}, {"position": "Должность"}],
        [{"gift_category": "Категория подарка"}],
        [{"birth_date": "День рождения в формате ДД.ММ.ГГГГ"}],
        [{"notice_before_days": "За сколько дней предупредить ДД"}],
        [{"confirm_data": "Подтвердить"}]
    ]
}


def make_menu(name, config):
    if name not in config:
        return
    level = config[name]
    menu = []
    for row in level:
        menu.append([Button.inline(text, button.encode('UTF-8')) for item in row
                     for button, text in item.items()])
    return menu


def get_prompt_from_config(choice, menu):
    if isinstance(menu, dict):
        if choice in menu:
            return menu[choice]
        for item in menu.values():
            result = get_prompt_from_config(choice, item)
            if result:
                return result
    elif isinstance(menu, list):
        for item in menu:
            result = get_prompt_from_config(choice, item)
            if result:
                return result


async def show_start_menu(event):
    """
    Показывает главное меню (1 уровень).
    """
    menu = make_menu("start_menu", TELETHON_API)
    await event.edit("Выберите опцию", buttons=menu)


async def show_add_record_menu(event, user_id):
    """
    Показывает меню 2 уровня для ввода данных.
    """
    menu = make_menu("add_record_menu", TELETHON_API)
    user_data.setdefault(user_id, {})  # Создаем запись для пользователя, если ее нет
    await event.edit("Выберите поле и введите данные:", buttons=menu)


async def ask_for_input(event, user_id, param_name, prompt_text):
    """
    Запрашивает у пользователя ввод данных (3 уровень).
    """
    user_data[user_id]['current_param'] = param_name  # Запоминаем, какой параметр ожидается
    await event.edit(prompt_text)


async def handle_data_entry(event, user_id):
    """
    Обрабатывает введенные данные на 3 уровне.
    """
    param_name = user_data[user_id].get('current_param')
    if param_name:
        user_data[user_id][param_name] = event.raw_text  # Сохраняем введенные данные
        buttons = [
            [Button.inline("Принять", b"accept_input")],
            [Button.inline("Отменить", b"cancel_input")]
        ]
        await event.reply(f"Вы ввели: {event.raw_text}. Подтвердите или отмените:", buttons=buttons)


async def show_input_id_menu(event, user_id):
    # TODO написать
    pass


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    """
    Обрабатывает команду /start и показывает меню старт.
    """
    sent = await event.respond("Загрузка меню...")
    await show_start_menu(sent)


@client.on(events.CallbackQuery)
async def handle_callback(event):
    """
    Обрабатывает нажатия кнопок меню.
    """
    user_id = event.sender_id
    data = event.data.decode('utf-8')

    match data:

        ##### start menu #####
        case "add_record":
            await show_add_record_menu(event, user_id)

        case "update_record_by_id":
            await show_input_id_menu(event, user_id)

        case "delete_record_by_id":
            await show_input_id_menu(event, user_id)

        case "import_csv":
            # TODO
            pass

        case "export_csv":
            # TODO
            pass

        case "delete_user":
            user_data.pop(user_id, None)  # Удаляем данные пользователя
            await event.edit("Ваши данные удалены.")
            await show_start_menu(event)

        #### add_record_menu ###

        case "company" | "position" | "gift_category" | "first_name" | "last_name" | \
             "birth_date" | "notice_before_days" as choice:
            prompt = f"Введите {get_prompt_from_config(choice, TELETHON_API)}"
            await ask_for_input(event, user_id, choice, prompt)

        case "confirm_data":
            user_info = user_data.get(user_id, {})
            if 'birth_date' in user_info:
                result = (
                    f"Введенные данные:\n"
                    ", ".join(user_info.values())
                )
                await event.edit(result)
                user_data.pop(user_id, None)  # Очищаем данные пользователя
                await show_start_menu(event)
            else:
                await event.edit("Вы не заполнили обязательное поле день рождения.")

        case "accept_input":
            await show_add_record_menu(event, user_id)

        case "cancel_input":
            param_name = user_data[user_id].get('current_param')
            if param_name:
                user_data[user_id].pop(param_name, None)  # Удаляем текущее значение
            await ask_for_input(event, user_id, param_name, f"Введите {param_name} снова:")

        case "back_to_start":
            await show_start_menu(event)


@client.on(events.NewMessage)
async def handle_text(event):
    """
    Обрабатывает текстовые сообщения для ввода данных на 3 уровне.
    """
    user_id = event.sender_id
    if user_id in user_data and 'current_param' in user_data[user_id]:
        await handle_data_entry(event, user_id)


def main():
    """
    The main entry point for running the Telegram bot.
    """

    client.start(bot_token=CONFIG.telethon_api_settings.get('bot_token'))
    logger.info("Telegram bot is running.")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
