import pytest
import pytest_asyncio
import random
from pathlib import Path
from mko_birth_reminder_bot.core import CSVHandler, TGUser, TGUserData, CONFIG
from mko_birth_reminder_bot.quotes import QuoteFetcher
import faker
import pandas as pd
from typing import List, Dict
from .test_data import TestData



@pytest.fixture(scope="class")
def config():
    return CONFIG

@pytest.fixture(scope="module")
def random_user_id()->int:
    return random.randrange(10 ** 11, 10 ** 12)

def get_test_data(num_records: int = 1, valid = True) -> list:
    """
    Generates test data for a database table basing on prepared lists

    :param num_records: Number of records to generate. If 0 returns whole set
    :param valid: which type of data return - True if valid, false if not
    :return: List of dictionaries with generated test data.
    """
    if valid:
        data = TestData.valid_data_en + TestData.valid_data_ru
    else:
        data = TestData.invalid_data_en + TestData.invalid_data_ru

    return data if num_records == 0 else random.sample(data, num_records)

def generate_valid_test_data(num_records: int = 1) -> list:
    """
    Generates test data for a database table.

    :param num_records: Number of records to generate.
    :return: List of dictionaries with generated test data.
    """
    fake = faker.Faker()
    test_data = []
    for _ in range(num_records):
        company = random.choice(TestData.COMPANIES)
        last_name = fake.last_name()
        first_name = fake.first_name()
        position = random.choice(TestData.POSITIONS)
        gift_category = random.choice(TestData.GIFT_CATEGORIES)

        # Генерация даты рождения в диапазоне от 20 до 60 лет назад
        birth_date = fake.date_of_birth(minimum_age=20, maximum_age=60).strftime('%Y-%m-%d')

        # Генерация notice_before как случайного значения от 1 до 30 дней
        notice_before = random.randint(1, 30)

        # Формирование записи
        record = {
            "company": company,
            "last_name": last_name,
            "first_name": first_name,
            "position": position,
            "gift_category": gift_category,
            "birth_date": birth_date,
            "notice_before": notice_before
        }
        test_data.append(record)
    return test_data


@pytest.fixture(scope="class")
def csv_handler():
    with CSVHandler() as tmp_csv_handler:
        yield tmp_csv_handler



@pytest.fixture(scope="class")
def random_user(random_user_id):  # Возвращает логин
    with TGUser(random_user_id) as tmp_user_handler:
        yield tmp_user_handler
        # удаляем пользователя из базы в любом случае
        tmp_user_handler.del_info()


@pytest.fixture(scope="class")
def user_data(random_user_id):
    with TGUserData(random_user_id) as tmp_user_data:
        yield tmp_user_data


def get_csv(test_data: List[Dict[str, str]]) -> Path:
    """
    Saves test data to a CSV file using pandas.
    :param test_data: List of dictionaries with test data.
    """

    try:
        df = pd.DataFrame(test_data)
        target_output = Path(CONFIG.CSV.EXPORT_DATA.path, 'test_data.csv')
        df.to_csv(target_output, **CONFIG.CSV.EXPORT_DATA.to_csv)
        print(f"Test data successfully saved to {target_output}")
        return target_output

    except Exception as e:
        print(f"An error occurred while saving to CSV: {e}")


# Clean up: Remove the temporary files after the tests
@pytest.fixture(autouse=True)
def cleanup_temp_files(config):
    yield
    target_output = Path(config.CSV.EXPORT_DATA.path, 'test_data.csv')
    if target_output.is_file():
        target_output.unlink()

@pytest_asyncio.fixture(loop_scope="class")
async def quote_fetcher():
    async with QuoteFetcher() as f:
        yield f