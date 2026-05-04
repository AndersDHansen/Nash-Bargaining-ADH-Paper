import logging

def get_logger(name: str) -> logging.Logger:
    """Get a logger with a shortened name, stripping the package prefix."""
    short_name = name.replace("ppa_symmetric_info.", "")
    return logging.getLogger(short_name)