"""Export service: CSV, JSON, PDF generation."""

import csv
import io
import json


def export_csv(data, filename="export.csv"):
    """Convert data dict/list to CSV string.

    Args:
        data: list of dicts (rows) or dict of {ticker: metrics_dict}
        filename: suggested filename

    Returns:
        tuple of (csv_string, filename)
    """
    output = io.StringIO()

    if isinstance(data, list) and data:
        writer = csv.DictWriter(output, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    elif isinstance(data, dict):
        # Comparison format: {ticker: {metric: value}}
        tickers = list(data.keys())
        if not tickers:
            return "", filename

        # Collect all metrics
        all_metrics = set()
        for t_data in data.values():
            if isinstance(t_data, dict) and "metrics" in t_data:
                all_metrics.update(t_data["metrics"].keys())
            elif isinstance(t_data, dict):
                all_metrics.update(t_data.keys())

        all_metrics = sorted(all_metrics)
        writer = csv.writer(output)
        writer.writerow(["Metric"] + tickers)

        for metric in all_metrics:
            row = [metric]
            for t in tickers:
                t_data = data[t]
                if isinstance(t_data, dict) and "metrics" in t_data:
                    row.append(t_data["metrics"].get(metric, "N/A"))
                elif isinstance(t_data, dict):
                    row.append(t_data.get(metric, "N/A"))
                else:
                    row.append("N/A")
            writer.writerow(row)

    return output.getvalue(), filename


def export_json(data, filename="export.json"):
    """Convert data to formatted JSON string."""
    return json.dumps(data, indent=2, default=str), filename


def export_pdf(data, title="Stock Analysis Report", filename="report.pdf"):
    """Generate PDF report.

    Args:
        data: dict with analysis data
        title: report title
        filename: output filename

    Returns:
        tuple of (pdf_bytes, filename)
    """
    from fpdf import FPDF

    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()

    # Title
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, ln=True, align="C")
    pdf.ln(5)

    pdf.set_font("Helvetica", "", 10)

    if isinstance(data, dict):
        _render_dict_to_pdf(pdf, data)
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                _render_dict_to_pdf(pdf, item)
                pdf.ln(5)

    return pdf.output(), filename


def _render_dict_to_pdf(pdf, d, level=0):
    """Recursively render a dict to PDF."""
    indent = "  " * level
    for key, value in d.items():
        if isinstance(value, dict):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"{indent}{key}:", ln=True)
            pdf.set_font("Helvetica", "", 10)
            _render_dict_to_pdf(pdf, value, level + 1)
        elif isinstance(value, list):
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 6, f"{indent}{key}: ({len(value)} items)", ln=True)
            pdf.set_font("Helvetica", "", 10)
            for i, item in enumerate(value[:20]):  # Limit to 20 items
                if isinstance(item, dict):
                    _render_dict_to_pdf(pdf, item, level + 1)
                else:
                    pdf.cell(0, 5, f"{indent}  - {item}", ln=True)
        else:
            val_str = str(value) if value is not None else "N/A"
            if len(val_str) > 100:
                val_str = val_str[:100] + "..."
            pdf.cell(0, 5, f"{indent}{key}: {val_str}", ln=True)
