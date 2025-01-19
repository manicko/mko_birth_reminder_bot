import pytest
import random
from pathlib import Path
from mko_birth_reminder_bot.core import CSVWorker, TGUser, TGUserData, CONFIG
import faker
import pandas as pd
from typing import List, Dict

COMPANIES = ["Acme Corp", "Beta Inc", "Gamma LLC", "Delta Ltd", "Epsilon Co", "Zeta Group", "Eta Partners", "Theta Inc"]
POSITIONS = ["Manager", "Developer", "Analyst", "Designer", "Consultant", "HR", "CEO", "Sales", "Marketing",
             "Accountant"]
GIFT_CATEGORIES = ["Luxury", "Tech", "Books", "Art", "Travel", "Fashion", "Food", "Gadgets", "Wellness"]

invalid_data = [
    ("Acme Corp", "Smith", "John", "Manager", "Luxury", "1985-06-15", 7),
    ("Beta Inc", "Doe", "Jane", "Developer", "Tech", "1990-03-22", 14),
    ("Gamma LLC", "Brown", "Charlie", "Analyst", "Books", "1988-11-05", 3),
    ("Delta Ltd", "Johnson", "Emily", "Designer", "Art", "1992-08-19", 10),
    ("Epsilon Co", "Davis", "Michael", "Consultant", "Travel", "1980-12-30", 5),
    ("Zeta Group", "Wilson", "Anna", "HR", "Fashion", "1995-04-18", 7),
    ("Eta Partners", "Taylor", "James", "CEO", "Luxury", "1978-09-23", 30),
    ("Theta Inc", "Martinez", "Sophia", "Sales", "Food", "1987-01-11", 2),
    ("Iota Ltd", "Garcia", "David", "Marketing", "Gadgets", "1991-07-07", 15),
    ("Kappa Co", "Anderson", "Laura", "Accountant", "Wellness", "1983-02-28", 7),
    ("Alpha Corp", "Black", "Olivia", "Engineer", "Music", "2024-12-25", 20),
    ("Beta Enterprises", "White", "Ethan", "Manager", "Books", "2024-12-31", 20),
    ("Gamma LLC", "Green", "Sophia", "Consultant", "Travel", "2025-01-01", 20),
    ("Delta Ltd", "Gray", "Lucas", "Developer", "Technology", "2025-01-03", 20),
    ("Lambda Co", "Hughes", "Emily", "Researcher", "Books", "2024-12-29", 10),
    ("Mu Inc", "Reed", "Oliver", "Engineer", "Tech", "2024-12-30", 15),
    ("Nu Partners", "Walker", "Emma", "Strategist", "Fashion", "2025-01-02", 20),
    ("Xi Group", "Hall", "Liam", "Advisor", "Luxury", "2025-01-04", 5),
]


@pytest.fixture(scope="class")
def config():
    return CONFIG


def random_user_id():
    return random.randrange(10 ** 11, 10 ** 12)


def generate_valid_test_data(num_records: int = 1) -> list:
    """
    Generates test data for a database table.

    :param num_records: Number of records to generate.
    :return: List of dictionaries with generated test data.
    """
    fake = faker.Faker()
    test_data = []
    for _ in range(num_records):
        company = random.choice(COMPANIES)
        last_name = fake.last_name()
        first_name = fake.first_name()
        position = random.choice(POSITIONS)
        gift_category = random.choice(GIFT_CATEGORIES)

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
def csv_worker():
    with CSVWorker() as tmp_csv_worker:
        yield tmp_csv_worker


@pytest.fixture(scope="class")
def random_user():  # Возвращает логин
    with TGUser(random_user_id()) as tmp_user_worker:
        yield tmp_user_worker
        tmp_user_worker.del_info()


@pytest.fixture(scope="class")
def data_worker():
    with TGUserData() as tmp_data_worker:
        yield tmp_data_worker


def get_csv(test_data: List[Dict[str, str]]) -> Path:
    """
    Saves test data to a CSV file using pandas.
    :param test_data: List of dictionaries with test data.
    """

    try:
        df = pd.DataFrame(test_data)
        target_output = Path(CONFIG['CSV']["EXPORT_DATA"]["path"], 'test_data.csv')
        df.to_csv(target_output, **CONFIG['CSV']["EXPORT_DATA"]["to_csv"])
        print(f"Test data successfully saved to {target_output}")
        return target_output

    except Exception as e:
        print(f"An error occurred while saving to CSV: {e}")


# Clean up: Remove the temporary files after the tests
@pytest.fixture(autouse=True)
def cleanup_temp_files(config):
    yield
    target_output = Path(config['CSV']["EXPORT_DATA"]["path"], 'test_data.csv')
    if target_output.is_file():
        target_output.unlink()