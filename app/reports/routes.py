from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..auth.decorators import admin_required, partner_required
from ..models.partner_model import count_active_partners
from ..models.lead_model import (
    get_admin_lead_metrics,
    get_partner_lead_metrics,
    get_partner_performance,
)
from ..models.payment_model import (
    get_admin_payment_metrics,
    get_partner_payment_metrics,
)

reports_bp = Blueprint("reports", __name__)


@reports_bp.get("/admin/summary")
@jwt_required()
@admin_required
def admin_summary():
    """
    JSON summary for admin analytics dashboard.
    """
    total_partners = count_active_partners()
    lead_metrics = get_admin_lead_metrics()
    payment_metrics = get_admin_payment_metrics()
    partner_perf = get_partner_performance()

    return (
        jsonify(
            {
                "total_partners": total_partners,
                "lead_metrics": lead_metrics,
                "payment_metrics": payment_metrics,
                "partner_performance": partner_perf,
            }
        ),
        200,
    )


@reports_bp.get("/partner/summary")
@jwt_required()
@partner_required
def partner_summary():
    """
    JSON summary of metrics for a specific partner.
    """
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")

    lead_metrics = get_partner_lead_metrics(partner_id)
    payment_metrics = get_partner_payment_metrics(partner_id)

    return (
        jsonify(
            {
                "lead_metrics": lead_metrics,
                "payment_metrics": payment_metrics,
            }
        ),
        200,
    )


