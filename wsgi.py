"""WSGI entrypoint for Gunicorn/Render
Exports `app` callable from the application factory in `app_enhanced.py`.
"""
from app_enhanced import create_app

# Create app using production config by default
application = create_app('production')

# Gunicorn expects a variable named `app` or `application`. Provide both.
app = application
