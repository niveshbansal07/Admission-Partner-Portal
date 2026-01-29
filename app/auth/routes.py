from flask import Blueprint, request, jsonify, render_template
from flask_jwt_extended import (
    create_access_token,
    create_refresh_token,
    get_jwt,
    get_jwt_identity,
    jwt_required,
    decode_token,
)

from ..extensions import check_password
from ..models.admin_model import get_admin_by_email
from ..models.partner_model import get_partner_by_mobile
from ..models.login_log_model import log_login, deactivate_session, is_token_active

auth_bp = Blueprint("auth", __name__)

@auth_bp.get("/admin-login")
def admin_login_page():
    return render_template("auth/admin_login.html")

@auth_bp.post("/admin-login")
def admin_login():
    """
    Admin login using email + password.

    Returns JWT access + refresh tokens on success.
    """
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = (data.get("password") or "").strip()

    if not email or not password:
        return jsonify({"msg": "Email and password are required"}), 400

    admin = get_admin_by_email(email)
    if not admin or not admin.get("is_active"):
        # Do not leak which field is incorrect
        return jsonify({"msg": "Invalid credentials"}), 401

    if not check_password(password, admin["password_hash"]):
        return jsonify({"msg": "Invalid credentials"}), 401

    identity = {"id": admin["id"], "role": "admin"}
    additional_claims = {"role": "admin"}

    access_token = create_access_token(
        identity=identity, additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        identity=identity, additional_claims=additional_claims
    )

    # Log login attempt and associate the access-token JTI with a session.
    # We decode the freshly created token to obtain the JTI.
    decoded = decode_token(access_token)
    jti = decoded.get("jti")
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    if jti:
        log_login("admin", admin["id"], ip, ua, jti)

    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": admin["id"],
                    "name": admin.get("name"),
                    "email": admin["email"],
                    "role": "admin",
                },
            }
        ),
        200,
    )


@auth_bp.get("/partner-login")
def partner_login_page():
    return render_template("auth/partner_login.html")

@auth_bp.post("/partner-login")
def partner_login():
    """
    Partner login using mobile + password.
    """
    data = request.get_json(silent=True) or {}
    mobile = (data.get("mobile") or "").strip()
    password = (data.get("password") or "").strip()

    if not mobile or not password:
        return jsonify({"msg": "Mobile and password are required"}), 400

    partner = get_partner_by_mobile(mobile)
    if not partner or partner.get("is_deleted") or partner.get("status") != "active":
        return jsonify({"msg": "Invalid credentials"}), 401

    if not check_password(password, partner["password_hash"]):
        return jsonify({"msg": "Invalid credentials"}), 401

    identity = {"id": partner["id"], "role": "partner"}
    additional_claims = {"role": "partner"}

    access_token = create_access_token(
        identity=identity, additional_claims=additional_claims
    )
    refresh_token = create_refresh_token(
        identity=identity, additional_claims=additional_claims
    )

    decoded = decode_token(access_token)
    jti = decoded.get("jti")
    ip = request.remote_addr or ""
    ua = request.headers.get("User-Agent", "")
    if jti:
        log_login("partner", partner["id"], ip, ua, jti)

    return (
        jsonify(
            {
                "access_token": access_token,
                "refresh_token": refresh_token,
                "user": {
                    "id": partner["id"],
                    "name": partner.get("name"),
                    "mobile": partner["mobile"],
                    "role": "partner",
                },
            }
        ),
        200,
    )


@auth_bp.post("/refresh")
@jwt_required(refresh=True)
def refresh_token():
    """
    Issue a new access token using a valid refresh token.
    """
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")

    additional_claims = {"role": role}
    access_token = create_access_token(identity=identity, additional_claims=additional_claims)

    return jsonify({"access_token": access_token}), 200


@auth_bp.post("/logout")
@jwt_required()
def logout():
    """
    Log out the current user by marking their JWT as inactive in login_logs.
    """
    jti = get_jwt().get("jti")
    if jti:
        deactivate_session(jti)
    return jsonify({"msg": "Logged out successfully"}), 200


@auth_bp.get("/me")
@jwt_required()
def me():
    """
    Simple endpoint to get the current authenticated user's identity.
    """
    identity = get_jwt_identity()
    claims = get_jwt()
    role = claims.get("role")
    return jsonify({"user": identity, "role": role}), 200

