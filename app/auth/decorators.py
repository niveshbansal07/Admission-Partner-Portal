from functools import wraps

from flask import jsonify
from flask_jwt_extended import (
    verify_jwt_in_request,
    get_jwt,
    get_jwt_identity,
)


def _role_required(required_role: str):
    """
    Internal helper for enforcing a specific role based on the JWT `role` claim
    and validating account state (active / not deleted).
    """

    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            claims = get_jwt()
            identity = get_jwt_identity() or {}
            role = claims.get("role")

            if role != required_role:
                return (
                    jsonify(
                        {
                            "msg": "Insufficient permissions",
                            "required_role": required_role,
                            "current_role": role,
                        }
                    ),
                    403,
                )

            # Extra safety: ensure underlying user account is still active.
            user_id = identity.get("id")
            if required_role == "admin":
                from ..models.admin_model import get_admin_by_id

                admin = get_admin_by_id(user_id)
                if not admin or not admin.get("is_active"):
                    return jsonify({"msg": "Admin account is inactive."}), 403
            elif required_role == "partner":
                from ..models.partner_model import get_partner_by_id

                partner = get_partner_by_id(user_id)
                if (
                    not partner
                    or partner.get("is_deleted")
                    or partner.get("status") != "active"
                ):
                    return jsonify({"msg": "Partner account is inactive."}), 403

            return fn(*args, **kwargs)

        return wrapper

    return decorator


def admin_required(fn):
    """Decorator to restrict endpoints to admin users only."""

    return _role_required("admin")(fn)


def partner_required(fn):
    """Decorator to restrict endpoints to partner users only."""

    return _role_required("partner")(fn)

