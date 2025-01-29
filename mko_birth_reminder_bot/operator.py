import logging
from mko_birth_reminder_bot.core import *
from pathlib import Path
logger = logging.getLogger(__name__)


class Operator:
    def __init__(self, user_id):
        self.user_id = int(user_id)
        self.user = TGUser(self.user_id)
        self.user_data = TGUserData(self.user_id)
        self.csv_worker = CSVWorker()
        self.user_init()

    def user_init(self, ):
        if self.user.is_exist is False:
            self.user.add_info()

    def import_data(self, csv_file):
        try:
            df = self.csv_worker.read_csv(csv_file=csv_file)
            df = self.csv_worker.prepare_dataframe(df)
            self.user_data.add_data(df)
            return "Данные успешно импортированы."
        except Exception as e:
            return str(e)


    def export_data(self):
        file_name = utils.generate_random_filename()
        df = self.user_data.get_all_records()
        return self.csv_worker.export_to_csv(df, file_name)


    def add_record(self, **data):
        try:
            self.user_data.add_record(**data)
            return "Запись успешно добавлена"
        except Exception as e:
            return str(e)

    def get_record_by_id(self, record_id):
        return self.user_data.get_record_by_id(record_id)

    def update_record_by_id(self, record_id, **data):
        try:
            self.user_data.update_record_by_id(record_id=record_id, **data)
            return "Запись успешно обновлена"
        except Exception as e:
            return str(e)

    def delete_record_by_id(self, record_id):
        try:
            self.user_data.del_record_by_id(record_id=record_id)
            return "Record was successfully deleted."
        except Exception as e:
            return str(e)

    def flush_date(self):
        self.user_data.flush_data()

    def del_info(self):
        self.user.del_info()

    def remove_tmp_file(self, file:Path):
        self.csv_worker.safe_file_delete(file)
