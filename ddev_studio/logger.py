# -*- coding: utf-8 -*-
"""
Sistema de logging estructurado y centralizado para DDEV Studio.
"""

import logging
import os
import sys

LOGGER_NAME = "ddev_studio"
logger = logging.getLogger(LOGGER_NAME)


def setup_logger(verbose: bool = False) -> logging.Logger:
    """
    Configura el logger global de DDEV Studio.
    Si verbose es True, existe la variable de entorno DDEV_STUDIO_DEBUG=1,
    o se pasa el argumento '--debug' en sys.argv, activa el nivel DEBUG.
    """
    is_debug = (
        verbose
        or os.environ.get("DDEV_STUDIO_DEBUG", "").lower() in ["1", "true", "yes"]
        or "--debug" in sys.argv
    )

    level = logging.DEBUG if is_debug else logging.INFO
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        formatter = logging.Formatter(
            fmt="[%(levelname)s] %(asctime)s [%(name)s:%(filename)s:%(lineno)d] %(message)s",
            datefmt="%H:%M:%S"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    return logger
