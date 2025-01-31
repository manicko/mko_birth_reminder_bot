import logging.config
from .config import CONFIG

logging.config.dictConfig(CONFIG.LOGGING)

