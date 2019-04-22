import re
import schedule
import _thread
import time

from functools import partial
from common.logging import get_logger

import bank

logger = get_logger(name='scheduler')


def schedule_loop():
    logger.info('Starting scheduler')
    for count, job in enumerate(schedule.jobs, start=1):
        logger.info('Job #{} of {}: {}'.format(
            count,
            len(schedule.jobs),
            re.sub(r'(.*?)do.*', r'\1execute "{}"'.format(list(job.tags)[0]), job.__repr__())
        ))
    while True:
        try:
            schedule.run_pending()
        except Exception as exc:
            print(exc)
        time.sleep(2)


def run_once(task, task_name):

    def wrapper():
        time.sleep(2)
        logger.info('Running one-time task "{}"'.format(task_name))
        task()
        logger.info('Finished one-time task "{}"'.format(task_name))

    _thread.start_new_thread(wrapper, ())


def run(config):
    execute_update_all = partial(bank.update_all, config, bank.env())

    for scrapping_hour in config.scheduler.scrapping_hours:
        schedule.every().day.at(scrapping_hour).do(execute_update_all).tag('Update all transactions from banks', 'run_at_start')

    # Start scheduling thread
    _thread.start_new_thread(schedule_loop, ())

    # Run the scrapping job once, non blocking
    run_once(execute_update_all, 'Update all transactions from banks')
