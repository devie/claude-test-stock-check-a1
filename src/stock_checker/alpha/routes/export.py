"""Export API routes."""

from flask import Blueprint, request, jsonify, Response
from stock_checker.alpha.services.export import export_csv, export_json, export_pdf

bp = Blueprint("alpha_export", __name__)


@bp.route("/api/export/csv", methods=["POST"])
def csv_export():
    data = request.get_json()
    payload = data.get("data", {})
    filename = data.get("filename", "export.csv")

    csv_str, fname = export_csv(payload, filename)
    return Response(
        csv_str,
        mimetype="text/csv",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@bp.route("/api/export/json", methods=["POST"])
def json_export():
    data = request.get_json()
    payload = data.get("data", {})
    filename = data.get("filename", "export.json")

    json_str, fname = export_json(payload, filename)
    return Response(
        json_str,
        mimetype="application/json",
        headers={"Content-Disposition": f"attachment; filename={fname}"},
    )


@bp.route("/api/export/pdf", methods=["POST"])
def pdf_export():
    data = request.get_json()
    payload = data.get("data", {})
    title = data.get("title", "Stock Analysis Report")
    filename = data.get("filename", "report.pdf")

    try:
        pdf_bytes, fname = export_pdf(payload, title, filename)
        return Response(
            pdf_bytes,
            mimetype="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500
