from freezegun import freeze_time
import pytest
import sqlite3
from mko_birth_reminder_bot.core import TGUser
from mko_birth_reminder_bot.tests.conftest import get_csv, get_test_data, csv_worker
from mko_birth_reminder_bot.core.utils import (dict_from_row)
from .test_data import TestData


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
        assert len(config.log_settings) != 0, f"Configuration does not contain log settings"


class TestCSVReader:
    def test_read_valid_data(self, csv_worker):
        try:
            valid_test_csv = get_csv(get_test_data(10))
            df = csv_worker.read_csv(valid_test_csv)
            df = csv_worker.prepare_dataframe(df)

            assert len(df) > 0, f"No data read"
        except Exception as e:
            pytest.fail(f"Fail to del_info: {e}")

    def test_read_wrong_columns_data(self, csv_worker):
        valid_test_csv = get_csv(TestData.invalid_data_wrong_col_num)
        df = csv_worker.read_csv(valid_test_csv)
        assert len(df) == 0

    def test_read_invalid_valid_data(self, csv_worker):
        try:
            valid_test_csv = get_csv(get_test_data(0, False))
            df = csv_worker.read_csv(valid_test_csv)
            df = csv_worker.prepare_dataframe(df)
            assert len(df) == 4, f"No data read"
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

    # def test_get_info(self, random_user):
    #     try:
    #         info = random_user.get_info()
    #         assert isinstance(info, sqlite3.Row) is True, f"Info is not a dict: {info}"
    #         assert set(TGUser.TABLE_FIELDS.keys()) == set(info.keys())
    #         assert ('tg_user_id' in set(info.keys())) == True
    #         assert info['tg_user_id'] == random_user.tg_user_id
    #     except Exception as e:
    #         pytest.fail(f"Fail to get_info: {e}")
    #
    # def test_data_load(self, random_user, csv_worker, data_worker):
    #     try:
    #         valid_test_csv = get_csv(get_test_data(20))
    #         df = csv_worker.read_csv(valid_test_csv)
    #         df = csv_worker.prepare_dataframe(df)
    #         data_worker.data_tbl_name = "id_" + str(random_user.tg_user_id)
    #         data_worker.add_data(df)
    #     except Exception as e:
    #         pytest.fail(f"Fail to get_info: {e}")
    #
    # def test_flush(self, data_worker):
    #     try:
    #         data_worker.flush_data()
    #     except Exception as e:
    #         pytest.fail(f"Fail to flush_data: {e}")

    # def test_add_record(self,random_user, data_worker,csv_worker):
    #     try:
    #         data_worker.data_tbl_name = "id_" + str(random_user.tg_user_id)
    #         data_worker.flush_data()
    #         data = dict(zip(csv_worker.data_column_names, get_test_data(1)[0]))
    #         data_worker.add_record(**data)
    #     except Exception as e:
    #         pytest.fail(f"Fail to add_record: {e}")

    def test_get_record(self, random_user, data_worker, csv_worker):
        try:
            data_worker.data_tbl_name = "id_" + str(random_user.tg_user_id)
            data_worker.flush_data()
            data = dict(zip(csv_worker.data_column_names, get_test_data(1)[0]))
            data_worker.add_record(**data)
            assert data_worker.get_record_by_id("SELECT") is None
            assert data_worker.get_record_by_id(2) is None
            assert len(data_worker.get_record_by_id(1)) == len(
                data_worker.column_names)  # 8 столбцов в таблице с данными
            data_worker.flush_data()
        except Exception as e:
            pytest.fail(f"Fail get_record: {e}")

    def test_update_record(self, random_user, data_worker, csv_worker):
        try:
            data_worker.data_tbl_name = "id_" + str(random_user.tg_user_id)
            data_worker.flush_data()

            data = dict(zip(csv_worker.data_column_names, get_test_data(1)[0]))
            data_worker.add_record(**data)
            data_worker.update_record_by_id(record_id=1, birth_date="1999/01/01")
            updated_record = data_worker.get_record_by_id(1)
            assert updated_record["birth_date"] == "1999-01-01"

            data_worker.update_record_by_id(record_id=1,
                                            company='TEST COMPANY',
                                            last_name='TEST LAST NAME',
                                            first_name='TEST FIRST NAME',
                                            position='TEST POSITION',
                                            gift_category='TEST GIFT CATEGORY',
                                            notice_before_days=99,
                                            birth_date='01/02/2023')
            updated_record = data_worker.get_record_by_id(1)
            assert updated_record["company"] == 'TEST COMPANY'
            assert updated_record["last_name"] =='TEST LAST NAME'
            assert updated_record["first_name"] == 'TEST FIRST NAME'
            assert updated_record["position"] == 'TEST POSITION'
            assert updated_record["gift_category"] == 'TEST GIFT CATEGORY'
            assert updated_record["notice_before_days"] == 99
            assert updated_record["birth_date"] == '2023-02-01'
            #data_worker.flush_data()
        except Exception as e:
            pytest.fail(f"Fail get_record: {e}")

    # def test_data_drop(self, data_worker):
    #     try:
    #         data_worker.flush_data()
    #     except Exception as e:
    #         pytest.fail(f"Fail to flush_data: {e}")

    # def test_full_data_load(self, random_user, csv_worker, data_worker):
    #     try:
    #         valid_test_csv = get_csv(get_test_data(0))
    #         df = csv_worker.read_csv(valid_test_csv)
    #         df = csv_worker.prepare_dataframe(df)
    #         data_worker.data_tbl_name = "id_" + str(random_user.tg_user_id)
    #         data_worker.add_data(df)
    #     except Exception as e:
    #         pytest.fail(f"Fail to get_info: {e}")
    #
    # @freeze_time("2025-08-29 12:00:00")
    # def test_default_reminders(self,  data_worker):
    #     test = []
    #     for i in [0, 1, 3, 7]:
    #         if x := data_worker.get_upcoming_dates(i):
    #             test.append(dict_from_row(x))
    #     print(test)
    #     assert len(test) == 4, f'Not all records got from test_data{test}'
    #
    # @freeze_time("2025-12-20 12:00:00")
    # def test_custom_reminders(self, data_worker):
    #     data = dict_from_row(data_worker.get_upcoming_dates_custom_column())
    #     assert len(data) == 6
    #
    # def test_del_info(self, random_user):
    #     try:
    #         random_user.del_info()
    #         assert random_user.get_info() is None, f"Info is not deleted: {random_user.get_info()}"
    #     except Exception as e:
    #         pytest.fail(f"Fail to del_info: {e}")
