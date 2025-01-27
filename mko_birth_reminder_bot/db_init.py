from mko_birth_reminder_bot.core import CSVWorker,DBWorker, TGUser, TGUserData, CONFIG
import mko_birth_reminder_bot.core.logger



def init():
    with DBWorker() as db_worker:
        db_worker.create_table(TGUser.TABLE_NAME, TGUser.TABLE_FIELDS)



if __name__ == '__main__':
    init()
