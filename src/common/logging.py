import logging


LOG_FORMAT = "%(asctime)s | %(name)-18s | %(levelname)-8s | %(message)s"
DEFAULT_LOG_LEVEL = logging.INFO


def get_logger(log_level='DEBUG', name='main'):
    logging.basicConfig(format=LOG_FORMAT)
    # logging.getLogger("sqlitedict.SqliteMultithread").setLevel(logging.CRITICAL)
    # logging.getLogger("sqlitedict").setLevel(logging.CRITICAL)
    logging.getLogger("schedule").setLevel(logging.WARNING)  # Disable logging from schedule library
    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    return logger
