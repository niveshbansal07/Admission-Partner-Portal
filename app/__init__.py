from flask import Flask, render_template, jsonify

from .config import get_config
from .extensions import jwt, close_db
from .models.login_log_model import is_token_active
from flask_jwt_extended import (
    JWTManager,
    get_jwt,
)


def create_app():
    """Application factory."""
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config.from_object(get_config())

    # Initialize extensions
    jwt.init_app(app)

    # JWT token blacklist / error handlers using login_logs
    @jwt.token_in_blocklist_loader
    def check_if_token_revoked(jwt_header, jwt_payload):
        jti = jwt_payload.get("jti")
        # If there is no record for this jti, treat token as revoked
        return not is_token_active(jti) if jti else True

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return (
            jsonify({"msg": "Token has been revoked. Please log in again."}),
            401,
        )

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return (
            jsonify({"msg": "Token has expired. Please log in again."}),
            401,
        )

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return (
            jsonify({"msg": "Invalid token."}),
            422,
        )

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return (
            jsonify({"msg": "Missing authorization token."}),
            401,
        )

    # DB teardown
    app.teardown_appcontext(close_db)

    # Blueprints
    from .auth.routes import auth_bp
    from .admin.routes import admin_bp
    from .partner.routes import partner_bp
    from .reports.routes import reports_bp

    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(partner_bp, url_prefix="/partner")
    app.register_blueprint(reports_bp, url_prefix="/reports")

    # Basic index route
    @app.route("/")
    def index():
        return render_template("index.html")

    # Global error handlers
    @app.errorhandler(404)
    def not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def internal_error(error):
        return render_template("errors/500.html"), 500

    return app

