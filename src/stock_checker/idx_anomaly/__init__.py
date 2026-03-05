"""IDX Anomaly Scanner — detects unusual price/volume/PBV patterns on IDX stocks."""
from __future__ import annotations

from flask import Flask


def init_idx_anomaly(app: Flask) -> None:
    """Register the idx_anomaly blueprint with the Flask app."""
    from .routes.anomaly import bp
    app.register_blueprint(bp)
