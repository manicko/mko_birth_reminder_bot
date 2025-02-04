import logging
import asyncio
from telethon import TelegramClient, events, Button
from mko_birth_reminder_bot.reminder import start_scheduler, check_missed_run
from mko_birth_reminder_bot.core import CONFIG, DB_CONNECTION
from mko_birth_reminder_bot.operator import Operator

logger = logging.getLogger(__name__)

client = TelegramClient(**CONFIG.TELETHON_API.client)
user_data = {} # Dictionary for temporary user data storage
running = True # Flag to track bot status
DEFAULT_CAPTION = "Repeat the attempt by entering the /start command."


async def save_csv_file(event,user_id, upload_dir: str = CONFIG.CSV.READ_DATA.path):
    """
    Saves a user-uploaded CSV file to the specified directory.

    The file path is stored in `user_data[user_id]['params']['csv']`.

    Args:
        event (telethon.events.NewMessage.Event): The event triggered by the user's file upload.
        upload_dir (str, optional): The directory path where the file should be saved. Defaults to CONFIG.CSV.READ_DATA.path.

    Returns:
        str: A message indicating success or an error.
    """

    user_data[user_id]['params']['csv'] = None
    if event.file and event.file.mime_type == "text/csv":
        try:
            # Save the file
            user_data[user_id]['params']['csv'] = await event.download_media(file=upload_dir)
            return "File successfully saved. Proceeding with data loading."
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            return f"Error saving file: {e}"
    else:
        return "Error: Please upload a CSV file."


def get_csv_prompt(columns: dict = CONFIG.DATABASE.columns,
                   sep: str = CONFIG.CSV.READ_DATA.from_csv["sep"],
                   enc: str = CONFIG.CSV.READ_DATA.from_csv["encoding"]):
    """
    Generates a prompt with instructions for uploading a CSV file.

    Args:
        columns (dict, optional): Database column configuration.
        sep (str, optional): CSV separator character.
        enc (str, optional): File encoding format.

    Returns:
        str: Formatted instruction text for uploading a CSV file.
    """

    example_data_ru = [["ОАО Зета", "Соколова", "Анна", "Кадры", "1-я категория", "1995-04-18", 7],
            ["ПАО Эта", "Козлов", "Иван", "Генеральный директор", "VIP", "1978-09-23", 30]]
    example_data = [["Company A", "Smith", "John", "HR", "Manager", "1995-04-18", 7],
                    ["Company B", "Doe", "Jane", "CEO", "VIP", "1980-09-15", 30]]

    column_names = [col_name for col_name, col_type in columns.items() if 'PRIMARY' not in col_type]
    csv_example = [column_names] + example_data
    csv_example_str = '\n'.join([sep.join(map(str, row)) for row in csv_example])
    prompt = (f"📄 **Upload a CSV file with birthday data, following these requirements:**"
              f"\n        - File encoding must be `'{enc.upper()}'`"
              f"\n        - Keep the number and order of fields strictly"
              f"\n        - Use `'{sep}'` as a field separator"
              f"\n        - Date format must be `'dd/mm/yyyy'` or `'dd.mm.yyyy'`"
              f"\n\n❗ **If you are using a previously exported file:**"
              f"\n        - Remove the `id` column"
              f"\n        - Clear records before importing to avoid duplicates"
              f"\n\n💡 **Example of correct formatting:**"
              f"```{csv_example_str}```")
    prompt_ru = (f"📄 **Отправьте CSV файл с данными дней рождений, соблюдая требования:**"
              f"\n        - файл должен быть в кодировке `'{enc.upper()}'`"
              f"\n        - строго соблюдайте количество и порядок полей"
              f"\n        - в качестве разделителя полей используйте `'{sep}'`"
              f"\n        - формат даты должен быть `'dd/mm/yyyy'` или `'dd.mm.yyyy'`"
              f"\n\n❗️ **Если для загрузки вы используете ранее выгруженный файл:**"
              f"\n        - удалите столбец `id`\n"
              f"\n        - очистите записи перед загрузкой, чтобы они не дублировались"
              f"\n\n💡 **Вот пример корректного заполнения:**"
              f"```{csv_example_str}```")
    return prompt


# General functions
def make_menu(name, config)->list[list[Button]]:
    """
    Generates a button menu based on the given configuration.

    Args:
        name (str): The name of the menu section.
        config (dict): The menu configuration dictionary.

    Returns:
        list[list[Button]]: A list of inline buttons for the menu, or None if not found.
    """
    if name not in config:
        return None
    level = config[name]
    return [
        [Button.inline(text, button.encode('UTF-8')) for item in row for button, text in item.items()]
        for row in level
    ]


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


async def handle_edit_respond(event, text, buttons=None, rewrite=True):
    """
    Sends or edits a message dynamically.

    If `rewrite` is True and the original message was sent by the bot, it attempts to edit it.
    Otherwise, a new message is sent.

    Args:
        event (telethon.events.CallbackQuery.Event or telethon.events.NewMessage.Event): The event triggering the response.
        text (str): The message text.
        buttons (list[list[Button]], optional): Inline buttons for the message. Defaults to None.
        rewrite (bool, optional): If True, attempts to edit the existing message. Defaults to True.
    """
    # Check if event is message and if the message was sent by the bot
    if rewrite and hasattr(event, 'message') and event.message.out:
        try:
            await event.edit(text, buttons=buttons)
            return
        except Exception as e:
            logger.error(f"Failed to edit message: {e}")
    # Send a new message if editing failed or rewrite is False
    await event.respond(text, buttons=buttons)


async def init_user(user_id):
    """Initializes user data."""
    user_data[user_id] = {'state': None, 'params': {}}


async def drop_user_state(user_id):
    """Resets the user's state."""
    if user_id in user_data:
        user_data[user_id]['state'] = None
        user_data[user_id].pop('waited_param_name', None)
        user_data[user_id]['params'] = {}


async def ask_for_input(event, user_id, param_name, prompt_text):
    """
    Requests user input for a specific parameter.

    The requested parameter is stored in `user_data[user_id]['waited_param_name']`.

    Args:
        event (telethon.events.NewMessage.Event): The event triggering the request.
        user_id (int): The Telegram user ID.
        param_name (str): The parameter name that is being requested.
        prompt_text (str): The text prompt to be sent to the user.

    Returns:
        None
    """
    if user_id not in user_data:
        logger.error(f"User ID {user_id} not found while requesting input.")
        prompt_text = "Unexpected error. Please try again from the /start command."

    user_data[user_id]['waited_param_name'] = param_name  # Store the expected parameter
    await handle_edit_respond(event, prompt_text)



async def handle_data_entry(event, user_id: int):
    """
    Processes user input at level 3 of the menu.

    Args:
        event (telethon.events.NewMessage.Event): The event containing user input.
        user_id (int): The Telegram user ID.

    Returns:
        None
    """
    if user_id not in user_data:
        logger.error(f"User ID {user_id} not found while handling data entry.")
        return

    param_name = user_data[user_id].get('waited_param_name')
    if param_name:
        user_data[user_id]['params'][param_name] = event.raw_text  # Save the entered data
        buttons = [
            [Button.inline("Accept", b"accept_input")],
            [Button.inline("Cancel", b"cancel_input")]
        ]
        await event.respond(f"You entered: {event.raw_text}. Confirm or cancel:", buttons=buttons)


# Menu functions
async def show_start_menu(event, user_id: int, rewrite: bool = True):
    """
    Displays the main menu and resets user state.

    Args:
        event (telethon.events.NewMessage.Event): The event triggering the menu display.
        user_id (int): The Telegram user ID.
        rewrite (bool, optional): If True, attempts to edit the existing message; otherwise, sends a new one. Defaults to True.

    Returns:
        None
    """
    await drop_user_state(user_id)
    menu = make_menu("start", CONFIG.TELETHON_API.menu)
    if menu:
        await handle_edit_respond(event, "Select an option:", buttons=menu, rewrite=rewrite)
    else:
        logger.error("Start menu not found in configuration.")


async def show_add_record_menu(event, rewrite: bool = True):
    """
    Displays the second-level menu for data entry.

    Args:
        event (telethon.events.NewMessage.Event): The event triggering the menu display.
        rewrite (bool, optional): If True, attempts to edit the existing message; otherwise, sends a new one. Defaults to True.

    Returns:
        None

    Raises:
        ValueError: If the add record menu is not found in the configuration.
    """
    menu = make_menu("add_record", CONFIG.TELETHON_API.menu)
    if menu:
        await handle_edit_respond(event, "Select a field to enter data:", buttons=menu, rewrite=rewrite)
    else:
        raise ValueError("Add record menu not found in the configuration file.")


async def validate_record(event, user_id):
    """
    Validates the user's input record and prompts for missing fields if necessary.

    This function checks whether the required `birth_date` field is present in the user's data.
    If it is missing, the function prompts the user to enter it. Otherwise, it displays the
    entered data.

    Args:
        event (Union[telethon.events.NewMessage.Event, telethon.events.CallbackQuery.Event]):
            The event associated with the user input.
        user_id (int): The Telegram user ID.

    Returns:
        None: The function interacts with the user via messages but does not return a value.
    """
    user_info = user_data[user_id].get('params', {})

    if 'birth_date' in user_info or user_data[user_id]['state'] == 'update_record_by_id_state':
        result = "\n".join(f"{key}: {value}" for key, value in user_info.items())
        await handle_edit_respond(event, text=f"Entered data:\n{result}", rewrite=True)
    else:
        await handle_edit_respond(event, text="You did not fill in the required field.", rewrite=True)

        msg = await client.send_message(
            event.chat_id,
            "You did not fill in the required field.",
            buttons=None
        )

        prompt = f"Enter {get_prompt_from_config('birth_date', CONFIG.TELETHON_API)}"
        await ask_for_input(msg, user_id, 'birth_date', prompt)


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    """Handles the /start command and shows the main menu."""
    user_id = event.sender_id
    await init_user(user_id)
    await show_start_menu(event, user_id)

# noinspection PyTypeChecker
@client.on(events.CallbackQuery)
async def handle_callback(event):
    """
    Handles menu button presses.
    """

    user_id = event.sender_id
    if user_id not in user_data:
        await init_user(user_id)

    data = event.data.decode('utf-8')
    operator: Operator = Operator(user_id)

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

            file = await asyncio.to_thread(operator.export_data)
            if file:
                caption = "Вот файл с вашими данными в формате CSV."
                await client.send_file(event.chat_id, file, caption=caption)
                await asyncio.to_thread(operator.remove_tmp_file, file)
            else:
                caption = f"Не удалось выгрузить файл, "
                f"обратитесь за помощью к разработчикам."
                await client.send_message(user_id, caption)

        case "delete_user":
            await asyncio.to_thread(operator.flush_data)
            await event.edit("Your data has been deleted.")
            await show_start_menu(event, user_id, rewrite=False)

        # add_record_menu
        case "company" | "position" | "gift_category" | "first_name" | "last_name" | \
             "birth_date" | "notice_before_days" as choice:
            prompt = f"Введите {get_prompt_from_config(choice, CONFIG.TELETHON_API)}"
            await ask_for_input(event, user_id, choice, prompt)

        case "confirm_record":
            await validate_record(event, user_id)
            caption = DEFAULT_CAPTION
            match user_data[user_id]['state']:
                case "add_record_state":
                    caption = await asyncio.to_thread(
                        operator.add_record, **user_data[user_id]['params']
                    )
                case "update_record_by_id_state":
                    caption = await asyncio.to_thread(
                        operator.update_record_by_id,
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


# noinspection PyTypeChecker
@client.on(events.NewMessage)
async def handle_text(event):
    """
    Обрабатывает вводимые пользователем ответы для всех уровней меню,
     используя state для определения текущего состояния меню.
    """

    user_id = event.sender_id

    if user_id not in user_data:
        await init_user(user_id)

    operator: Operator = Operator(user_id)

    match user_data[user_id]['state']:
        case 'add_record_state' if 'waited_param_name' in user_data[user_id]:
            waited_param_name = user_data[user_id].pop('waited_param_name', None)
            user_data[user_id]['params'][waited_param_name] = event.raw_text
            await show_add_record_menu(event, user_id)

        case 'update_record_by_id_state' if 'waited_param_name' in user_data[user_id]:
            waited_param_name = user_data[user_id].pop('waited_param_name', None)
            user_data[user_id]['params'][waited_param_name] = event.raw_text
            await show_add_record_menu(event, user_id)

        case 'delete_record_by_id_state':
            record_id = event.raw_text
            caption = await asyncio.to_thread(operator.delete_record_by_id, record_id)
            await client.send_message(event.chat_id, caption)
            await drop_user_state(user_id)

        case 'import_csv_state':
            response = await save_csv_file(event,user_id)
            msg = await event.respond(response)
            file = user_data[user_id]['params']['csv']

            if file:
                text = await asyncio.to_thread(operator.import_data,file)
                msg = await msg.respond(text)

        case 'export_csv_state':
            # export CSV обрабатывается в CallBack
            pass

        case 'delete_user_state':
            # delete_user_state обрабатывается в CallBack
            pass
        case _:
            pass


async def run_tg_bot():
    """
    Starts the Telegram bot and its scheduler.

    This function initializes and runs the Telegram bot using the Telethon library.
    It also starts the scheduled tasks associated with the bot. The function keeps running
    until the global `running` flag is set to False.
    """
    global running

    await client.start(bot_token=CONFIG.TELETHON_API.bot_token)
    logger.info("Telegram bot is running.")

    # Start scheduler
    await start_scheduler(client)
    await check_missed_run(client)

    try:
        while running:
            await asyncio.sleep(1)  # Keeps the bot running
    except asyncio.CancelledError:
        pass  # Allows graceful exit if cancelled externally

    # Shutdown process
    await stop_tg_bot()


async def stop_tg_bot():
    """
    Gracefully stops the Telegram bot and its scheduler.

    This function stops the bot, commits and closes the database connection,
    and ensures a clean shutdown.
    """
    global running
    running = False

    try:
        if DB_CONNECTION:
            DB_CONNECTION.commit()
            DB_CONNECTION.close()
            logger.info("Database connection closed.")
    except Exception as e:
        logger.error(f"Error closing the database: {e}")

    await client.disconnect()
    logger.info("Telegram bot has been stopped.")


if __name__ == "__main__":
    asyncio.run(run_tg_bot())
