from datetime import datetime, date
from os import PathLike
import re
from typing import Union, List, Optional, Tuple
from yaml import (safe_load as yaml_safe_load, YAMLError)
import sqlite3
import logging
logger = logging.getLogger(__name__)

DATE_PATTERNS = ('%d.%m.%Y', '%Y.%m.%d', '%d-%m-%Y', '%Y-%m-%d', '%d/%m/%Y', '%Y/%m/%d')


def dict_from_row(rows:Union[List[sqlite3.Row], sqlite3.Row]):
    try:
        return [dict(zip(row.keys(), row)) for row in rows]
    except TypeError as e:
        logger.error(e)


def gen_date_patterns(date_pattern: list[str] = ("%d", "%m", "%Y"),
                      concat_symbols: list[str] = ('.', '-', '/')) -> tuple[str, ...]:
    patterns:list[str] = []
    for symbol in concat_symbols:
        patterns.append(symbol.join(date_pattern))
        patterns.append(symbol.join(date_pattern[::-1]))
    return tuple(patterns)

def data_validation(column_names, date_column_name, date_format, data:[dict[str:str|int]])->[dict[str:str|int]]:

    try:
        data_validated = {k: get_text(v) for k, v in data.keys() if k in column_names}
        if date_column_name in data_validated:
            data_validated[date_column_name] = get_date(data_validated[date_column_name]).strftime(date_format)
        return data_validated
    except YAMLError as e:
        logger.error(e)

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

