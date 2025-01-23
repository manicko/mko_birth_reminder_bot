from datetime import datetime, date
from os import PathLike
import re
from typing import Dict, Union, List, Optional, Tuple
from yaml import (safe_load as yaml_safe_load, YAMLError)
import sqlite3
import logging
import uuid
logger = logging.getLogger(__name__)
DATE_PATTERNS = ('%d.%m.%Y', '%Y.%m.%d', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d')


def dict_from_row(rows: Union[List[sqlite3.Row], sqlite3.Row]):
    try:
        return [dict(zip(row.keys(), row)) for row in rows]
    except TypeError as e:
        logger.error(e)

def generate_random_filename(extension: str = "csv") -> str:
    """
    Generates a random filename with the specified extension.

    Args:
        extension (str): The file extension. Default is "csv".

    Returns:
        str: A randomly generated filename.
    """
    return f"{uuid.uuid4().hex}.{extension}"

def gen_date_patterns(date_pattern: list[str] = ("%d", "%m", "%Y"),
                      concat_symbols: list[str] = ('.', '-', '/')) -> tuple[str, ...]:
    patterns: list[str] = []
    for symbol in concat_symbols:
        patterns.append(symbol.join(date_pattern))
        patterns.append(symbol.join(date_pattern[::-1]))
    return tuple(patterns)


def data_validation(column_names: List[str],
                    date_column_name: str,
                    date_format: str,
                    data: Dict[str, Union[str, int]]) -> Dict[str, Union[str, int]]:
    """
    Validates and processes data by cleaning text fields and ensuring date fields are properly formatted.

    Parameters:
    ----------
    column_names : List[str]
        A list of valid column names that should be retained in the data.
    date_column_name : str
        The name of the column containing date values to validate and reformat.
    date_format : str
        The target format for the date column (e.g., '%Y-%m-%d').
    data : Dict[str, Union[str, int]]
        A dictionary representing a row of data where keys are column names and values
        are their corresponding data (either strings or integers).

    Returns:
    -------
    Dict[str, Union[str, int]]
        A dictionary containing validated and cleaned data. Only the columns specified
        in `column_names` are retained, and the date column (if present) is reformatted
        to the specified `date_format`.

    Behavior:
    --------
    - Filters the input data to retain only the specified `column_names`.
    - Cleans text fields using the `get_text` function.
    - Validates and reformats the date in the `date_column_name` field to the `date_format`.
    - Logs errors if any exceptions occur during validation.
    """
    try:
        # Filter and clean text columns
        data_validated = {k: get_text(v) for k, v in data.items() if k in column_names and k != date_column_name}

        # Validate and format the date column if present
        if date_column_name in data and data[date_column_name]:
            formatted_date = get_date(data[date_column_name])
            if formatted_date:
                data_validated[date_column_name] = formatted_date.strftime(date_format)
            else:
                logger.warning(f"Invalid date format in column '{date_column_name}': {data[date_column_name]}")

        return data_validated
    except Exception as e:
        logger.error(f"Error in data_validation function: {e}")
        return {}


def get_date(date_to_validate: str, date_patterns: tuple[str] = DATE_PATTERNS) -> date | None:
    for pattern in date_patterns:
        try:
            d = datetime.strptime(date_to_validate, pattern).date()
        except (ValueError, TypeError):
            # skip if not is date
            continue
        else:
            return d
    return None


def get_text(text_to_validate: str) -> str:
    pattern = r'[^а-яА-Яa-zA-Z0-9\s\-–]'

    clean_value = re.sub(pattern, '', str(text_to_validate))
    clean_value = clean_value.strip()
    return clean_value


def yaml_to_dict(file: str | PathLike):
    with open(file, "r", encoding="utf8") as stream:
        try:
            data = yaml_safe_load(stream)
        except YAMLError as exc:
            raise exc
        else:
            return data
