import yaml
import logging
from pathlib import Path
from typing import Any, Dict, Union

logger = logging.getLogger(__name__)


def load_config(path: Path) -> Dict[str, Any]:
    """
    Loads configuration from a YAML file.

    Args:
        path (Path): Path to the YAML configuration file.

    Returns:
        dict[str, Any]: Parsed configuration dictionary.
    """
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(file_from: Path, file_to: Path) -> None:
    """
    Saves user configuration from one file to another.

    Args:
        file_from (Path): Source file path.
        file_to (Path): Destination file path.
    """
    try:
        file_from = Path(file_from)
        file_to = Path(file_to)

        # Ensure the parent directory exists
        if not file_to.exists():
            parent_dir = file_to.parent.absolute()
            parent_dir.mkdir(parents=True, exist_ok=True)

        data = load_config(file_from)

        with open(file_to, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True, default_flow_style=False)
    except Exception as e:
        logger.error(e)


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


def make_path(path: Path) -> None:
    """
    Checks if a path exists and creates it if necessary.

    Args:
        path (Path): Path to a file or directory.

    Raises:
        ValueError: If the path cannot be created.
    """
    try:
        if path.exists():  # If the path already exists, do nothing
            return
        if path.suffix:  # If the path points to a file
            path.parent.mkdir(parents=True, exist_ok=True)
        else:  # If the path points to a directory
            path.mkdir(parents=True, exist_ok=True)
    except Exception as e:
        raise ValueError(f"Failed to create path: {path} ({e})")


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

    # If the path is absolute and exists, return it immediately
    if path.is_absolute():
        if path.exists():
            return path
        make_path(path)  # If not found, attempt to create it
        return path

    # If base_dir is not provided, use the parent directory of this module
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent

    # Resolve the full path
    resolved_path = (base_dir / path).resolve()

    if not resolved_path.exists():
        make_path(resolved_path)  # Create the path if it does not exist

    return resolved_path
