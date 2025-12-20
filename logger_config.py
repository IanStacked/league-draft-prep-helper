import logging
import sys


def setup_logging():
    logger = logging.getLogger("league_bot")
    logger.setLevel(logging.INFO) # Capture everything INFO and above (WARNING, ERROR)
    c_handler = logging.StreamHandler(sys.stdout)
    c_format = logging.Formatter(
        "%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s",
        datefmt="%m-%d-%Y %H:%M:%S"
    )
    c_handler.setFormatter(c_format)
    if not logger.handlers:
        logger.addHandler(c_handler)
    return logger

logger = setup_logging()
