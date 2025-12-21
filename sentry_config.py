import logging
import os

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration

logger = logging.getLogger(__name__)

def setup_sentry():
    if sentry_sdk.Hub.current.client:
        return
    dsn = os.getenv("SENTRY_DSN")
    if not dsn:
        logger.warning("⚠️ SENTRY_DSN not found. Sentry is DISABLED.")
        return
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
            attach_stacktrace=True,
            environment = current_env,
        )
        logger.info(f"✅ Sentry tracking initialized in {current_env} mode.")
    except Exception as e:
        logger.error(f"❌ Failed to initialize Sentry: {e}")
