from typing import Optional, Dict, Any, List, Tuple

from ..extensions import get_db, hash_password


def get_partner_by_mobile(mobile: str) -> Optional[Dict[str, Any]]:
    """
    Fetch a partner row by mobile.

    Expected table schema (adjust as needed):
      partners(id, name, email, mobile, password_hash, status, is_deleted)
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, name, email, mobile, password_hash, status, is_deleted
        FROM partners
        WHERE mobile = %s
        """,
        (mobile,),
    )
    partner = cursor.fetchone()
    cursor.close()
    return partner


def get_partner_by_id(partner_id: int) -> Optional[Dict[str, Any]]:
    """Fetch partner by primary key."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id, name, email, mobile, password_hash, status, is_deleted,
               shop_name, profession, address
        FROM partners
        WHERE id = %s
        """,
        (partner_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row


def list_partners(
    page: int = 1,
    per_page: int = 20,
    status: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], int]:
    """
    Paginated list of partners for admin.

    Returns (rows, total_count).
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    filters = ["is_deleted = 0"]
    params: List[Any] = []

    if status in {"active", "inactive"}:
        filters.append("status = %s")
        params.append(status)

    where_clause = " AND ".join(filters)

    # Total count
    cursor.execute(f"SELECT COUNT(*) AS cnt FROM partners WHERE {where_clause}", params)
    total = cursor.fetchone()["cnt"]

    offset = (page - 1) * per_page
    cursor.execute(
        f"""
        SELECT id, name, email, mobile, status, shop_name, profession, address
        FROM partners
        WHERE {where_clause}
        ORDER BY id DESC
        LIMIT %s OFFSET %s
        """,
        (*params, per_page, offset),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows, total


def count_active_partners() -> int:
    """Total number of non-deleted partners (any status)."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM partners
        WHERE is_deleted = 0
        """
    )
    row = cursor.fetchone()
    cursor.close()
    return row["cnt"]


def create_partner(
    name: str,
    mobile: str,
    password: str,
    email: Optional[str] = None,
    status: str = "active",
    shop_name: Optional[str] = None,
    profession: Optional[str] = None,
    address: Optional[str] = None,
) -> int:
    """Create a new partner with a bcrypt password hash."""
    db = get_db()
    cursor = db.cursor()
    password_hash = hash_password(password)
    cursor.execute(
        """
        INSERT INTO partners
          (name, mobile, email, password_hash, status, is_deleted,
           shop_name, profession, address)
        VALUES (%s, %s, %s, %s, %s, 0, %s, %s, %s)
        """,
        (name, mobile, email, password_hash, status, shop_name, profession, address),
    )
    db.commit()
    partner_id = cursor.lastrowid
    cursor.close()
    return partner_id


def update_partner_profile_admin(
    partner_id: int,
    name: str,
    email: Optional[str],
    status: str,
    shop_name: Optional[str],
    profession: Optional[str],
    address: Optional[str],
) -> None:
    """Admin-side editable fields for partner profile (no password/mobile)."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE partners
        SET name = %s,
            email = %s,
            status = %s,
            shop_name = %s,
            profession = %s,
            address = %s
        WHERE id = %s
        """,
        (name, email, status, shop_name, profession, address, partner_id),
    )
    db.commit()
    cursor.close()


def update_partner_profile_self(
    partner_id: int,
    name: str,
    shop_name: Optional[str],
    profession: Optional[str],
    email: Optional[str],
    address: Optional[str],
) -> None:
    """
    Partner self-service profile update.

    Mobile and password are intentionally not updatable here.
    """
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE partners
        SET name = %s,
            shop_name = %s,
            profession = %s,
            email = %s,
            address = %s
        WHERE id = %s AND is_deleted = 0
        """,
        (name, shop_name, profession, email, address, partner_id),
    )
    db.commit()
    cursor.close()


def set_partner_status(partner_id: int, status: str) -> None:
    """Activate / deactivate partner account."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE partners
        SET status = %s
        WHERE id = %s AND is_deleted = 0
        """,
        (status, partner_id),
    )
    db.commit()
    cursor.close()


def soft_delete_partner(partner_id: int) -> None:
    """Soft delete partner – they can no longer log in or create leads."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute(
        """
        UPDATE partners
        SET is_deleted = 1
        WHERE id = %s
        """,
        (partner_id,),
    )
    db.commit()
    cursor.close()

