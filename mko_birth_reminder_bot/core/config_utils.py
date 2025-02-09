import yaml
import logging
import click
import shutil
from pathlib import Path
from typing import Any, Dict, Union, Callable
from functools import reduce, wraps
from mko_birth_reminder_bot.core.utils import list_files_in_directory

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


def merge_dicts(dict1: Dict[Any, Any], dict2: Dict[Any, Any]) -> Dict[Any, Any]:
    """
    Recursively merges two dictionaries.

    If both dictionaries have the same key and the value is also a dictionary, it merges them recursively.
    Otherwise, `dict2`'s value overwrites `dict1`'s value.

    Args:
        dict1 (Dict[Any, Any]): The first dictionary.
        dict2 (Dict[Any, Any]): The second dictionary.

    Returns:
        Dict[Any, Any]: The merged dictionary.
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
        if path.exists():
            return  # Path already exists, no action needed
        if path.suffix:  # If it's a file, create its parent directory
            path.parent.mkdir(parents=True, exist_ok=True)
        else:  # If it's a directory, create it
            path.mkdir(parents=True, exist_ok=True)
    except OSError as e:
        raise ValueError(f"Failed to create path {path}: {e}")


def resolve_path(path: Union[str, Path], base_dir: Union[Path, None] = None) -> Path:
    """
    Resolves an absolute path, creating it if necessary.

    If a relative path is given, it is resolved against `base_dir`.

    Args:
        path (Union[str, Path]): The path to resolve (can be absolute or relative).
        base_dir (Union[Path, None], optional): The base directory for resolving relative paths.
            Defaults to the parent directory of this script.

    Returns:
        Path: The resolved absolute path.

    Raises:
        ValueError: If the path cannot be found or created.
    """
    path = Path(path).expanduser()  # Expands `~` (home directory)

    # If the path is absolute and exists, return it immediately
    if path.is_absolute():
        if path.exists():
            return path
        ensure_path_exists(path)  # If not found, attempt to create it
        return path

    # Ensure base_dir is a valid Path
    base_dir = base_dir or Path(__file__).resolve().parent.parent
    resolved_path = (base_dir / path).resolve()

    if not resolved_path.exists():
        ensure_path_exists(resolved_path)  # Create the path if it does not exist

    return resolved_path


def resolve_paths_by_names(*path_names) -> Callable:
    """
    Decorator to resolve file paths by name.

    Args:
        *path_names (str): Names of function arguments that should be resolved to absolute paths.

    Returns:
        Callable: Wrapped function with resolved paths.
    """
    def outer_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            for name in path_names:
                if name in kwargs:
                    kwargs[name] = resolve_path(kwargs[name])
            return func(*args, **kwargs)
        return inner
    return outer_wrapper


def ask_overwrite(destination_name: str, force_overwrite_name: str = 'force_overwrite'):
    """
    Decorator that asks the user whether to overwrite an existing file.

    Args:
        destination_name (str): The keyword argument name that holds the file path.
        force_overwrite_name (str): The keyword argument name that determines if overwriting should be forced.

    Returns:
        Callable: Wrapped function with overwrite confirmation.
    """
    def outer_wrapper(func):
        @wraps(func)
        def inner(*args, **kwargs):
            force_overwrite = kwargs.get(force_overwrite_name, False)
            if destination_name in kwargs and not force_overwrite:
                destination = Path(kwargs[destination_name])
                if destination.exists() and \
                        not click.confirm(f"\nFile {destination} already exists. Overwrite?", default=False):
                    click.echo("\nSkipping overwrite.")
                    return
            return func(*args, **kwargs)
        return inner
    return outer_wrapper


def read_file(filepath: Union[str, Path]) -> str:
    """
    Reads a file and returns its content.

    Args:
        filepath (Union[str, Path]): Path to the file.

    Returns:
        str: The file contents, or an empty string if an error occurs.
    """
    try:
        with open(filepath, encoding="utf-8") as file:
            return file.read()
    except Exception as e:
        logger.error(f"Error reading file '{filepath}': {e}")
        return ""


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

@ask_overwrite('destination', force_overwrite_name='force_overwrite')
@resolve_paths_by_names('source', 'destination')
def save_config(source: Path, destination: Path, force_overwrite: bool = False) -> None:
    """
    Saves configuration from one YAML file to another.

    Args:
        source (Path): Source YAML file path.
        destination (Path): Destination YAML file path.
        force_overwrite (bool): If True, overwrites the destination file without confirmation.

    Raises:
        OSError: If an error occurs while writing the file.
    """
    try:
        data = load_config(source)
        with destination.open("w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
        click.echo(f"Config saved successfully to {destination}")
    except OSError as e:
        logger.error(f"Failed to save config from {source} to {destination}: {e}")


@ask_overwrite('destination', force_overwrite_name='force_overwrite')
@resolve_paths_by_names('source', 'destination')
def save_message(source: Path, destination: Path, force_overwrite: bool = False) -> None:
    """
    Saves a message file from source to destination.

    Args:
        source (Path): Source file path.
        destination (Path): Destination file path.
        force_overwrite (bool): If True, overwrites the destination file without confirmation.
    """
    try:
        shutil.copy(source, destination)
        click.echo(f"Message file saved successfully to {destination}")
    except OSError as e:
        logger.error(f"Failed to save message file from {source} to {destination}: {e}")
