import mysql.connector
from flask import current_app, g
from flask_jwt_extended import JWTManager
import bcrypt

jwt = JWTManager()


def get_db():
    """
    Get a per-request MySQL connection.

    Uses raw MySQL connector, no ORM. Connection is stored on `g`
    so it can be reused within the same request and closed on teardown.
    """
    if "db" not in g:
        cfg = current_app.config
        g.db = mysql.connector.connect(
            host=cfg["MYSQL_HOST"],
            port=cfg["MYSQL_PORT"],
            user=cfg["MYSQL_USER"],
            password=cfg["MYSQL_PASSWORD"],
            database=cfg["MYSQL_DB"],
            auth_plugin="mysql_native_password",
        )
    return g.db


def close_db(e=None):
    """Close the DB connection at the end of the request."""
    db = g.pop("db", None)
    if db is not None:
        db.close()


def hash_password(plain_password: str) -> str:
    """Hash a plain-text password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(plain_password.encode("utf-8"), salt)
    return hashed.decode("utf-8")


def check_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain-text password against a bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"), hashed_password.encode("utf-8")
        )
    except ValueError:
        # Handles invalid hash formats gracefully
        return False

