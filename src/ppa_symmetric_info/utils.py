import logging


def get_logger(name: str) -> logging.Logger:
    short_name = name.replace("ppa_symmetric_info.", "")
    return logging.getLogger(short_name)
