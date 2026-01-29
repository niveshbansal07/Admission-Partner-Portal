from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ..extensions import get_db


def create_lead_for_partner(
    partner_id: int,
    student_name: str,
    mobile: str,
    email: Optional[str],
    address: Optional[str],
    current_status: str,
) -> int:
    """
    Create a new lead for a partner.

    Expected `leads` schema (adapt as needed):
      leads(
        id, partner_id, student_name, mobile, email, address,
        current_status, lead_status, created_at, conversion_date
      )
    """
    db = get_db()
    cursor = db.cursor()
    now = datetime.utcnow()
    cursor.execute(
        """
        INSERT INTO leads
          (partner_id, student_name, mobile, email, address,
           current_status, lead_status, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            partner_id,
            student_name,
            mobile,
            email,
            address,
            current_status,
            "Pending",
            now,
        ),
    )
    db.commit()
    lead_id = cursor.lastrowid
    cursor.close()
    return lead_id


def list_leads_admin(
    partner_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
) -> List[Dict[str, Any]]:
    """
    Admin view of all leads with optional filters.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    filters = ["1=1"]
    params: List[Any] = []

    if partner_id:
        filters.append("partner_id = %s")
        params.append(partner_id)
    if status:
        filters.append("lead_status = %s")
        params.append(status)
    if date_from:
        filters.append("created_at >= %s")
        params.append(date_from)
    if date_to:
        filters.append("created_at <= %s")
        params.append(date_to)

    where_clause = " AND ".join(filters)
    cursor.execute(
        f"""
        SELECT l.id,
               l.partner_id,
               l.student_name,
               l.mobile,
               l.email,
               l.address,
               l.current_status,
               l.lead_status,
               l.created_at,
               l.conversion_date
        FROM leads l
        WHERE {where_clause}
        ORDER BY l.created_at DESC
        """,
        params,
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def list_leads_for_partner(partner_id: int) -> List[Dict[str, Any]]:
    """Partner view of their own leads."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id,
               student_name,
               mobile,
               email,
               address,
               current_status,
               lead_status,
               created_at,
               conversion_date
        FROM leads
        WHERE partner_id = %s
        ORDER BY created_at DESC
        """,
        (partner_id,),
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def has_lead_with_mobile(partner_id: int, mobile: str) -> bool:
    """Check if this partner already created a lead with the same mobile."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT id
        FROM leads
        WHERE partner_id = %s AND mobile = %s
        LIMIT 1
        """,
        (partner_id, mobile),
    )
    row = cursor.fetchone()
    cursor.close()
    return row is not None


def get_lead_by_id(lead_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a single lead."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT *
        FROM leads
        WHERE id = %s
        """,
        (lead_id,),
    )
    row = cursor.fetchone()
    cursor.close()
    return row


def update_lead_status(
    lead_id: int,
    new_status: str,
    changed_by_type: str,
    changed_by_id: int,
) -> Optional[Dict[str, Any]]:
    """
    Update the status of a lead.

    Returns updated lead row. Also logs status history.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT lead_status FROM leads WHERE id = %s", (lead_id,))
    row = cursor.fetchone()
    if not row:
        cursor.close()
        return None

    old_status = row["lead_status"]
    if old_status == new_status:
        cursor.close()
        return row

    now = datetime.utcnow()
    cursor.execute(
        """
        UPDATE leads
        SET lead_status = %s,
            conversion_date = CASE
                WHEN %s = 'Converted' THEN %s
                ELSE conversion_date
            END
        WHERE id = %s
        """,
        (new_status, new_status, now, lead_id),
    )

    # Log status change in a separate history table
    cursor.execute(
        """
        INSERT INTO lead_status_history
          (lead_id, old_status, new_status, changed_by_type, changed_by_id, changed_at)
        VALUES (%s, %s, %s, %s, %s, %s)
        """,
        (lead_id, old_status, new_status, changed_by_type, changed_by_id, now),
    )

    db.commit()

    cursor.execute("SELECT * FROM leads WHERE id = %s", (lead_id,))
    updated = cursor.fetchone()
    cursor.close()
    return updated


def get_admin_lead_metrics() -> Dict[str, Any]:
    """
    Aggregated metrics for admin dashboard.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)

    metrics: Dict[str, Any] = {}

    cursor.execute("SELECT COUNT(*) AS total_leads FROM leads")
    metrics["total_leads"] = cursor.fetchone()["total_leads"]

    cursor.execute(
        "SELECT COUNT(*) AS converted_leads FROM leads WHERE lead_status = 'Converted'"
    )
    metrics["converted_leads"] = cursor.fetchone()["converted_leads"]

    total = metrics["total_leads"] or 0
    converted = metrics["converted_leads"] or 0
    metrics["conversion_rate"] = (converted / total * 100.0) if total > 0 else 0.0

    # Monthly trend: group by year-month
    cursor.execute(
        """
        SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS ym,
               COUNT(*) AS total,
               SUM(lead_status = 'Converted') AS converted
        FROM leads
        GROUP BY ym
        ORDER BY ym DESC
        LIMIT 6
        """
    )
    metrics["monthly_trend"] = cursor.fetchall()

    cursor.close()
    return metrics


def get_partner_performance() -> List[Dict[str, Any]]:
    """
    Partner-wise performance for admin analytics.

    Includes total leads, converted leads, and payment aggregates.
    """
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute(
        """
        SELECT
          p.id AS partner_id,
          p.name AS partner_name,
          COUNT(DISTINCT l.id) AS total_leads,
          SUM(CASE WHEN l.lead_status = 'Converted' THEN 1 ELSE 0 END) AS converted_leads,
          COALESCE(
            SUM(CASE WHEN pay.status = 'Pending' THEN pay.amount END),
            0
          ) AS pending_amount,
          COALESCE(
            SUM(CASE WHEN pay.status = 'Released' THEN pay.amount END),
            0
          ) AS released_amount
        FROM partners p
        LEFT JOIN leads l ON l.partner_id = p.id
        LEFT JOIN payments pay ON pay.partner_id = p.id
        WHERE p.is_deleted = 0
        GROUP BY p.id, p.name
        ORDER BY total_leads DESC
        """
    )
    rows = cursor.fetchall()
    cursor.close()
    return rows


def get_partner_lead_metrics(partner_id: int) -> Dict[str, Any]:
    """Metrics for a specific partner."""
    db = get_db()
    cursor = db.cursor(dictionary=True)
    metrics: Dict[str, Any] = {}

    cursor.execute(
        "SELECT COUNT(*) AS total_leads FROM leads WHERE partner_id = %s",
        (partner_id,),
    )
    metrics["total_leads"] = cursor.fetchone()["total_leads"]

    cursor.execute(
        """
        SELECT COUNT(*) AS converted_leads
        FROM leads
        WHERE partner_id = %s AND lead_status = 'Converted'
        """,
        (partner_id,),
    )
    metrics["converted_leads"] = cursor.fetchone()["converted_leads"]

    total = metrics["total_leads"] or 0
    converted = metrics["converted_leads"] or 0
    metrics["conversion_rate"] = (converted / total * 100.0) if total > 0 else 0.0

    cursor.execute(
        """
        SELECT DATE_FORMAT(created_at, '%%Y-%%m') AS ym,
               COUNT(*) AS total
        FROM leads
        WHERE partner_id = %s
        GROUP BY ym
        ORDER BY ym DESC
        LIMIT 6
        """,
        (partner_id,),
    )
    metrics["monthly_trend"] = cursor.fetchall()

    cursor.close()
    return metrics

