"""Stock Review Intelligence - Alpha module."""

import secrets

from flask import Blueprint, jsonify, request
from stock_checker.alpha.models.database import db

MUTATING_METHODS = {"POST", "PUT", "DELETE", "PATCH"}


def create_alpha_blueprint():
    """Create and configure the Alpha blueprint."""
    alpha_bp = Blueprint(
        "alpha",
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="static",
        url_prefix="/alpha",
    )

    @alpha_bp.before_request
    def check_api_key_for_mutations():
        """Require API key for state-mutating requests when APP_API_KEY is set."""
        if request.method not in MUTATING_METHODS:
            return
        from flask import current_app
        app_key = current_app.config.get("APP_API_KEY", "")
        if not app_key:
            return  # not configured, allow (dev mode)
        provided = request.headers.get("X-API-Key", "")
        if not secrets.compare_digest(provided, app_key):
            return jsonify({"error": "Unauthorized"}), 401

    # Import and register route modules
    from stock_checker.alpha.routes import dashboard, comparison, financials
    from stock_checker.alpha.routes import trends, modelling, portfolio, export, scores, industry
    from stock_checker.alpha.routes import news, company, recommendations

    alpha_bp.register_blueprint(dashboard.bp)
    alpha_bp.register_blueprint(comparison.bp)
    alpha_bp.register_blueprint(financials.bp)
    alpha_bp.register_blueprint(trends.bp)
    alpha_bp.register_blueprint(modelling.bp)
    alpha_bp.register_blueprint(portfolio.bp)
    alpha_bp.register_blueprint(export.bp)
    alpha_bp.register_blueprint(scores.bp)
    alpha_bp.register_blueprint(industry.bp)
    alpha_bp.register_blueprint(news.bp)
    alpha_bp.register_blueprint(company.bp)
    alpha_bp.register_blueprint(recommendations.bp)

    # Error handlers for the blueprint
    @alpha_bp.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @alpha_bp.errorhandler(500)
    def internal_error(e):
        return jsonify({"error": "Internal server error"}), 500

    return alpha_bp


def init_alpha(app):
    """Initialize Alpha module with the Flask app."""
    # Configure SQLAlchemy
    if "SQLALCHEMY_DATABASE_URI" not in app.config:
        import os
        instance_path = os.path.join(app.instance_path, "alpha.db")
        os.makedirs(app.instance_path, exist_ok=True)
        app.config["SQLALCHEMY_DATABASE_URI"] = f"sqlite:///{instance_path}"
        app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    db.init_app(app)

    # Register blueprint
    bp = create_alpha_blueprint()
    app.register_blueprint(bp)

    # Create tables
    with app.app_context():
        db.create_all()

    return app
