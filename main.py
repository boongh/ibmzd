import sys

from loguru import logger

from src import app
from src import config

if __name__ == "__main__":
    logger.remove()
    temp_logger = logger.add(sys.stderr, level="DEBUG")
    logger.debug("Starting GateKeeper")

    try:
        logger.debug("Loading configuration")
        app_conf = config.AppConfig.load_config("config.toml")
        logger.debug(f"Configuration loaded: {app_conf}")
    except Exception as e:
        logger.error(e)
        sys.exit(1)

    logger.remove(temp_logger)
    logger.add(sys.stderr, level=app_conf.log.level)
    logger.info(f"Log level set to {app_conf.log.level}")

    app.run(app_conf)
