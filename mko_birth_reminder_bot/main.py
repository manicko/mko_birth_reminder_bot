from mko_birth_reminder_bot.core import CSVWorker,DBWorker, TGUser, TGUserData, CONFIG
import mko_birth_reminder_bot.core.logger



def init():
    with DBWorker() as db_worker:
        db_worker.create_table(TGUser.TABLE_NAME, TGUser.TABLE_FIELDS)


def main():
    tg_user_id = 7777
    data_con = TGUser(tg_user_id)

    csv = CSVWorker()

    df = csv.read_csv('dates.csv')
    df = csv.prepare_dataframe(df)
    if len(df.columns) != 0:
        db_con.add_data(df)


if __name__ == '__main__':
    main()
