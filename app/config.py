import os
from datetime import timedelta

from dotenv import load_dotenv


BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(BASE_DIR, ".env"))


class Config:
    """Base configuration loaded from environment variables."""

    SECRET_KEY = os.getenv("SECRET_KEY", "change-me-in-production")
    JWT_SECRET_KEY = os.getenv("JWT_SECRET_KEY", "change-me-too")

    MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", "3306"))
    MYSQL_USER = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "0522nivesh#")
    MYSQL_DB = os.getenv("MYSQL_DB", "admission_partner_portal")

    # JWT configuration
    JWT_TOKEN_LOCATION = ["headers"]
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=15)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)
    JWT_COOKIE_SECURE = False  # set True in production with HTTPS

    # Security headers
    SESSION_COOKIE_SECURE = False  # set True in production with HTTPS
    REMEMBER_COOKIE_SECURE = False
    PREFERRED_URL_SCHEME = "https"

    # Business configuration
    DEFAULT_CONVERSION_AMOUNT = float(os.getenv("DEFAULT_CONVERSION_AMOUNT", "10000.0"))


class DevelopmentConfig(Config):
    FLASK_ENV = "development"
    DEBUG = True


class ProductionConfig(Config):
    FLASK_ENV = "production"
    DEBUG = False


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
}


def get_config():
    env = os.getenv("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)

