import random
import pandas as pd
import datetime
from freezegun import freeze_time


class TestData:
    COMPANIES = ["Acme Corp", "Beta Inc", "Gamma LLC", "Delta Ltd", "Epsilon Co", "Zeta Group", "Eta Partners",
                 "Theta Inc"]
    POSITIONS = ["Manager", "Developer", "Analyst", "Designer", "Consultant", "HR", "CEO", "Sales", "Marketing",
                 "Accountant"]
    GIFT_CATEGORIES = ["Luxury", "Tech", "Books", "Art", "Travel", "Fashion", "Food", "Gadgets", "Wellness"]

    valid_data_en = [
        ("Acme Corp", "Smith", "John", "Manager", "Luxury", "1985-06-15", 7),  # 1
        ("Beta Inc", "Doe", "Jane", "Developer", "Tech", "1990-03-22", 14),  # 2
        ("Gamma LLC", "Brown", "Charlie", "Analyst", "Books", "1988-11-05", 3),  # 3
        ("Delta Ltd", "Johnson", "Emily", "Designer", "Art", "1992-08-29", 10),  # 4
        ("Zeta Group", "Wilson", "Anna", "HR", "Fashion", "1995-04-18", 7),  # 5
        ("Eta Partners", "Taylor", "James", "CEO", "Luxury", "1978-09-05", 30),  # 6
        ("Iota Ltd", "Garcia", "David", "Marketing", "Gadgets", "1991-07-07", 15),  # 7
        ("Kappa Co", "Anderson", "Laura", "Accountant", "Wellness", "1983-02-28", 7),  # 8
        ("Alpha Corp", "Black", "Olivia", "Engineer", "Music", "2024-09-01", 20),  # 9
        ("Beta Enterprises", "White", "Ethan", "Manager", "Books", "2010-01-02", 20),  # 9
        ("Gamma LLC", "Green", "Sophia", "Consultant", "Travel", "2025-02-01", 13),
        ("Lambda Co", "Hughes", "Emily", "Researcher", "Books", "2024-12-29", 9), #+
        ("Mu Inc", "Reed", "Oliver", "Engineer", "Tech", "2024-12-30", 10), #+
        ("Nu Partners", "Walker", "Emma", "Strategist", "Fashion", "1990-01-02", 13), #+
        ("Xi Group", "Hall", "Liam", "Advisor", "Luxury", "2025-01-03", 14), #+
        ("Epsilon Co", "Davis", "Michael", "Consultant", "Travel", "1980-12-31", 10),
        ("Theta Inc", "Martinez", "Sophia", "Sales", "Food", "1987-01-11", 22), # +
        ("Delta Ltd", "Gray", "Lucas", "Developer", "Technology", "2025-08-30", 15),  #
    ]
    valid_data_ru = [
        ("ООО Альфа", "Иванов", "Алексей", "Менеджер", "Роскошь", "1985-06-15", 7),
        ("ЗАО Бета", "Петрова", "Мария", "Разработчик", "Технологии", "1990-03-22", 14),
        ("ООО Гамма", "Смирнов", "Дмитрий", "Аналитик", "Книги", "1988-11-05", 3),
        ("ООО Дельта", "Кузнецова", "Екатерина", "Дизайнер", "Искусство", "1992-08-19", 10),
        ("ИП Эпсилон", "Попов", "Михаил", "Консультант", "Путешествия", "1980-12-30", 5),
        ("ОАО Зета", "Соколова", "Анна", "Кадры", "Мода", "1995-04-18", 7),
        ("ПАО Эта", "Козлов", "Иван", "Генеральный директор", "Роскошь", "1978-09-23", 30),
        ("ООО Тета", "Мартынова", "Софья", "Продавец", "Еда", "1987-01-11", 2),
        ("ИП Йота", "Гарин", "Давид", "Маркетолог", "Гаджеты", "1991-07-07", 15),
        ("ЗАО Каппа", "Андреева", "Людмила", "Бухгалтер", "Здоровье", "1983-02-28", 7),
        ("ООО Альфа", "Чернов", "Ольга", "Инженер", "Музыка", "2024-12-25", 20),
        ("ИП Бета", "Белый", "Илья", "Менеджер", "Книги", "2024-12-31", 20),
        ("ООО Гамма", "Зелёный", "Софья", "Консультант", "Путешествия", "2025-01-01", 20),
        ("ООО Дельта", "Серый", "Максим", "Разработчик", "Технологии", "2025-01-03", 20),
        ("ИП Лямбда", "Рыжова", "Елизавета", "Исследователь", "Книги", "2024-12-29", 10),
        ("ООО Мю", "Рид", "Олег", "Инженер", "Технологии", "2024-12-30", 15),
        ("ПАО Ню", "Лескова", "Елена", "Стратег", "Мода", "2025-01-05", 16),
        ("ООО Кси", "Холин", "Арсений", "Советник", "Роскошь", "2025-01-04", 5),
    ]
    invalid_data_en = [
        # 1. Одно или несколько полей содержат недопустимые символы
        ("#4Ac**&--==..>>", "SELECT * FROM", "John", "Manager", ")766", "1985-06-15", 7),
        # 3. Поле дата заполнено некорректно (сначала год, затем месяц)
        ("Delta Ltd", "Johnson", "Emily", "Designer", "Art", "30-12-1992", 10),  # Дата в формате DD-MM-YYYY
        # 3. Поле дата заполнено некорректно (год сокращен до 2 цифр)
        ("Epsilon Co", "Davis", "Michael", "Consultant", "Travel", "10-03-22", 5),
        # 3. Поле дата заполнено некорректно (день не в формате dd)
        ("Epsilon Co", "Davis", "Michael", "Consultant", "Travel", "1-03-1992", 5),
        # 3. Поле дата содержит недопустимые символы
        ("Zeta Group", "Wilson", "Anna", "HR", "Fashion", "1995%04%18", 7),  # Дата с символами %
        # 4. Последнее поле содержит не цифры, а строку
        ("Eta Partners", "Taylor", "James", "CEO", "Luxury", "1978-09-23", "thirty"),
    ]

    invalid_data_ru = [

    ]

    invalid_data_wrong_col_num = [
        # 2. Количество столбцов больше необходимого
        ("Beta Inc", "Doe", "Jane", "Developer", "Tech", "1990-03-22", 14, "ExtraColumn"),
        # 2. Количество столбцов меньше необходимого
        ("Gamma LLC", "Brown", "Charlie", "Books", "1988-11-05"),  # Поле notice_before отсутствует
    ]



