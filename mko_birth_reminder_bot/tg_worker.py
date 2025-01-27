import logging
from telethon import TelegramClient, events, Button

from mko_birth_reminder_bot.core import CONFIG

from mko_birth_reminder_bot.operator import Operator

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
        [{"notice_before_days": "За сколько дней предупредить"}],
        [{"confirm_record": "Подтвердить"}]
    ]
}

DEFAULT_CAPTION = "Повторите попытку введя команду /start"

async def save_csv_file(event, upload_dir: str = CONFIG.csv_settings["READ_DATA"]["path"]):
    """
    Сохраняет загруженный пользователем CSV-файл в указанную папку.

    Параметры:
        event: событие Telethon.
        upload_dir: путь к папке для сохранения файла.
    Возвращает:
        str: Путь к сохраненному файлу или сообщение об ошибке.
    """
    user_id = event.sender_id
    user_data[user_id]['params']['csv'] = None
    if event.file and event.file.mime_type == "text/csv":
        try:
            # Сохраняем файл
            user_data[user_id]['params']['csv'] = await event.download_media(file=upload_dir)
            return f"Файл успешно сохранен. Приступаю к загрузке данных"
        except Exception as e:
            logger.error(f"Ошибка при сохранении файла: {e}")
            return f"Ошибка при сохранении файла: {e}"
    else:
        return "Ошибка: Пожалуйста, загрузите CSV-файл."


def get_csv_prompt(columns: dict = CONFIG.db_settings["columns"],
                   sep: str = CONFIG.csv_settings["READ_DATA"]["from_csv"]["sep"],
                   enc: str = CONFIG.csv_settings["READ_DATA"]["from_csv"]["encoding"]):
    text = [["ОАО Зета", "Соколова", "Анна", "Кадры", "1-я категория", "1995-04-18", 7],
            ["ПАО Эта", "Козлов", "Иван", "Генеральный директор", "VIP", "1978-09-23", 30]]
    names = [col_name for col_name, col_type in columns.items() if 'PRIMARY' not in col_type]
    csv_ex = [names] + text
    csv_ex = '\n'.join([sep.join(map(str, r)) for r in csv_ex])
    prompt = (f"Отправьте CSV файл с данными дней рождений, соблюдая требования:"
              f"\n - файл должен быть в кодировке '{enc.upper()}'."
              f"\n - строго соблюдайте количество и порядок полей."
              f"\n - в качестве разделителя полей используйте '{sep}'."
              f"\n - формат даты должен быть dd/mm/yyyy."
              f"\n\nВот пример корректного заполнения:"
              f"\n{csv_ex}")
    return prompt


# General functions
def make_menu(name, config):
    """
    Генерирует меню на основе конфигурации.
    """
    if name not in config:
        return
    level = config[name]
    menu = [
        [Button.inline(text, button.encode('UTF-8')) for item in row for button, text in item.items()]
        for row in level
    ]
    return menu


def get_prompt_from_config(choice, menu):
    """
    Recursively searches for a key in a nested dictionary or list structure.

    Parameters:
    ----------
    choice : str
        The key to search for.
    menu : dict or list
        The nested structure (dictionary or list) to search within.

    Returns:
    -------
    Any
        The value associated with the specified key, or None if not found.
    """
    # Base case: if the key exists at the current level of the dictionary
    if isinstance(menu, dict):
        if choice in menu:
            return menu[choice]
        # Recursively search in values of the dictionary
        for value in menu.values():
            result = get_prompt_from_config(choice, value)
            if result is not None:
                return result

    # If the current level is a list, iterate through its elements
    elif isinstance(menu, list):
        for item in menu:
            result = get_prompt_from_config(choice, item)
            if result is not None:
                return result

    # If no match is found, return None
    return None


async def handle_edit_respond(event, text, buttons, rewrite=True):
    """
    Универсальная функция для отправки или редактирования сообщения.
    Параметры:
        event: событие Telethon (CallbackQuery или NewMessage).
        text: текст сообщения.
        buttons: кнопки для сообщения.
        rewrite: True - редактировать, False - отправить новое сообщение.
    """
    if not rewrite:
        await event.respond(text, buttons=buttons)
    else:
        try:
            await event.edit(text, buttons=buttons)
        except Exception as e:
            logger.error(f"Не удалось отредактировать сообщение: {e}")
            await event.respond(text, buttons=buttons)


async def init_user(user_id):
    user_data[user_id] = {}
    user_data[user_id]['operator']: Operator = Operator(user_id)
    await drop_user_state(user_id)


async def drop_user_state(user_id):
    user_data[user_id]['state'] = None
    user_data[user_id].pop('waited_param_name', None)
    user_data[user_id]['params'] = {}


async def ask_for_input(event, user_id, param_name, prompt_text):
    """
    Запрашивает у пользователя ввод данных (3 уровень).
    """
    user_data[user_id]['waited_param_name'] = param_name  # Запоминаем, какой параметр ожидается
    await event.edit(prompt_text)


async def handle_data_entry(event, user_id):
    """
    Обрабатывает введенные данные на 3 уровне.
    """
    param_name = user_data[user_id].get('waited_param_name')
    if param_name:
        user_data[user_id]['params'][param_name] = event.raw_text  # Сохраняем введенные данные
        buttons = [
            [Button.inline("Принять", b"accept_input")],
            [Button.inline("Отменить", b"cancel_input")]
        ]
        await event.respond(f"Вы ввели: {event.raw_text}. Подтвердите или отмените:", buttons=buttons)


# Menu functions
async def show_start_menu(event, user_id, rewrite=True):
    """
    Показывает главное меню (1 уровень).
    """
    # перед выводом главного меню сбрасываем состояние пользователя до изначального
    await drop_user_state(user_id)
    menu = make_menu("start_menu", TELETHON_API)
    await handle_edit_respond(event, "Выберите опцию:", buttons=menu, rewrite=rewrite)


async def show_add_record_menu(event, user_id, rewrite=True):
    """
    Показывает меню 2 уровня для ввода данных.
    """
    menu = make_menu("add_record_menu", TELETHON_API)
    await handle_edit_respond(event, "Выберите поле для ввода данных:", buttons=menu, rewrite=rewrite)


async def validate_record(event, user_id):
    user_info = user_data[user_id].get('params', {})
    if 'birth_date' in user_info or user_data[user_id]['state'] == 'update_record_by_id_state':
        result = "\n".join(f"{key}: {value}" for key, value in user_info.items())
        await event.edit(f"Введенные данные:\n{result}")
        # Очищаем данные пользователя

    else:
        await event.edit(f"Вы не заполнили обязательное поле.")
        msg = await client.send_message(event.chat_id, f'Вы не заполнили обязательное поле.', buttons=None)
        prompt = f"Введите {get_prompt_from_config('birth_date', TELETHON_API)}"
        await ask_for_input(msg, user_id, 'birth_date', prompt)


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    """
    Обрабатывает команду /start и показывает главное меню.
    """
    user_id = event.sender_id
    await init_user(user_id)
    await show_start_menu(event, user_id)


@client.on(events.CallbackQuery)
async def handle_callback(event):
    """
    Обрабатывает нажатия кнопок меню. Ключевая точка входа для пользователя.
    Пользователь выбирает пункт меню - тип данных, которые он будет вводить.
    Этот тип запоминается в state и на основе state ответы пользователя сохраняются в базу
    функцией handle_text.

    """
    user_id = event.sender_id
    if user_id not in user_data:
        await init_user(user_id)

    data = event.data.decode('utf-8')

    operator: Operator = user_data[user_id]['operator']

    match data:

        # start menu
        case "add_record":
            user_data[user_id]['state'] = "add_record_state"
            await show_add_record_menu(event, user_id)

        case "back_to_start":
            await show_start_menu(event, user_id)

        # record_by_id
        case "update_record_by_id":
            user_data[user_id]['state'] = "update_record_by_id_state"

            await ask_for_input(
                event,
                user_id,
                'record_id',
                f"Введите id записи которую хотите отредактировать."
            )

        case "delete_record_by_id":
            user_data[user_id]['state'] = "delete_record_by_id_state"

            await ask_for_input(
                event,
                user_id,
                'record_id',
                f"Введите id записи которую хотите удалить."
            )

        # import / export
        case "import_csv":
            user_data[user_id]['state'] = "import_csv_state"
            await ask_for_input(
                event,
                user_id,
                'import_csv',
                get_csv_prompt()
            )

        case "export_csv":
            user_data[user_id]['state'] = "export_csv_state"

            file = operator.export_data()
            if file:
                caption = "Вот файл с вашими данными в формате CSV."
                await client.send_file(event.chat_id, file, caption=caption)
            else:
                caption = f"Не удалось выгрузить файл, "
                f"обратитесь за помощью к разработчикам."
                await client.send_message(user_id, caption)

        case "delete_user":
            # TODO Добавить удаление данных пользователя по id из базы
            await event.edit("Ваши данные удалены.")
            await show_start_menu(event, user_id)

        # add_record_menu
        case "company" | "position" | "gift_category" | "first_name" | "last_name" | \
             "birth_date" | "notice_before_days" as choice:
            prompt = f"Введите {get_prompt_from_config(choice, TELETHON_API)}"
            await ask_for_input(event, user_id, choice, prompt)

        case "confirm_record":
            await validate_record(event, user_id)
            caption = DEFAULT_CAPTION
            match user_data[user_id]['state']:
                case "add_record_state":
                    caption = operator.add_record(
                        **user_data[user_id]['params']
                    )
                case "update_record_by_id_state":
                    caption = operator.update_record_by_id(
                        **user_data[user_id]['params']
                    )

            await client.send_message(user_id, caption)

            await show_start_menu(event, user_id, rewrite=False)

        # case "accept_input":
        #     await show_add_record_menu(event, user_id)

        case "cancel_input":
            param_name = user_data[user_id].get('waited_param_name')
            if param_name:
                user_data[user_id]['params'].pop(param_name, None)  # Удаляем текущее значение
            await ask_for_input(event, user_id, param_name, f"Введите {param_name} снова:")


@client.on(events.NewMessage)
async def handle_text(event):
    """
    Обрабатывает вводимые пользователем ответы для всех уровней меню,
     используя state для определения текущего состояния меню.
    """
    user_id = event.sender_id

    if user_id not in user_data:
        await init_user(user_id)

    operator: Operator = user_data[user_id]['operator']

    match user_data[user_id]['state']:
        case 'add_record_state':
            waited_param_name = user_data[user_id].pop('waited_param_name', None)
            user_data[user_id]['params'][waited_param_name] = event.raw_text
            await show_add_record_menu(event, user_id)

        case 'update_record_by_id_state':
            waited_param_name = user_data[user_id].pop('waited_param_name', None)
            user_data[user_id]['params'][waited_param_name] = event.raw_text
            await show_add_record_menu(event, user_id)

        case 'delete_record_by_id_state':
            # waited_param_name = user_data[user_id].pop('waited_param_name', None)
            # user_data[user_id]['params'][waited_param_name] = event.raw_text

            record_id = event.raw_text
            caption = operator.delete_record_by_id(record_id)
            await client.send_message(event.chat_id, caption)
            await drop_user_state(user_id)

        case 'import_csv_state':
            response = await save_csv_file(event)
            msg = await event.respond(response)
            file = user_data[user_id]['params']['csv']
            print('TELEGA',str(file))
            if file:
                text = operator.import_data(file)
                msg = await msg.respond(text)

        case 'export_csv_state':
            # export CSV обрабатывается в CallBack
            pass

        case 'delete_user_state':
            # delete_user_state обрабатывается в CallBack
            pass
        case _:
            pass


def main():
    """
    The main entry point for running the Telegram bot.
    """

    client.start(bot_token=CONFIG.telethon_api_settings.get('bot_token'))
    logger.info("Telegram bot is running.")
    client.run_until_disconnected()


if __name__ == "__main__":
    main()
