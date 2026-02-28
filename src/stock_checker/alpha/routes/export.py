"""Export API routes."""

import re

from flask import Blueprint, request, jsonify, Response
from stock_checker.alpha.services.export import export_csv, export_json, export_pdf

bp = Blueprint("alpha_export", __name__)


def _safe_filename(name, default="export"):
    """Sanitize filename: alphanumeric, dots, hyphens, underscores only."""
    name = re.sub(r'[^\w.\-]', '_', name)
    name = name.strip('._')
    return name or default


@bp.route("/api/export/csv", methods=["POST"])
def csv_export():
    data = request.get_json()
    payload = data.get("data", {})
    filename = _safe_filename(data.get("filename", "export.csv"))

    csv_str, fname = export_csv(payload, filename)
    fname = _safe_filename(fname, "export.csv")
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@bp.route("/api/export/json", methods=["POST"])
def json_export():
    data = request.get_json()
    payload = data.get("data", {})
    filename = _safe_filename(data.get("filename", "export.json"))

    json_str, fname = export_json(payload, filename)
    fname = _safe_filename(fname, "export.json")
    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f'attachment; filename="{fname}"'},
    )


@bp.route("/api/export/pdf", methods=["POST"])
def pdf_export():
    data = request.get_json()
    payload = data.get("data", {})
    title = data.get("title", "Stock Analysis Report")
    filename = _safe_filename(data.get("filename", "report.pdf"))

    try:
        pdf_bytes, fname = export_pdf(payload, title, filename)
        fname = _safe_filename(fname, "report.pdf")
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{fname}"'},
        )
    except Exception:
        return jsonify({"error": "Export failed"}), 500
