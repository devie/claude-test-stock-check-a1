"""AI-powered watchlist analysis using Claude."""

import os
import json
import re

from stock_checker.alpha.services.data_fetcher import get_info
from stock_checker.alpha.calculations.industry import detect_industry, get_industry_config

MODEL = "claude-sonnet-4-6"

SYSTEM_PROMPT = """\
Kamu adalah investment analysis engine yang menghasilkan scoring saham yang konsisten, \
sector-aware, dan balanced. Tugasmu adalah mengevaluasi watchlist menggunakan tiga pilar: \
Quality, Valuation, dan Risk — lalu menghasilkan rekomendasi yang decision-ready.

Kamu harus output HANYA valid JSON array, tanpa markdown, tanpa penjelasan di luar JSON."""

_USER_TEMPLATE = """\
===========================
SCORING FRAMEWORK
===========================
Bobot final score:
- Quality   = 35%
- Valuation = 35%
- Risk      = 25%  (Risk score TINGGI = LEBIH AMAN)

Recommendation thresholds (gunakan PERSIS ini):
  Strong Buy : composite >= 75 DAN valuation >= 60
  Buy        : composite >= 60 DAN valuation >= 45
  Hold       : composite >= 45
  Avoid      : composite < 45

===========================
SECTOR NORMALIZATION
===========================
Normalisasi metrik per sektor agar perbandingan fair:
- Perbankan    : ROE 15-20% = kuat; PBV < 2.0 = menarik; DER tinggi = NORMAL (jangan dihukum)
- Telekomunikasi: ROE 8-12% = kuat; EV/EBITDA < 6 = menarik; CapEx besar = NORMAL
- Energi/Tambang: laba siklikal, gunakan EV/EBITDA bukan PER; FCF yield penting
- Consumer Goods: margin stabil, growth 4-8%, PER 15-25x = wajar
- Teknologi     : ROE 20-40% = normal; valuation tinggi lumrah untuk growth company
- Properti      : PBV < 1x = cheap; DER tinggi = NORMAL untuk sektor ini
Jangan hukum sektor atas karakteristik strukturalnya.

===========================
CONSISTENCY CHECK (WAJIB)
===========================
Sebelum output:
1. Jika Risk > 85 untuk lebih dari 50% ticker: compress semua Risk dengan
   new_risk = 50 + (risk - 50) * 0.7  (pertahankan urutan relatif)
2. Jika Quality < 40 untuk blue-chip (BBCA, TLKM, ASII, dsb): recalibrate naik
3. Pastikan distribusi rekomendasi masuk akal — tidak semua Hold, tidak semua Buy

===========================
WATCHLIST INPUT
===========================
Format: Ticker | Sektor | Quality | Valuation | Risk | Composite | Rec Saat Ini

{table}

===========================
INSTRUKSI OUTPUT
===========================
Return HANYA JSON array berikut, tanpa teks lain:

[
  {{
    "ticker": "BBCA.JK",
    "quality": 65.0,
    "valuation": 42.0,
    "risk": 78.0,
    "composite": 62.1,
    "recommendation": "Hold",
    "narrative": "Narasi 2-3 kalimat dalam Bahasa Indonesia. Jelaskan driver utama, \
konteks sektor, dan trade-off valuasi vs kualitas."
  }}
]

Pastikan:
- composite = quality*0.35 + valuation*0.35 + risk*0.25 (hitung ulang, jangan pakai input)
- recommendation mengikuti threshold yang ditetapkan di atas (PERSIS)
- narrative: Bahasa Indonesia, 2-3 kalimat, decision-ready, mention sektor
- Semua angka float dengan 1 desimal
"""


def _build_table(scores_with_sector: list[dict]) -> str:
    """Format scores list into a readable table for the prompt."""
    lines = ["Ticker | Sektor | Quality | Valuation | Risk | Composite | Rec Saat Ini",
             "-------|--------|---------|-----------|------|-----------|-------------"]
    for s in scores_with_sector:
        lines.append(
            f"{s['ticker']} | {s['sector_label']} | "
            f"{s.get('quality_score') or 'N/A'} | "
            f"{s.get('valuation_score') or 'N/A'} | "
            f"{s.get('risk_score') or 'N/A'} | "
            f"{s.get('composite_score') or 'N/A'} | "
            f"{s.get('recommendation') or 'N/A'}"
        )
    return "\n".join(lines)


def _enrich_with_sector(scores: list[dict]) -> list[dict]:
    """Add sector_label to each score dict using cached info."""
    enriched = []
    for sc in scores:
        ticker = sc.get("ticker", "")
        label = "General"
        try:
            info = get_info(ticker)
            key = detect_industry(info.get("sector", ""), info.get("industry", ""))
            cfg = get_industry_config(key)
            label = cfg.get("label", "General")
        except Exception:
            pass
        enriched.append({**sc, "sector_label": label})
    return enriched


def _parse_response(text: str) -> list[dict]:
    """Extract JSON array from Claude response, tolerating markdown fences."""
    # Strip markdown code fences if present
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    return json.loads(text)


def analyze_watchlist(scores: list[dict]) -> list[dict]:
    """Run AI analysis on a batch scores list.

    Args:
        scores: list of dicts from /api/scores/batch

    Returns:
        list of dicts with revised scores + narrative

    Raises:
        EnvironmentError: if ANTHROPIC_API_KEY not set
        RuntimeError: if Claude call or JSON parse fails
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not api_key:
        raise EnvironmentError(
            "ANTHROPIC_API_KEY belum diset. "
            "Tambahkan ke file .env atau environment variable."
        )

    # Filter out error entries, enrich with sector
    valid = [s for s in scores if not s.get("error")]
    if not valid:
        raise ValueError("Tidak ada ticker valid untuk dianalisis.")

    enriched = _enrich_with_sector(valid)
    table = _build_table(enriched)
    user_msg = _USER_TEMPLATE.format(table=table)

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=SYSTEM_PROMPT,
            messages=[{"role": "user", "content": user_msg}],
        )
        raw = message.content[0].text
    except Exception as e:
        raise RuntimeError(f"Claude API call gagal: {e}") from e

    try:
        results = _parse_response(raw)
    except Exception as e:
        raise RuntimeError(f"Gagal parse JSON dari Claude: {e}\nRaw response:\n{raw[:500]}") from e

    return results
