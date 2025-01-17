
from freezegun import freeze_time
import pytest

from mko_birth_reminder_bot.core import utils, CSVWorker, DBWorker, TGUser, TGUserData, ConfigReader, Logger
from pathlib import Path

config = ConfigReader()
logger = Logger(config.logs)
CONFIGURATION = {'config': config, 'logger': logger}

data1 = ['Сириус', 'Сергеевич', 'Сергей', 'Сетевой', 'VIP', '01.01.1988', 1]
data2 = ['Сириус', 'Сергеевич', 'Сергей', 'Сетевой', 'VIP', '01.01.1988', 1]


# def init():
#     with DBWorker(config.db_settings, logger) as db_worker:
#         db_worker.create_table(TGUser.TABLE_NAME, TGUser.TABLE_FIELDS)

class TestConfig:
    @pytest.fixture
    def test_config(self):
        try:
            return ConfigReader()
        except Exception as e:
            pytest.fail(f"Reading YAML file raised an exception: {e}")

    @pytest.mark.parametrize("field, expected_result", [
        ('LOGS', True),
        ('TELETHON_API', True),
        ('DATABASE', True),
        ('CSV', True),

    ])
    def test_key_fields(self, test_config, field, expected_result):
        assert (field in test_config.settings) == expected_result


def test_data(random_user_id):
    assert isinstance(random_user_id,int) == True

class TestTGUser:
    
def test_load_user():
    with TGUser(**CONFIGURATION, tg_user_id=3232) as user_worker, \
            TGUserData(**CONFIGURATION) as data_worker, \
            CSVWorker(**CONFIGURATION) as csv_worker:
        user_worker.update_last_interaction_date()
        user_worker.notify_before_days = 30
        # user_worker.add_info()
        info = user_worker.get_info()
        for c in TGUser.TABLE_FIELDS:
            print(c, info[c])
        print(user_worker.tg_user_id)
        data_worker.data_tbl_name = "id_" + str(user_worker.tg_user_id)
        # df = csv_worker.read_csv('dates.csv')
        # df = csv_worker.prepare_dataframe(df)
        # data_worker.add_data(df)

        ### test custom reminder ok
        # for i in range(360):
        #     if x:=data_worker.get_upcoming_dates(i):
        #         print(i, utils.dict_from_row(x))
        #
        ### test custom reminder ok
        # if x:=data_worker.get_upcoming_dates_custom_column():
        #     print(utils.dict_from_row(x))

        # user_worker.del_info()
