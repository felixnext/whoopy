__version__ = "0.2.1"

import logging

try:
    # from . import auth
    from . import models
    from . import handlers
    from .models.models_v1 import SPORT_IDS
    from .client_v1 import WhoopClient, API_VERSION
except Exception as ex:
    logging.error(f"Error importing whoopy: {ex}")

try:
    # import versions
    from . import client_vu7
    from . import client_v1
except Exception as ex:
    logging.error(f"Not all dependencies installed: {ex}")
