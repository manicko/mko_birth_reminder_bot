import logging
import asyncio
from collections import defaultdict
from time import time
from telethon import TelegramClient, events, Button
from telethon.events import StopPropagation
from mko_birth_reminder_bot.reminder import start_scheduler, check_missed_run
from mko_birth_reminder_bot.core import CONFIG, DB_CONNECTION
from mko_birth_reminder_bot.operator import Operator

logger = logging.getLogger(__name__)


client = None
bot = None
bot_id = 0
user_data = {}  # Dictionary for temporary user data storage
user_request_times = defaultdict(list)  # {user_id: [timestamps]}
running = True  # Flag to track bot status
UNEXPECTED_ERROR_CAPTION = "Unexpected error. Repeat the attempt by entering the /start command."

try:
    client = TelegramClient(**CONFIG.TELETHON_API.client)
except ValueError as error:
    logger.error(f"Error while connecting to Telegram: {error}. "
                 f"Please ensure the secrets config is filed in and correct.")


def get_menu_buttons_list(name:str, config:dict[str:str]) -> list[str]:
    """ Generates Telethon menu buttons list from configuration."""
    level = config.get(name, [])
    return [button for row in level for item in row for button in item.keys()]


def pattern_from_list(buttons:list[str]) -> str:
    """Creates pattern for the Telethon client.on() events filters, from the list of commands"""
    return f"^({'|'.join(buttons)})$"


def get_menu_pattern(name, config=CONFIG.TELETHON_API.menu) -> str:
    """Creates pattern for the Telethon client.on() events filters, from the config basing on the name of the menu"""
    buttons = get_menu_buttons_list(name, config)
    return pattern_from_list(buttons)


async def handle_waited_param(event, user_id):
    """Handles user input when adding, updating a new record."""
    waited_param_name = user_data[user_id].pop("waited_param_name", None)
    if waited_param_name:
        user_data[user_id]["params"][waited_param_name] = event.raw_text
        await show_record_menu(event, user_id)


async def handle_confirm_data(event, user_id):
    """Handles data confirmation."""
    is_valid = await validate_record(event, user_id)
    if not is_valid:
        return
    operator: Operator = Operator(user_id)
    state = user_data[user_id].get("state")
    try:
        if state == "add_record":
            caption = await asyncio.to_thread(operator.add_record, **user_data[user_id]["params"])
        elif state == "update_record_by_id":
            caption = await asyncio.to_thread(operator.update_record_by_id, **user_data[user_id]["params"])
        else:
            logger.error(f"Unexpected state: {state}")
            caption = UNEXPECTED_ERROR_CAPTION
    except Exception as e:
        logger.error(f"Error in state: {state}, while processing record. {e}")
        caption = UNEXPECTED_ERROR_CAPTION

    await client.send_message(user_id, caption)
    await show_start_menu(event, user_id, rewrite=False)


async def handle_delete_record(event, user_id):
    """Handles user input when deleting a record."""
    record_id = event.raw_text.strip()

    if not record_id.isdigit():
        await event.respond("⚠️ Invalid ID format. Please enter a valid number.")
        return

    operator: Operator = Operator(user_id)
    caption = await asyncio.to_thread(operator.delete_record_by_id, record_id)
    await client.send_message(event.chat_id, caption)
    await show_start_menu(event, user_id, rewrite=False)


async def handle_import_csv(event, user_id):
    """Handles CSV file import."""
    response = await save_csv_file(event, user_id)
    msg = await event.respond(response)

    file = user_data[user_id]["params"].get("csv")
    if not file:
        await msg.respond("⚠️ No file found. Please upload a CSV file.")
        return

    operator: Operator = Operator(user_id)
    text = await asyncio.to_thread(operator.import_data, file)
    await msg.respond(text)
    await show_start_menu(event, user_id, rewrite=False)


async def save_csv_file(event, user_id: int, upload_dir: str = CONFIG.CSV.READ_DATA.path):
    """
    Saves a user-uploaded CSV file to the specified directory.

    The file path is stored in `user_data[user_id]['params']['csv']`.

    Args:
        event (telethon.events.NewMessage.Event): The event triggered by the user's file upload.
        user_id (int): The Telegram user ID.
        upload_dir (str, optional): The directory path where the file should be saved.
            Defaults to `CONFIG.CSV.READ_DATA.path`.

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


# General functions
def make_menu(name, config) -> list[list[Button]] | None:
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


async def get_event_message(event):
    """
    Safely retrieves the message associated with the event.

    Args:
        event (telethon.events.CallbackQuery.Event or telethon.events.NewMessage.Event):
            The event triggering the response.

    Returns:
        telethon.tl.custom.message.Message or None: The retrieved message or None if not found.
    """
    if isinstance(event, events.CallbackQuery.Event):
        return await event.get_message()  # Fetch message from server if necessary
    return getattr(event, "message", None)


async def handle_edit_respond(event, text=None, buttons=None, rewrite=True):
    """
    Sends or edits a message dynamically.

    If `rewrite` is True and the original message was sent by the bot, it attempts to edit it.
    If editing fails or `remove_old_buttons` is True, sends a new message.

    Args:
        event (telethon.events.NewMessage.Event or telethon.events.CallbackQuery.Event):
            The event triggering the response.
        text (str, optional): The message text. Defaults to None.
        buttons (list[list[Button]], optional): Inline buttons for the message. Defaults to None.
        rewrite (bool, optional): If True, attempts to edit the existing message. Defaults to True.

    Returns:
        telethon.tl.custom.message.Message: The sent or edited message object.
    """
    # Get bot information once per function call
    message = await get_event_message(event)  # Safe message retrieval

    if rewrite and message and message.sender_id == bot_id:
        try:
            return await message.edit(text=text, buttons=buttons)
        except Exception as e:
            logger.warning(f"Editing failed, sending new message: {e}")

    return await event.respond(text, buttons=buttons)


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
        event (telethon.events.NewMessage.Event or telethon.events.CallbackQuery.Event or telethon.tl.custom.message.Message):
            The event triggering the response or a sent message object.
        user_id (int): The Telegram user ID.
        param_name (str): The parameter name that is being requested.
        prompt_text (str): The text prompt to be sent to the user.

    Returns:
        None
    """
    if user_id not in user_data:
        logger.error(f"User ID {user_id} not found while requesting input.")
        prompt_text = UNEXPECTED_ERROR_CAPTION

    user_data[user_id]['waited_param_name'] = param_name  # Store the expected parameter
    await handle_edit_respond(event, prompt_text)


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


async def show_record_menu(event, rewrite: bool = True):
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


async def validate_record(event, user_id) -> bool:
    """
    Validates the user's input record and prompts for missing fields if necessary.

    This function checks whether the required `birth_date` field is present in the user's data.
    - If `birth_date` exists or the user is in the `update_record_by_id_state`, the function displays
      the entered data and returns `True`.
    - If `birth_date` is missing, the function prompts the user to enter it and returns `False`.

    Args:
        event (Union[telethon.events.NewMessage.Event, telethon.events.CallbackQuery.Event]):
            The event associated with the user input.
        user_id (int): The Telegram user ID.

    Returns:
        bool: True if the record is complete, False if additional input is required.
    """
    user_info = user_data[user_id].get('params', {})

    if 'birth_date' in user_info or user_data[user_id]['state'] == 'update_record_by_id':
        result = "\n".join(f"{key}: {value}" for key, value in user_info.items())
        await handle_edit_respond(event, text=f"Entered data:\n{result}", rewrite=True)
        return True
    else:
        prompt = f"You did not fill in the required field: {get_prompt_from_config('birth_date', CONFIG.TELETHON_API.menu)}"
        await handle_edit_respond(event, text=prompt, rewrite=True)
        await show_record_menu(event, rewrite=False)
        return False


async def is_throttled(user_id: int, command: str) -> bool:
    """Checks if the user is sending too many requests and applies rate limiting.

    Args:
        user_id (int): Telegram user ID.
        command (str): The command or event name (e.g. "/start", "callback").

    Returns:
        bool: True if throttled, False otherwise.
    """
    now = time()

    max_requests, period = CONFIG.TELETHON_API.throttle_limits.get(command, (5, 10))  # Default: 5 in 10 sec
    request_times = user_request_times[user_id]

    # Remove outdated requests
    user_request_times[user_id] = [t for t in request_times if now - t < period]

    if len(user_request_times[user_id]) >= max_requests:
        return True

    user_request_times[user_id].append(now)
    return False


async def request_id(event, user_id):
    """ Helper function to request ID of the record to be deleted or modified"""
    await ask_for_input(
        event,
        user_id,
        param_name='record_id',
        prompt_text="Enter the ID of the record."
    )


async def request_csv(event, user_id):
    """ Helper function to request import of the CSV file with records."""
    await ask_for_input(
        event,
        user_id,
        param_name='import_csv',
        prompt_text=CONFIG.MSG.help_import
    )


async def handle_export_csv(event, user_id):
    """Handles CSV export."""
    operator: Operator = Operator(user_id)
    file = await asyncio.to_thread(operator.export_data)
    if file:
        await client.send_file(event.chat_id, file, caption="Here is your data file in CSV format.")
        await asyncio.to_thread(operator.remove_tmp_file, file)
    else:
        await client.send_message(user_id, "Failed to export the file. Please contact the developers for assistance.")


async def delete_all_records(event, user_id):
    """Handles deleting all user records."""
    operator: Operator = Operator(user_id)
    await asyncio.to_thread(operator.flush_data)
    await handle_edit_respond(event, text="All your data has been deleted.", rewrite=True)
    await show_start_menu(event, user_id, rewrite=False)


async def delete_user(event, user_id):
    """Handles deleting all user records."""
    operator: Operator = Operator(user_id)
    await asyncio.to_thread(operator.del_info)
    await handle_edit_respond(
        event=event,
        text="All your data has been deleted, "
             "and you have been successfully unsubscribed.",
        rewrite=True
    )


async def default_handler(event, user_id):
    """Handles unexpected states."""
    logger.warning(f"Unexpected state for user {user_id}")
    await event.respond("⚠️ Please read /help and use /start command to get the main menu.")
    # await show_start_menu(event, user_id, rewrite=False)


# noinspection PyTypeChecker
@client.on(events.NewMessage)
async def throttle_filter_text(event):
    """
    Throttle filter for all incoming messages.

    Args:
        event (telethon.events.NewMessage.Event): The incoming event.

    Returns:
        None: The function either stops propagation or forwards the event.
    """
    user_id = event.sender_id
    #  Throttling (antispam)
    if await is_throttled(user_id, "text"):
        await event.respond("⏳ Too many actions! Please wait a moment.")
        raise StopPropagation


# noinspection PyTypeChecker
@client.on(events.CallbackQuery)
async def throttle_filter_callback(event):
    """
    Throttle filter for all CallbackQuery events.

    Args:
        event (telethon.events.CallbackQuery.Event): The incoming event.

    Returns:
        None: The function either stops propagation or forwards the event.
    """
    user_id = event.sender_id

    #  Throttling (antispam)
    if await is_throttled(user_id, "callback"):
        await event.answer("⏳ Too many actions! Please wait a moment.", alert=True)
        raise StopPropagation


# noinspection PyTypeChecker
@client.on(events.CallbackQuery(
    pattern=get_menu_pattern('start')))
async def handle_start_menu_callback(event):
    """
    Handles start menu button clicks in the Telegram bot menu.

    Args:
        event (telethon.events.CallbackQuery.Event): The event triggered by a button press.

    Returns:
        None
    """

    user_id = event.sender_id

    if user_id not in user_data:
        await init_user(user_id)

    callback = event.data.decode("utf-8")

    # keeping state for the user
    user_data[user_id]['state'] = callback

    match callback:
        case "add_record":
            await show_record_menu(event, user_id)
        case "update_record_by_id":
            await request_id(event, user_id)
        case "delete_record_by_id":
            await request_id(event, user_id)
        case "import_csv":
            await request_csv(event, user_id)
        case "export_csv":
            await handle_export_csv(event, user_id)
        case "delete_all_records":
            await delete_all_records(event, user_id)
        case "delete_user":
            await delete_user(event, user_id)
        case _:
            logger.error(f"Unexpected callback: {callback}")
    raise StopPropagation


@client.on(events.CallbackQuery(data=b"confirm_data"))
async def handle_confirm_data_callback(event):
    """
    Handles confirm_data button clicks in the Telegram bot menu.
    Args:
        event (telethon.events.CallbackQuery.Event): The event triggered by a button press.

    Returns:
        None
    """
    user_id = event.sender_id
    await handle_confirm_data(event, user_id)
    raise StopPropagation


@client.on(events.CallbackQuery(data=b"birth_date"))
async def handle_birth_day_callback(event):
    """
    Handles birth_date button clicks in the Telegram bot menu.
    Args:
        event (telethon.events.CallbackQuery.Event): The event triggered by a button press.

    Returns:
        None
    """
    choice = event.data.decode("utf-8")
    user_id = event.sender_id
    prompt = get_prompt_from_config(choice, CONFIG.TELETHON_API.menu)
    prompt = f"Send me {prompt}"
    prompt += "\nFormat: dd/mm/yyyy (e.g. 01/03/2000)"
    await ask_for_input(event, user_id, "birth_date", prompt)
    raise StopPropagation


@client.on(
    events.CallbackQuery(
        pattern=pattern_from_list(
            ["company", "position", "gift_category",
             "first_name", "last_name", "notice_before_days"]
        )))
async def handle_record_menu_callback(event):
    """
    Handles record fields entry button clicks in the Telegram bot menu.
    Args:
        event (telethon.events.CallbackQuery.Event): The event triggered by a button press.

    Returns:
        None
    """
    user_id = event.sender_id
    choice = event.data.decode("utf-8")
    prompt = get_prompt_from_config(choice, CONFIG.TELETHON_API.menu)
    prompt = f"Send me {prompt}"
    await ask_for_input(event, user_id, choice, prompt)
    raise StopPropagation


@client.on(events.NewMessage(pattern="/start"))
async def start(event):
    """Handles the /start command and shows the main menu.

    Args:
        event (telethon.events.NewMessage.Event): The event triggered by a button press.

    Returns:
        None
    """
    user_id = event.sender_id

    await init_user(user_id)
    await show_start_menu(event, user_id)
    raise StopPropagation


@client.on(events.NewMessage(pattern="/help"))
async def help_command(event):
    """Handles the /help command and sends the help message."""
    await event.respond(CONFIG.MSG.help)
    raise StopPropagation


@client.on(events.NewMessage())
async def handle_text(event):
    """
    Handles user text input at all menu levels.

    Args:
        event (telethon.events.NewMessage.Event):
        The event triggered by a user's text message.

    Returns:
        None
    """

    user_id = event.sender_id

    if user_id not in user_data:
        await init_user(user_id)

    match user_data[user_id]['state']:
        case "add_record":
            await handle_waited_param(event=event, user_id=user_id)
        case "update_record_by_id":
            await handle_waited_param(event=event, user_id=user_id)
        case "delete_record_by_id":
            await handle_delete_record(event=event, user_id=user_id)
        case "import_csv":
            await handle_import_csv(event=event, user_id=user_id)
        case _:
            await default_handler(event=event, user_id=user_id)

async def run_tg_bot():
    """
    Starts the Telegram bot and its scheduler.

    This function initializes and runs the Telegram bot using the Telethon library.
    It also starts the scheduled tasks associated with the bot. The function keeps running
    until the global `running` flag is set to False.
    """
    global running, bot, bot_id
    await client.start(bot_token=CONFIG.TELETHON_API.bot_token)
    bot = await client.get_me()
    bot_id = bot.id
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
