"""Dashboard route - serves the SPA shell."""

from flask import Blueprint, render_template

bp = Blueprint("alpha_dashboard", __name__)


@bp.route("/")
def index():
    """Serve the Alpha SPA shell."""
    return render_template("alpha/index.html")
