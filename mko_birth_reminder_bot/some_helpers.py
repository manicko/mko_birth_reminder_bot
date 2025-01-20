import random

import pandas as pd
import datetime
from freezegun import freeze_time

from mko_birth_reminder_bot.tests.test_data import TestData
data = [
    ["Eta Partners", "Taylor", "James", "CEO", "Luxury", "1978-09-05", 30],
    ["ПАО Эта", "Козлов", "Иван", "Генеральный директор", "Роскошь", "1978-09-23", 30],
    ["ИП Эпсилон", "Попов", "Михаил", "Консультант", "Путешествия", "1980-12-30", 5],
    ["Epsilon Co", "Davis", "Michael", "Consultant", "Travel", "1980-12-31", 10],
    ["Kappa Co", "Anderson", "Laura", "Accountant", "Wellness", "1983-02-28", 7],
    ["ЗАО Каппа", "Андреева", "Людмила", "Бухгалтер", "Здоровье", "1983-02-28", 7],
    ["Acme Corp", "Smith", "John", "Manager", "Luxury", "1985-06-15", 7],
    ["ООО Альфа", "Иванов", "Алексей", "Менеджер", "Роскошь", "1985-06-15", 7],
    ["Theta Inc", "Martinez", "Sophia", "Sales", "Food", "1987-01-11", 22],
    ["ООО Тета", "Мартынова", "Софья", "Продавец", "Еда", "1987-01-11", 2],
    ["Gamma LLC", "Brown", "Charlie", "Analyst", "Books", "1988-11-05", 3],
    ["ООО Гамма", "Смирнов", "Дмитрий", "Аналитик", "Книги", "1988-11-05", 3],
    ["Nu Partners", "Walker", "Emma", "Strategist", "Fashion", "1990-01-02", 13],
    ["Beta Inc", "Doe", "Jane", "Developer", "Tech", "1990-03-22", 14],
    ["ЗАО Бета", "Петрова", "Мария", "Разработчик", "Технологии", "1990-03-22", 14],
    ["Iota Ltd", "Garcia", "David", "Marketing", "Gadgets", "1991-07-07", 15],
    ["ИП Йота", "Гарин", "Давид", "Маркетолог", "Гаджеты", "1991-07-07", 15],
    ["ООО Дельта", "Кузнецова", "Екатерина", "Дизайнер", "Искусство", "1992-08-19", 10],
    ["Delta Ltd", "Johnson", "Emily", "Designer", "Art", "1992-08-29", 10],
    ["Zeta Group", "Wilson", "Anna", "HR", "Fashion", "1995-04-18", 7],
    ["ОАО Зета", "Соколова", "Анна", "Кадры", "Мода", "1995-04-18", 7],
    ["Beta Enterprises", "White", "Ethan", "Manager", "Books", "2010-01-02", 20],
    ["Alpha Corp", "Black", "Olivia", "Engineer", "Music", "2024-09-01", 20],
    ["ООО Альфа", "Чернов", "Ольга", "Инженер", "Музыка", "2024-12-25", 20],
    ["Lambda Co", "Hughes", "Emily", "Researcher", "Books", "2024-12-29", 9],
    ["ИП Лямбда", "Рыжова", "Елизавета", "Исследователь", "Книги", "2024-12-29", 10],
    ["Mu Inc", "Reed", "Oliver", "Engineer", "Tech", "2024-12-30", 10],
    ["ООО Мю", "Рид", "Олег", "Инженер", "Технологии", "2024-12-30", 15],
    ["ИП Бета", "Белый", "Илья", "Менеджер", "Книги", "2024-12-31", 20],
    ["ООО Гамма", "Зелный", "Софья", "Консультант", "Путешествия", "2025-01-01", 20],
    ["ПАО Ню", "Лескова", "Елена", "Стратег", "Мода", "2025-01-02", 20],
    ["Xi Group", "Hall", "Liam", "Advisor", "Luxury", "2025-01-03", 14],
    ["ООО Дельта", "Серый", "Максим", "Разработчик", "Технологии", "2025-01-03", 20],
    ["ООО Кси", "Холин", "Арсений", "Советник", "Роскошь", "2025-01-04", 5],
    ["Gamma LLC", "Green", "Sophia", "Consultant", "Travel", "2025-02-01", 13],
    ["Delta Ltd", "Gray", "Lucas", "Developer", "Technology", "2025-08-30", 15],
]

@freeze_time("2023-12-20 12:00:00")
def get_custom_birthdays(valid_data: list[tuple | list], date_col_idx: int = -2, reminder_col_idx: int = -1):
    columns = ["company", "last_name", "first_name", "position", "department", "birth_date", "notice_before_days"]
    birthdays_df = pd.DataFrame(valid_data, columns=columns)
    print(birthdays_df)
    print(len(birthdays_df))
    # Recalculate notification dates ignoring year
    birthdays_df["notification_day_month"] = birthdays_df.apply(
        lambda row: (datetime.datetime.strptime(row["birth_date"], "%Y-%m-%d") - datetime.timedelta(
            days=row["notice_before_days"])).strftime("%m-%d"),
        axis=1,
    )

    # Target notification date (ignoring year)
    target_day_month =  datetime.date.today().strftime("%m-%d")
    target_day_month = "12-20"
    print(target_day_month)
    # Filter rows where notification day and month match the target
    matching_birthdays = birthdays_df[birthdays_df["notification_day_month"] == target_day_month]

    print(matching_birthdays)


# print(get_custom_birthdays(TestData.valid_data_en + TestData.valid_data_ru))
# print(get_custom_birthdays(data))

from mko_birth_reminder_bot.core import CSVWorker

x = CSVWorker()
print( dict(zip(x.data_column_names,random.sample(data,1)[0])))
