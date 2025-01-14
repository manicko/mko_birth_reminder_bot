from core import CSVWorker,DBWorker, TGUser, TGUserData, ConfigReader, Logger
from pathlib import Path

config = ConfigReader()
logger = Logger(config.logs)

def init():
    with DBWorker(config.db_settings, logger) as db_worker:
        db_worker.create_table(TGUser.TABLE_NAME, TGUser.TABLE_FIELDS)


def main():
    tg_user_id = 'id_7777'
    data_con = TGUser(config.db_settings, logger, tg_user_id)

    csv = CSVWorker(config, logger)

    df = csv.read_csv('dates.csv')
    df = csv.prepare_dataframe(df)
    if len(df.columns) != 0:
        db_con.add_data(df)


if __name__ == '__main__':
    main()
