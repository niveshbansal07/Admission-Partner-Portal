from typing import Optional, Dict, Any

from ..extensions import get_db


def get_admin_by_email(email: str) -> Optional[Dict[str, Any]]:
    """
    Fetch an admin row by email.

    Expected table schema (adjust as needed):
      admins(id, email, password_hash, name, is_active, created_at)
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, email, password_hash, name, is_active
        FROM admins
        WHERE email = %s
        """,
        (email,),
    )
    admin = cursor.fetchone()
    cursor.close()
    return admin


def get_admin_by_id(admin_id: int) -> Optional[Dict[str, Any]]:
    """Fetch an admin row by ID."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, email, password_hash, name, is_active
        FROM admins
        WHERE id = %s
        """,
        (admin_id,),
    )
    admin = cursor.fetchone()
    cursor.close()
    return admin


