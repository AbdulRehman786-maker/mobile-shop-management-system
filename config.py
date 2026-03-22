import os
from datetime import timedelta

BASE_DIR = os.path.abspath(os.path.dirname(__file__))

def _normalize_database_url(raw_url: str | None) -> str | None:
    """Normalize relative SQLite URLs to absolute paths."""
    if not raw_url:
        return None
    if raw_url.startswith("sqlite:///"):
        path = raw_url.replace("sqlite:///", "", 1)
        if path and not os.path.isabs(path):
            abs_path = os.path.join(BASE_DIR, path)
            return f"sqlite:///{abs_path}"
    return raw_url


class Config:
    """Base configuration"""
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    SQLALCHEMY_DATABASE_URI = _normalize_database_url(
        os.environ.get('DATABASE_URL')
    ) or f"sqlite:///{os.path.join(BASE_DIR, 'instance', 'mobile_shop.db')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Session configuration
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # File upload configuration
    UPLOAD_FOLDER = os.environ.get('UPLOAD_FOLDER', 'app/static/uploads')
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_CONTENT_LENGTH', 16 * 1024 * 1024))  # 16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
    
    # Pagination
    ITEMS_PER_PAGE = 20

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    TESTING = False
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False

class TestingConfig(Config):
    """Testing configuration"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False

config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': ProductionConfig
}
