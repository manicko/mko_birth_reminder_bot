import os

import yaml
import logging
from pathlib import Path
from importlib import resources
from typing import Any
logger = logging.getLogger(__name__)



def load_config(path: Path) -> dict[str, Any]:
    if path.exists():
        with path.open("r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def save_config(file_from:Path, file_to:Path):
    """Сохраняет пользовательские настройки"""
    try:
        if not file_to.exists():
            parent_dir = file_to.parent.absolute()
            parent_dir.mkdir(parents=True, exist_ok=True)

        data = load_config(file_from)

        with open(file_to, "w", encoding="utf-8") as f:
            yaml.safe_dump(data, f, allow_unicode=True)

    except Exception as e:
        logger.error(e)


def merge_dicts(dict1, dict2):
    """ Recursively merges dict2 into dict1 """
    if not isinstance(dict1, dict) or not isinstance(dict2, dict):
        return dict2
    for k in dict2:
        if k in dict1:
            dict1[k] = merge_dicts(dict1[k], dict2[k])
        else:
            dict1[k] = dict2[k]
    return dict1



def resolve_path(path: str | Path, base_dir: Path | None = None) -> Path:
    """
    Универсальная функция для поиска пути.

    Args:
        path (str | Path): Путь к файлу или папке (может быть абсолютным или относительным).
        base_dir (Path | None): Базовая директория, относительно которой искать (по умолчанию - папка с кодом).

    Returns:
        Path: Найденный путь.

    Raises:
        ValueError: Если путь не найден.
    """
    path = Path(path).expanduser()  # Обрабатывает `~` (домашнюю директорию)

    # Если путь абсолютный и существует — возвращаем его сразу
    if path.is_absolute():
        if path.exists():
            return path
        raise ValueError(f"Invalid path: {path}")

    # Если base_dir не указан, берём директорию текущего модуля
    if base_dir is None:
        base_dir = Path(__file__).resolve().parent.parent

    # Ищем файл в базовой директории
    resolved_path = (base_dir / path).resolve()
    if resolved_path.exists():
        return resolved_path

    raise ValueError(f"Invalid path: {path} (Checked in {resolved_path})")


def resolve_nested_paths(settings: dict, path_names: str | tuple = ("path", "filename", "state_file")) -> dict:
    """
    Проходит по словарю и исправляет пути по ключам из path_names.

    Args:
        settings: dict
            Словарь с настройками, в котором будут исправлены пути.
        path_names: str | tuple
            Названия ключей, которые считаются путями.

    Returns:
        dict: Словарь с исправленными путями.
    """
    stack = [settings]
    while stack:
        current = stack.pop()
        for key, value in current.items():
            if isinstance(value, dict):
                stack.append(value)
            elif key in path_names and isinstance(value, str):
                try:
                    current[key] = resolve_path(value)
                except ValueError as err:
                    logger.error(err)

    return settings