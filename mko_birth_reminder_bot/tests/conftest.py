import pytest
import random

@pytest.fixture(scope="function")
def random_user_id():
    return random.randrange(10**11, 10**12) # Возвращает логин и пароль