from datetime import datetime, date
from os import PathLike
import re
from typing import Dict, Union, List, Tuple, Optional
import sqlite3
import logging
import uuid
from pathlib import Path

logger = logging.getLogger(__name__)

DATE_PATTERNS: Tuple[str, ...] = ('%d.%m.%Y', '%Y.%m.%d', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d')

def list_files_in_directory(path: Union[str, PathLike],
                            extensions: Tuple[str, ...] = ('csv', 'txt'),
                            include_subfolders: bool = False) -> List[Path]:
    """
    Lists files in a directory with specific extensions.

    Args:
        path (Union[str, PathLike]): The directory path.
        extensions (Tuple[str, ...]): Allowed file extensions (default: ('csv', 'txt')).
        include_subfolders (bool): Whether to include subfolders (default: False).

    Returns:
        List[Path]: A list of file paths matching the given extensions.
    """
    try:
        files = []
        subfolder_pattern = '**/' if include_subfolders else ''
        for ext in extensions:
            files.extend(Path(path).glob(f'{subfolder_pattern}*.{ext.strip(".")}'))
        return files
    except Exception as err:
        logger.error(f"Error reading directory {path}: {err}")
        return []

def rows_to_dict_list(rows: Union[List[sqlite3.Row], sqlite3.Row]) -> List[Dict[str, Union[str, int]]]:
    """
    Converts SQLite row objects to a list of dictionaries.

    Args:
        rows (Union[List[sqlite3.Row], sqlite3.Row]): SQLite row(s).

    Returns:
        List[Dict[str, Union[str, int]]]: A list of dictionaries representing row data.
    """
    try:
        if isinstance(rows, sqlite3.Row):
            rows = [rows]
        return [dict(zip(row.keys(), row)) for row in rows]
    except TypeError as e:
        logger.error(f"Error converting rows to dictionary: {e}")
        return []


def generate_random_filename(extension: str = "csv") -> str:
    """
    Generates a random filename with the specified extension.

    Args:
        extension (str): The file extension. Default is "csv".

    Returns:
        str: A randomly generated filename.
    """
    return f"{uuid.uuid4().hex}.{extension}"

def generate_date_patterns(date_parts: List[str] = ("%d", "%m", "%Y"),
                           separators: List[str] = ('.', '-', '/')) -> Tuple[str, ...]:
    """
    Generates possible date patterns using different separators.

    Args:
        date_parts (List[str]): List of date components (default: day, month, year).
        separators (List[str]): List of separators (default: '.', '-', '/').

    Returns:
        Tuple[str, ...]: A tuple of formatted date patterns.
    """
    patterns = []
    for symbol in separators:
        patterns.append(symbol.join(date_parts))
        patterns.append(symbol.join(reversed(date_parts)))
    return tuple(patterns)

def validate_data(column_names: List[str],
                  date_column_name: str,
                  date_format: str,
                  data: Dict[str, Union[str, int]]) -> Dict[str, Union[str, int]]:
    """
    Validates and processes data by cleaning text fields and ensuring date fields are properly formatted.

    Args:
        column_names (List[str]): Valid column names to retain.
        date_column_name (str): Name of the column containing date values.
        date_format (str): Target date format (e.g., '%Y-%m-%d').
        data (Dict[str, Union[str, int]]): Data row as a dictionary.

    Returns:
        Dict[str, Union[str, int]]: Validated data with cleaned text and formatted dates.
    """
    try:
        validated_data = {k: clean_text(v) for k, v in data.items() if k in column_names and k != date_column_name}

        if date_column_name in data and data[date_column_name]:
            formatted_date = parse_date(data[date_column_name])
            if formatted_date:
                validated_data[date_column_name] = formatted_date.strftime(date_format)
            else:
                logger.warning(f"Invalid date format in column '{date_column_name}': {data[date_column_name]}")

        return validated_data
    except Exception as e:
        logger.error(f"Error in validate_data: {e}")
        return {}

def parse_date(date_str: str, date_patterns: Tuple[str, ...] = DATE_PATTERNS) -> Optional[date]:
    """
    Parses a date string using multiple possible formats.

    Args:
        date_str (str): Date string to validate.
        date_patterns (Tuple[str, ...]): Tuple of date formats to try.

    Returns:
        Optional[date]: Parsed date object, or None if parsing fails.
    """
    for pattern in date_patterns:
        try:
            return datetime.strptime(date_str, pattern).date()
        except (ValueError, TypeError):
            continue
    return None

def clean_text(text: str) -> str:
    """
    Cleans text by removing unwanted characters and extra spaces.

    Args:
        text (str): The text to clean.

    Returns:
        str: The cleaned text.
    """
    pattern = r'[^а-яА-Яa-zA-Z0-9\s\-–]'
    return re.sub(pattern, '', text).strip()


def safe_substitute(template: str, mapping: Dict[str, str]) -> str:
    """
    Safely substitutes placeholders in the template with values from mapping.

    This function only replaces placeholders that exactly match a key in mapping.
    Placeholders with more complex expressions (e.g., {enc.upper()}) are left unchanged.

    Args:
        template (str): The template string containing placeholders in the form {key}.
        mapping (Dict[str, str]): Dictionary where keys are placeholders and values are replacements.

    Returns:
        str: The template with placeholders replaced by their corresponding values.
    """
    pattern = r'\{([a-zA-Z_][a-zA-Z0-9_]*)\}'

    def replace_match(match):
        key = match.group(1)
        return str(mapping.get(key, match.group(0)))

    return re.sub(pattern, replace_match, template)
