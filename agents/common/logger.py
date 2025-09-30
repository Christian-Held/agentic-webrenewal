# D:\projects\helddigital\projects\agentic-webrenewal\agents\common\logger.py
import logging
from logging import Logger
from typing import Optional

def get_logger(name: str, level: int = logging.INFO) -> Logger:
    """
    Create and configure a module-level logger with consistent format.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(level)
        handler = logging.StreamHandler()
        fmt = "[%(asctime)s] %(levelname)s %(name)s :: %(message)s"
        handler.setFormatter(logging.Formatter(fmt))
        logger.addHandler(handler)
        logger.propagate = False
    return logger

def set_level(logger: Logger, level: int) -> None:
    for h in logger.handlers:
        h.setLevel(level)
    logger.setLevel(level)
