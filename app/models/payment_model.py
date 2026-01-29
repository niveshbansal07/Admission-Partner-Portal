from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

from flask import current_app

from ..extensions import get_db


def payment_exists_for_lead(lead_id: int) -> bool:
    """Check if a payment record already exists for a given lead."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id
        FROM payments
        WHERE lead_id = %s
        """,
        (lead_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def create_payment_for_conversion(lead_id: int, partner_id: int) -> Optional[int]:
    """
    Create a pending payment for a converted lead if one does not already exist.
    """
    if payment_exists_for_lead(lead_id):
        return None

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute(
        "SELECT conversion_date FROM leads WHERE id = %s", (lead_id,)
    )
    row = cursor.fetchone()
    if not row or not row["conversion_date"]:
        cursor.close()
        return None

    conversion_date = row["conversion_date"]
    amount = current_app.config.get("DEFAULT_CONVERSION_AMOUNT", 10000.0)
    due_date = conversion_date + timedelta(days=15)

    cursor = db.cursor()
    cursor.execute(
        """
        INSERT INTO payments
          (partner_id, lead_id, amount, status, due_date, created_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (partner_id, lead_id, amount, "Pending", due_date, datetime.utcnow()),
    )
    db.commit()
    payment_id = cursor.lastrowid
    cursor.close()
    return payment_id


def list_payments_admin(
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    due_from: Optional[datetime] = None,
    due_to: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """Admin view of all payments."""
    db = get_db()
    cursor = db.cursor(dictionary=True)

    filters = ["1=1"]
    params: List[Any] = []

    if partner_id:
        filters.append("p.partner_id = %s")
        params.append(partner_id)
    if status:
        filters.append("p.status = %s")
        params.append(status)
    if due_from:
        filters.append("p.due_date >= %s")
        params.append(due_from)
    if due_to:
        filters.append("p.due_date <= %s")
        params.append(due_to)

    where_clause = " AND ".join(filters)
    cursor.execute(
        f"""
        SELECT p.id,
               p.partner_id,
               p.lead_id,
               p.amount,
               p.status,
               p.due_date,
               p.released_date,
               p.created_at
        FROM payments p
        WHERE {where_clause}
        ORDER BY p.due_date ASC
        """,
        params,
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def mark_payment_released(payment_id: int) -> None:
    """
    Set payment status to Released and set released_date.

    Only pending payments are updatable to keep history immutable.
    """
    db = get_db()
    cursor = db.cursor()
    now = datetime.utcnow()
    cursor.execute(
        """
        UPDATE payments
        SET status = %s,
            released_date = %s
        WHERE id = %s AND status = 'Pending'
        """,
        ("Released", now, payment_id),
    )
    db.commit()
    cursor.close()


def list_payments_for_partner(partner_id: int) -> List[Dict[str, Any]]:
    """Partner view of their payments."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id,
               lead_id,
               amount,
               status,
               due_date,
               released_date,
               created_at
        FROM payments
        WHERE partner_id = %s
        ORDER BY due_date ASC
        """,
        (partner_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def get_admin_payment_metrics() -> Dict[str, Any]:
    """Aggregate payment metrics for admin dashboard."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    metrics: Dict[str, Any] = {}

    cursor.execute(
        "SELECT COUNT(*) AS pending FROM payments WHERE status = 'Pending'"
    )
    metrics["pending_count"] = cursor.fetchone()["pending"]

    cursor.execute(
        "SELECT COUNT(*) AS released FROM payments WHERE status = 'Released'"
    )
    metrics["released_count"] = cursor.fetchone()["released"]

    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS pending_amount FROM payments WHERE status = 'Pending'"
    )
    metrics["pending_amount"] = float(cursor.fetchone()["pending_amount"])

    cursor.execute(
        "SELECT COALESCE(SUM(amount), 0) AS released_amount FROM payments WHERE status = 'Released'"
    )
    metrics["released_amount"] = float(cursor.fetchone()["released_amount"])

    cursor.close()
    return metrics


def get_partner_payment_metrics(partner_id: int) -> Dict[str, Any]:
    """Payment metrics for a specific partner."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    metrics: Dict[str, Any] = {}

    cursor.execute(
        """
        SELECT COUNT(*) AS pending,
               COALESCE(SUM(amount), 0) AS pending_amount
        FROM payments
        WHERE partner_id = %s AND status = 'Pending'
        """,
        (partner_id,),
    )
    row = cursor.fetchone()
    metrics["pending_count"] = row["pending"]
    metrics["pending_amount"] = float(row["pending_amount"])

    cursor.execute(
        """
        SELECT COUNT(*) AS released,
               COALESCE(SUM(amount), 0) AS released_amount
        FROM payments
        WHERE partner_id = %s AND status = 'Released'
        """,
        (partner_id,),
    )
    row = cursor.fetchone()
    metrics["released_count"] = row["released"]
    metrics["released_amount"] = float(row["released_amount"])

    cursor.close()
    return metrics

