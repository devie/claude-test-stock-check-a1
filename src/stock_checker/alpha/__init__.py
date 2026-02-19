"""Stock Review Intelligence - Alpha module."""

from flask import Blueprint, jsonify
from stock_checker.alpha.models.database import db


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

    # Import and register route modules
    from stock_checker.alpha.routes import dashboard, comparison, financials
    from stock_checker.alpha.routes import trends, modelling, portfolio, export, scores

    alpha_bp.register_blueprint(dashboard.bp)
    alpha_bp.register_blueprint(comparison.bp)
    alpha_bp.register_blueprint(financials.bp)
    alpha_bp.register_blueprint(trends.bp)
    alpha_bp.register_blueprint(modelling.bp)
    alpha_bp.register_blueprint(portfolio.bp)
    alpha_bp.register_blueprint(export.bp)
    alpha_bp.register_blueprint(scores.bp)

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
