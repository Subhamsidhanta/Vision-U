"""WSGI entrypoint for Gunicorn/Render
Exports `app` callable from the application factory in `app_enhanced.py`.
"""
import os
import logging

# Configure logging for WSGI startup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s [%(filename)s:%(lineno)d]: %(message)s'
)
logger = logging.getLogger(__name__)

logger.info("Starting WSGI application...")
logger.info(f"FLASK_ENV: {os.environ.get('FLASK_ENV', 'not set')}")
logger.info(f"PORT: {os.environ.get('PORT', 'not set')}")
logger.info(f"DATABASE_URL: {'set' if os.environ.get('DATABASE_URL') else 'not set'}")

try:
    from app_enhanced import create_app
    
    # Create app using production config by default
    logger.info("Creating Flask application with production config...")
    application = create_app('production')
    
    # Gunicorn expects a variable named `app` or `application`. Provide both.
    app = application
    
    logger.info("WSGI application created successfully!")
    
except Exception as e:
    logger.error(f"Failed to create WSGI application: {e}")
    raise
