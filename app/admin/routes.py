from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_jwt_extended import jwt_required

from ..auth.decorators import admin_required
from ..models.partner_model import (
    list_partners,
    create_partner,
    update_partner_profile_admin,
    set_partner_status,
    soft_delete_partner,
    get_partner_by_id,
    count_active_partners,
)
from ..models.lead_model import (
    list_leads_admin,
    get_lead_by_id,
    update_lead_status,
    get_admin_lead_metrics,
    get_partner_performance,
)
from ..models.payment_model import (
    list_payments_admin,
    mark_payment_released,
    get_admin_payment_metrics,
)

admin_bp = Blueprint("admin", __name__, template_folder="../templates/admin")


@admin_bp.get("/dashboard")
@jwt_required()
@admin_required
def dashboard():
    """
    Admin analytics dashboard.
    """
    total_partners = count_active_partners()
    lead_metrics = get_admin_lead_metrics()
    payment_metrics = get_admin_payment_metrics()
    partner_perf = get_partner_performance()

    return render_template(
        "admin/dashboard.html",
        total_partners=total_partners,
        lead_metrics=lead_metrics,
        payment_metrics=payment_metrics,
        partner_performance=partner_perf,
    )


# -------------------------
# Partner management (CRUD)
# -------------------------


@admin_bp.get("/partners")
@jwt_required()
@admin_required
def partners_list():
    page = max(int(request.args.get("page", 1)), 1)
    status_filter = request.args.get("status") or None

    partners, total = list_partners(page=page, per_page=20, status=status_filter)
    has_next = total > page * 20
    has_prev = page > 1

    return render_template(
        "admin/partners.html",
        partners=partners,
        total=total,
        page=page,
        has_next=has_next,
        has_prev=has_prev,
        status_filter=status_filter,
    )


@admin_bp.post("/partners/create")
@jwt_required()
@admin_required
def partners_create():
    form = request.form
    name = (form.get("name") or "").strip()
    mobile = (form.get("mobile") or "").strip()
    password = (form.get("password") or "").strip()
    email = (form.get("email") or "").strip() or None
    status = form.get("status") or "active"
    shop_name = (form.get("shop_name") or "").strip() or None
    profession = (form.get("profession") or "").strip() or None
    address = (form.get("address") or "").strip() or None

    if not name or not mobile or not password:
        flash("Name, mobile and password are required.", "error")
        return redirect(url_for("admin.partners_list"))

    existing = get_partner_by_id  # type: ignore  # placeholder to satisfy lints
    # Mobile uniqueness check using existing helper
    from ..models.partner_model import get_partner_by_mobile

    if get_partner_by_mobile(mobile):
        flash("Mobile already exists for another partner.", "error")
        return redirect(url_for("admin.partners_list"))

    if status not in {"active", "inactive"}:
        status = "active"

    create_partner(
        name=name,
        mobile=mobile,
        password=password,
        email=email,
        status=status,
        shop_name=shop_name,
        profession=profession,
        address=address,
    )
    flash("Partner created successfully.", "success")
    return redirect(url_for("admin.partners_list"))


@admin_bp.post("/partners/<int:partner_id>/update")
@jwt_required()
@admin_required
def partners_update(partner_id: int):
    form = request.form
    name = (form.get("name") or "").strip()
    email = (form.get("email") or "").strip() or None
    status = form.get("status") or "active"
    shop_name = (form.get("shop_name") or "").strip() or None
    profession = (form.get("profession") or "").strip() or None
    address = (form.get("address") or "").strip() or None

    if status not in {"active", "inactive"}:
        status = "active"

    update_partner_profile_admin(
        partner_id=partner_id,
        name=name,
        email=email,
        status=status,
        shop_name=shop_name,
        profession=profession,
        address=address,
    )
    flash("Partner updated.", "success")
    return redirect(url_for("admin.partners_list"))


@admin_bp.post("/partners/<int:partner_id>/status")
@jwt_required()
@admin_required
def partners_status(partner_id: int):
    status = request.form.get("status") or "inactive"
    if status not in {"active", "inactive"}:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.partners_list"))

    set_partner_status(partner_id, status)
    flash("Partner status updated.", "success")
    return redirect(url_for("admin.partners_list"))


@admin_bp.post("/partners/<int:partner_id>/delete")
@jwt_required()
@admin_required
def partners_delete(partner_id: int):
    soft_delete_partner(partner_id)
    flash("Partner deleted.", "success")
    return redirect(url_for("admin.partners_list"))


# -------------------------
# Lead management
# -------------------------


@admin_bp.get("/leads")
@jwt_required()
@admin_required
def leads_list():
    partner_id = request.args.get("partner_id", type=int)
    status = request.args.get("status") or None
    date_from_raw = request.args.get("date_from") or None
    date_to_raw = request.args.get("date_to") or None

    date_from = (
        datetime.strptime(date_from_raw, "%Y-%m-%d") if date_from_raw else None
    )
    date_to = datetime.strptime(date_to_raw, "%Y-%m-%d") if date_to_raw else None

    leads = list_leads_admin(
        partner_id=partner_id,
        status=status,
        date_from=date_from,
        date_to=date_to,
    )

    # For filter dropdowns we reuse partners list (first page only)
    partners, _ = list_partners(page=1, per_page=100)

    return render_template(
        "admin/leads.html",
        leads=leads,
        partners=partners,
        partner_id=partner_id,
        status=status,
        date_from=date_from_raw,
        date_to=date_to_raw,
    )


@admin_bp.post("/leads/<int:lead_id>/status")
@jwt_required()
@admin_required
def leads_update_status(lead_id: int):
    new_status = request.form.get("status") or ""
    allowed_statuses = {"Pending", "In-Process", "Converted", "Not Converted"}

    if new_status not in allowed_statuses:
        flash("Invalid status.", "error")
        return redirect(url_for("admin.leads_list"))

    lead = get_lead_by_id(lead_id)
    if not lead:
        flash("Lead not found.", "error")
        return redirect(url_for("admin.leads_list"))

    old_status = lead["lead_status"]

    # Converted leads cannot be reconverted or downgraded
    if old_status == "Converted":
        flash("Converted leads cannot change status.", "error")
        return redirect(url_for("admin.leads_list"))

    # Apply status update & log history
    updated = update_lead_status(
        lead_id=lead_id,
        new_status=new_status,
        changed_by_type="admin",
        changed_by_id=0,  # could be set to admin id from JWT
    )

    # Conversion → payment logic
    if updated and new_status == "Converted":
        from ..models.payment_model import create_payment_for_conversion

        create_payment_for_conversion(
            lead_id=lead_id, partner_id=updated["partner_id"]
        )

    flash("Lead status updated.", "success")
    return redirect(url_for("admin.leads_list"))


# -------------------------
# Payment management
# -------------------------


@admin_bp.get("/payments")
@jwt_required()
@admin_required
def payments_list():
    partner_id = request.args.get("partner_id", type=int)
    status = request.args.get("status") or None
    due_from_raw = request.args.get("due_from") or None
    due_to_raw = request.args.get("due_to") or None

    due_from = (
        datetime.strptime(due_from_raw, "%Y-%m-%d") if due_from_raw else None
    )
    due_to = datetime.strptime(due_to_raw, "%Y-%m-%d") if due_to_raw else None

    payments = list_payments_admin(
        partner_id=partner_id,
        status=status,
        due_from=due_from,
        due_to=due_to,
    )
    partners, _ = list_partners(page=1, per_page=100)

    return render_template(
        "admin/payments.html",
        payments=payments,
        partners=partners,
        partner_id=partner_id,
        status=status,
        due_from=due_from_raw,
        due_to=due_to_raw,
    )


@admin_bp.post("/payments/<int:payment_id>/release")
@jwt_required()
@admin_required
def payments_release(payment_id: int):
    mark_payment_released(payment_id)
    flash("Payment marked as released.", "success")
    return redirect(url_for("admin.payments_list"))


