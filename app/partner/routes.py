from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..auth.decorators import partner_required
from ..models.partner_model import (
    get_partner_by_id,
    update_partner_profile_self,
)
from ..models.lead_model import (
    list_leads_for_partner,
    create_lead_for_partner,
    has_lead_with_mobile,
    get_partner_lead_metrics,
)
from ..models.payment_model import (
    list_payments_for_partner,
    get_partner_payment_metrics,
)

partner_bp = Blueprint("partner", __name__, template_folder="../templates/partner")


@partner_bp.get("/dashboard")
@jwt_required()
@partner_required
def dashboard():
    """Partner dashboard with quick metrics."""
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")

    lead_metrics = get_partner_lead_metrics(partner_id)
    payment_metrics = get_partner_payment_metrics(partner_id)

    return render_template(
        "partner/dashboard.html",
        lead_metrics=lead_metrics,
        payment_metrics=payment_metrics,
    )


# -------------------------
# Profile management
# -------------------------


@partner_bp.get("/profile")
@jwt_required()
@partner_required
def profile():
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")
    partner = get_partner_by_id(partner_id)
    return render_template("partner/profile.html", partner=partner)


@partner_bp.post("/profile/update")
@jwt_required()
@partner_required
def profile_update():
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")

    form = request.form
    name = (form.get("name") or "").strip()
    shop_name = (form.get("shop_name") or "").strip() or None
    profession = (form.get("profession") or "").strip() or None
    email = (form.get("email") or "").strip() or None
    address = (form.get("address") or "").strip() or None

    update_partner_profile_self(
        partner_id=partner_id,
        name=name,
        shop_name=shop_name,
        profession=profession,
        email=email,
        address=address,
    )
    flash("Profile updated.", "success")
    return redirect(url_for("partner.profile"))


# -------------------------
# Lead creation & tracking
# -------------------------


@partner_bp.get("/leads")
@jwt_required()
@partner_required
def leads_list():
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")
    leads = list_leads_for_partner(partner_id)
    duplicate = request.args.get("duplicate") == "1"
    return render_template(
        "partner/leads.html",
        leads=leads,
        duplicate=duplicate,
    )


@partner_bp.post("/leads/create")
@jwt_required()
@partner_required
def leads_create():
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")

    partner = get_partner_by_id(partner_id)
    if not partner or partner.get("is_deleted") or partner.get("status") != "active":
        # Extra guard, though decorator also enforces this.
        flash("Your account is inactive. You cannot create leads.", "error")
        return redirect(url_for("partner.leads_list"))

    form = request.form
    student_name = (form.get("student_name") or "").strip()
    mobile = (form.get("mobile") or "").strip()
    email = (form.get("email") or "").strip() or None
    address = (form.get("address") or "").strip() or None
    current_status = (form.get("current_status") or "Study").strip()

    if not student_name or not mobile:
        flash("Student name and mobile are required.", "error")
        return redirect(url_for("partner.leads_list"))

    duplicate = has_lead_with_mobile(partner_id, mobile)

    create_lead_for_partner(
        partner_id=partner_id,
        student_name=student_name,
        mobile=mobile,
        email=email,
        address=address,
        current_status=current_status,
    )

    flash("Lead created successfully.", "success")
    # Optional duplicate warning flag
    return redirect(
        url_for("partner.leads_list", duplicate="1" if duplicate else "0")
    )


# -------------------------
# Payments & reports
# -------------------------


@partner_bp.get("/payments")
@jwt_required()
@partner_required
def payments_list():
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")
    payments = list_payments_for_partner(partner_id)
    return render_template("partner/payments.html", payments=payments)


@partner_bp.get("/reports")
@jwt_required()
@partner_required
def reports():
    identity = get_jwt_identity() or {}
    partner_id = identity.get("id")

    lead_metrics = get_partner_lead_metrics(partner_id)
    payment_metrics = get_partner_payment_metrics(partner_id)

    return render_template(
        "partner/reports.html",
        lead_metrics=lead_metrics,
        payment_metrics=payment_metrics,
    )


