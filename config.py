"""
Configuration management for Vision U application
"""
import os
from urllib.parse import urlparse, urlunparse
from typing import Type
from dotenv import load_dotenv

load_dotenv()

class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    API_KEY = os.environ.get('API_KEY')
    
    # Security configurations
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None
    SESSION_COOKIE_SECURE = os.environ.get('SESSION_COOKIE_SECURE', 'False').lower() == 'true'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Rate limiting
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_DEFAULT = "100 per hour"
    
    # Application settings
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    
    @staticmethod
    def init_app(app):
        """Initialize application with this config"""
        pass

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'sqlite:///instance/users.db'
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    SESSION_COOKIE_SECURE = True
    
    # PostgreSQL connection pool settings for better performance
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 120,
        'pool_pre_ping': True,
        'max_overflow': 20
    }
    
    @classmethod
    def get_database_uri(cls):
        """Get database URI from environment with proper format conversion"""
        database_url = os.environ.get('DATABASE_URL')
        
        if not database_url:
            # Check for alternative database environment variables
            alternative_vars = {
                'POSTGRES_URL': os.environ.get('POSTGRES_URL'),
                'POSTGRESQL_URL': os.environ.get('POSTGRESQL_URL'),
                'DB_URL': os.environ.get('DB_URL'),
            }
            
            # Try to find any available database URL
            for var_name, var_value in alternative_vars.items():
                if var_value:
                    print(f"Using {var_name} as database URL")
                    database_url = var_value
                    break
            
            if not database_url:
                # Show all environment variables for debugging
                all_env_vars = list(os.environ.keys())
                db_related_vars = [k for k in all_env_vars if any(term in k.upper() for term in ['DATABASE', 'DB', 'POSTGRES', 'SQL'])]
                
                error_msg = (
                    'DATABASE_URL environment variable is required in production.\n'
                    f'Available database-related environment variables: {db_related_vars}\n'
                    f'All environment variables: {sorted(all_env_vars)}\n'
                    'Please connect your PostgreSQL database to your Render web service manually:\n'
                    '1. Go to your Render dashboard\n'
                    '2. Select your web service\n'
                    '3. Go to Environment tab\n'
                    '4. Click "Add Environment Variable"\n'
                    '5. Connect your vision-u-db database'
                )
                raise RuntimeError(error_msg)
        
        # Handle PostgreSQL URL format conversion
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        # Ensure SSL when using external Render Postgres host (non-internal)
        try:
            parsed = urlparse(database_url)
            host = parsed.hostname or ""
            if host.endswith('render.com') and '-internal' not in host:
                # Append sslmode=require if not already present
                if 'sslmode=' not in (parsed.query or ''):
                    sep = '&' if parsed.query else ''
                    new_query = f"{parsed.query}{sep}sslmode=require"
                    parsed = parsed._replace(query=new_query)
                    database_url = urlunparse(parsed)
        except Exception:
            # If parsing fails, leave URL unchanged
            pass
        
        return database_url
    
    @classmethod
    def init_app(cls, app):
        """Initialize the app with this configuration"""
        Config.init_app(app)
        
        # Set database URI at app initialization time
        if not app.config.get('SQLALCHEMY_DATABASE_URI'):
            app.config['SQLALCHEMY_DATABASE_URI'] = cls.get_database_uri()
        
        # Log to stderr in production
        import logging
        from logging import StreamHandler
        file_handler = StreamHandler()
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

# Configuration mapping
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config() -> Type[Config]:
    """Get configuration based on environment"""
    return config[os.getenv('FLASK_ENV', 'default')]