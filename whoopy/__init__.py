__version__ = "0.1.3"

import logging

try:
    # from . import auth
    from .client_v1 import WhoopClient, API_VERSION
    from .models.models_v1 import SPORT_IDS

    # import versions
    from . import client_vu7
    from . import client_v1
except Exception as ex:
    logging.error(f"Not all dependencies installed: {ex}")
