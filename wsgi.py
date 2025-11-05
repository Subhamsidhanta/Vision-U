"""WSGI entrypoint for Gunicorn/Render
Exports `app` callable from the application factory in `app_enhanced.py`.
Includes robust startup logging and safe environment diagnostics to aid
production debugging (e.g., on Render when ports/envs are misconfigured).
"""
import os
import logging

# Configure logging for WSGI startup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d]: %(message)s'
)
logger = logging.getLogger(__name__)


def _log_env_snapshot():
    """Log a safe snapshot of relevant environment variables.
    Values for sensitive keys are not printed; only presence is logged.
    """
    safe_keys = [
        'FLASK_ENV', 'PORT', 'PYTHON_VERSION', 'RENDER', 'GUNICORN_CMD_ARGS'
    ]
    # Common provider-specific keys to show presence
    presence_only = ['DATABASE_URL', 'SECRET_KEY', 'RENDER_SERVICE_ID', 'RENDER_INSTANCE_ID']

    # Print explicit values for non-sensitive, short vars
    for key in safe_keys:
        # Special handling: group all RENDER_* keys
        if key == 'RENDER':
            render_keys = sorted(k for k in os.environ.keys() if k.startswith('RENDER_'))
            if render_keys:
                logger.info(f"ENV present keys (RENDER_*): {', '.join(render_keys)}")
            continue
        logger.info(f"ENV {key} = {os.environ.get(key, 'not set')}")

    # Presence-only logging for sensitive values
    for key in presence_only:
        logger.info(f"ENV {key}: {'set' if os.environ.get(key) else 'not set'}")


logger.info("Starting WSGI application...")
_log_env_snapshot()

try:
    from app_enhanced import create_app

    # Create app using production config by default
    logger.info("Creating Flask application with production config...")
    application = create_app('production')

    # Gunicorn expects a variable named `app` or `application`. Provide both.
    app = application

    logger.info("WSGI application created successfully! App is ready to serve.")

except Exception:
    # Log full traceback for easier diagnosis in production logs
    logger.exception("Failed to create WSGI application during startup")
    raise
