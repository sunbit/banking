import schedule
import _thread
import time

from functools import partial

import bank


def schedule_loop():
    while True:
        print('Run pending')
        try:
            schedule.run_pending()
        except Exception as exc:
            print(exc)
        time.sleep(2)


def run(bank_config):

    execute_update_all = partial(bank.update_all, bank_config)
    execute_update_all()

    #schedule.every().day.at("08:30").do(partial(bank.update_all, bank_config))
    schedule.every(1).minutes.do(execute_update_all)
    _thread.start_new_thread(schedule_loop, ())
