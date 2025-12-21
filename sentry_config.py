import logging
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger("sentry_setup")

def setup_sentry():
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.warning("⚠️ SENTRY_DSN not found. Sentry is DISABLED.")
    current_env = os.getenv("ENV","development")
    sentry_logging = LoggingIntegration(
        level = logging.INFO,
        event_level = logging.ERROR,
    )
    try:
        sentry_sdk.init(
            dsn = dsn,
            integrations = [sentry_logging],
            traces_sample_rate = 1.0,
            profiles_sample_rate = 1.0,
            send_default_pii = True,
            environment = current_env,
        )
        logger.info(f"✅ Sentry tracking initialized in {current_env} mode.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")
