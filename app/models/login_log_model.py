from typing import Optional, Dict, Any
from datetime import datetime

from ..extensions import get_db


def log_login(user_type: str, user_id: int, ip_address: str, user_agent: str, jti: str):
    """
    Insert a login attempt record.

    Expected table schema (adjust as needed):
      login_logs(
        id, user_type, user_id, ip_address, user_agent,
        jti, login_time, logout_time, is_active
      )
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO login_logs
          (user_type, user_id, ip_address, user_agent, jti, login_time, is_active)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            user_type,
            user_id,
            ip_address,
            user_agent[:255],
            jti,
            datetime.utcnow(),
            1,
        ),
    )
    db.commit()
    cursor.close()


def deactivate_session(jti: str):
    """Mark a login_log row as inactive based on JWT ID (logout)."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE login_logs
        SET is_active = 0, logout_time = %s
        WHERE jti = %s AND is_active = 1
        """,
        (datetime.utcnow(), jti),
    )
    db.commit()
    cursor.close()


def is_token_active(jti: str) -> bool:
    """Check if a given JWT ID is still marked as active."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id
        FROM login_logs
        WHERE jti = %s AND is_active = 1
        """,
        (jti,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None

