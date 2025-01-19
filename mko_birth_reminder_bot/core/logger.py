import logging.config
from .config_reader import CONFIG

logging.config.dictConfig(CONFIG.log_settings)

