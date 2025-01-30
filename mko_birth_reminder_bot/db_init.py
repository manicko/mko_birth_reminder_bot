from mko_birth_reminder_bot.core import DBWorker, TGUsers




def init():
    with DBWorker() as db_worker:
        db_worker.create_table(TGUsers.TABLE_NAME, TGUsers.TABLE_FIELDS)



if __name__ == '__main__':
    init()
