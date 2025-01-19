from time import sleep

from freezegun import freeze_time
import pytest
import sqlite3
from mko_birth_reminder_bot.core import TGUser
from mko_birth_reminder_bot.tests.conftest import get_csv, generate_valid_test_data
from mko_birth_reminder_bot.core.utils import (dict_from_row)
from pathlib import Path



class TestConfig:
    def test_config(self, config):
        try:
            config
        except Exception as e:
            pytest.fail(f"Reading YAML file raised an exception: {e}")

    @pytest.mark.parametrize("field, expected_result", [
        ('TELETHON_API', True),
        ('DATABASE', True),
        ('CSV', True),

    ])
    def test_key_fields(self, config, field, expected_result):
        assert (field in config.settings) == expected_result, f"Configuration does not contain required field:{field}"

    def test_log(self, config):
        print(config.log_settings['root'])
        assert len(config.log_settings) != 0, f"Configuration does not contain log settings"


class TestCSVReader:
    def test_read_data(self, csv_worker):
        try:
            valid_test_csv = get_csv(generate_valid_test_data(10))
            df = csv_worker.read_csv(valid_test_csv)
            df = csv_worker.prepare_dataframe(df)

            assert len(df) > 0, f"No data read"
        except Exception as e:
            pytest.fail(f"Fail to del_info: {e}")


class TestTGUser:
    def test_is_user(self, random_user):
        assert isinstance(random_user.tg_user_id, int) is True, f"User id {random_user.tg_user_id} is not an integer"
        print(f" user_id = {random_user.tg_user_id}")

    def test_add_attributes(self, random_user):
        print(f" user_id = {random_user.tg_user_id}")
        try:
            random_user.update_last_interaction_date()
            random_user.notify_before_days = 30
        except Exception as e:
            pytest.fail(f"Fail to add attributes: {e}")

    def test_add_info(self, random_user):
        try:
            random_user.add_info()
        except Exception as e:
            pytest.fail(f"Failed to add info: {e}")

    def test_get_info(self, random_user):
        try:
            info = random_user.get_info()
            assert isinstance(info, sqlite3.Row) is True, f"Info is not a dict: {info}"
            assert set(TGUser.TABLE_FIELDS.keys()) == set(info.keys())
            assert ('tg_user_id' in set(info.keys())) == True
            assert info['tg_user_id'] == random_user.tg_user_id
        except Exception as e:
            pytest.fail(f"Fail to get_info: {e}")

    def test_data_load(self, random_user, csv_worker, data_worker):
        try:
            valid_test_csv = get_csv(generate_valid_test_data(20))
            df = csv_worker.read_csv(valid_test_csv)
            df = csv_worker.prepare_dataframe(df)
            data_worker.data_tbl_name = "id_" + str(random_user.tg_user_id)
            data_worker.add_data(df)
        except Exception as e:
            pytest.fail(f"Fail to get_info: {e}")

    def test_default_reminders(self, random_user,data_worker):
        test = []
        for i in range(366):
            if x := data_worker.get_upcoming_dates(i):
                test.append(dict_from_row(x))
        assert len(test) == 20, f'Not all records got from test_data{test}'

    def test_custom_reminders(self, random_user):

        if x := data_worker.get_upcoming_dates_custom_column():
            print(dict_from_row(x))

    # # def test_load_user():
    #     with TGUser(**CONFIGURATION, tg_user_id=3232) as user_worker, \
    #             TGUserData(**CONFIGURATION) as data_worker, \
    #             CSVWorker(**CONFIGURATION) as csv_worker:
    #         user_worker.update_last_interaction_date()
    #         user_worker.notify_before_days = 30
    #         # user_worker.add_info()
    #         info = user_worker.get_info()
    #         for c in TGUser.TABLE_FIELDS:
    #             print(c, info[c])
    #         print(user_worker.tg_user_id)
    #         data_worker.data_tbl_name = "id_" + str(user_worker.tg_user_id)
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
    def test_del_info(self, random_user):
        try:
            random_user.del_info()
            assert random_user.get_info() is None, f"Info is not deleted: {random_user.get_info()}"
        except Exception as e:
            pytest.fail(f"Fail to del_info: {e}")
