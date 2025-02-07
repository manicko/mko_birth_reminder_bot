import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Union
from mko_birth_reminder_bot.core.utils import list_files_in_directory
from functools import reduce

logger = logging.getLogger(__name__)


def load_config(path: Path) -> Dict[str, Any]:
    """
    Loads configuration from a YAML file.

    Args:
        path (Path): Path to the YAML configuration file.

    Returns:
        Dict[str, Any]: Parsed configuration dictionary, or an empty dict if the file does not exist or is invalid.
    """
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(source: Path, destination: Path) -> None:
    """
    Saves configuration from one YAML file to another.

    Args:
        source (Path): Source YAML file path.
        destination (Path): Destination YAML file path.

    Raises:
        OSError: If an error occurs while reading or writing the file.
    """
    try:
        source = Path(source)
        destination = Path(destination)

        # Ensure the destination directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        data = load_config(source)

        with destination.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
    except OSError as e:
        logger.error(f"Failed to save config from {source} to {destination}: {e}")


def merge_dicts(dict1: Dict[Any, Any], dict2: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Recursively merges two dictionaries.

    Args:
        dict1 (dict): The first dictionary.
        dict2 (dict): The second dictionary.

    Returns:
        dict: Merged dictionary.
    """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict2
    for k in dict2:
        if k in dict1:
            dict1[k] = merge_dicts(dict1[k], dict2[k])
        else:
            dict1[k] = dict2[k]
    return dict1


def ensure_path_exists(path: Path) -> None:
    """
    Ensures that a given path exists, creating directories if necessary.

    Args:
        path (Path): Path to a file or directory.

    Raises:
        ValueError: If the path cannot be created.
    """
    try:
        if path.exists():  # Path already exists
            return
        if path.suffix:  # If it's a file, create its parent directory
            path.parent.mkdir(parents=True, exist_ok=True)
        else:  # If it's a directory, create it
            path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Failed to create path {path}: {e}")


def resolve_path(path: Union[str, Path], base_dir: Union[Path, None] = None) -> Path:
    """
    Resolves an absolute path, creating it if necessary.

    Args:
        path (str | Path): The path to resolve (can be absolute or relative).
        base_dir (Path | None): The base directory to resolve relative paths against.
            Defaults to the module's parent directory.

    Returns:
        Path: The resolved path.

    Raises:
        ValueError: If the path cannot be found or created.
    """
    path = Path(path).expanduser()  # Expands `~` (home directory)

    if path.is_absolute():
        if path.exists():
            return path
        ensure_path_exists(path)  # Create if it doesn't exist
        return path

    # If base_dir is not provided, use the parent directory of this module
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent

    # Resolve the full path
    resolved_path = (base_dir / path).resolve()

    if not resolved_path.exists():
        ensure_path_exists(resolved_path)  # Create the path if it does not exist

    return resolved_path


def read_file(filepath: str | Path) -> str:
    """
    Reads a file and prepares its content for sending.

    The function opens the file using UTF-8 encoding and reads its content.

    Args:
        filepath (str): The path to the Markdown file.

    Returns:
        str: The formatted Markdown text.

    Raises:
        Exception: If an error occurs while reading the file.
    """
    text = ''
    try:
        with open(filepath, encoding="utf-8") as file:
            text = file.read()
    except Exception as e:
        logger.error(f"Error reading file '{filepath}': {e}")
    return text

def get_messages(*paths_to_md: Union[str, Path]) -> Dict[str, str]:
    """
    Retrieves Markdown messages from multiple directories.

    Args:
        paths_to_md (Union[str, Path]): One or more directory paths containing Markdown files.

    Returns:
        Dict[str, str]: A dictionary where keys are file names (without extensions) and values are file contents.
    """
    list_of_files = []
    for path in paths_to_md:
        files = list_files_in_directory(path, ('md',))
        list_of_files.append({f.stem: f for f in files})

    # Merge dictionaries to avoid duplicate keys
    messages = reduce(merge_dicts, list_of_files, {})

    # Read file contents into dictionary
    return {name: read_file(file) for name, file in messages.items()}