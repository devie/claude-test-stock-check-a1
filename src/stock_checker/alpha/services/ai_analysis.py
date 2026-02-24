"""AI-powered watchlist analysis — supports Groq (free), Ollama (local), Anthropic."""

import os
import json
import re

from stock_checker.alpha.services.data_fetcher import get_info
from stock_checker.alpha.calculations.industry import detect_industry, get_industry_config

# ── Provider config ───────────────────────────────────────────────────────────
# LLM_PROVIDER env var selects backend (default: groq)
_PROVIDER_DEFAULTS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "model":    "llama-3.3-70b-versatile",
        "key_env":  "GROQ_API_KEY",
    },
    "ollama": {
        "base_url": "http://localhost:11434/v1",
        "model":    "llama3.2",
        "key_env":  None,          # Ollama doesn't need a real key
    },
    "anthropic": {
        "base_url": None,          # uses anthropic SDK directly
        "model":    "claude-sonnet-4-6",
        "key_env":  "ANTHROPIC_API_KEY",
    },
    "openai": {
        "base_url": None,
        "model":    "gpt-4o-mini",
        "key_env":  "OPENAI_API_KEY",
    },
}

_SETUP_HINTS = {
    "groq":      "Daftar gratis di console.groq.com, buat API key, set GROQ_API_KEY di .env",
    "ollama":    "Install Ollama di ollama.ai lalu jalankan: ollama pull llama3.2",
    "anthropic": "Daftar di console.anthropic.com, buat API key, set ANTHROPIC_API_KEY di .env",
    "openai":    "Daftar di platform.openai.com, buat API key, set OPENAI_API_KEY di .env",
}

# ── Prompt ────────────────────────────────────────────────────────────────────
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


# ── Helpers ───────────────────────────────────────────────────────────────────
def _build_table(scores_with_sector: list[dict]) -> str:
    lines = [
        "Ticker | Sektor | Quality | Valuation | Risk | Composite | Rec Saat Ini",
        "-------|--------|---------|-----------|------|-----------|-------------",
    ]
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
    enriched = []
    for sc in scores:
        label = "General"
        try:
            info = get_info(sc.get("ticker", ""))
            key = detect_industry(info.get("sector", ""), info.get("industry", ""))
            label = get_industry_config(key).get("label", "General")
        except Exception:
            pass
        enriched.append({**sc, "sector_label": label})
    return enriched


def _parse_response(text: str) -> list[dict]:
    text = re.sub(r"```(?:json)?\s*", "", text).strip()
    text = re.sub(r"```\s*$", "", text).strip()
    return json.loads(text)


# ── Helpers ───────────────────────────────────────────────────────────────────
def _is_rate_limit(exc: Exception) -> bool:
    """Return True if the exception looks like a rate-limit / quota error."""
    msg = str(exc).lower()
    try:
        from openai import RateLimitError
        if isinstance(exc, RateLimitError):
            return True
    except ImportError:
        pass
    return any(k in msg for k in ("rate limit", "rate_limit", "429",
                                  "quota", "too many requests"))


# ── Provider calls ────────────────────────────────────────────────────────────
def _call_openai_compat(base_url: str, api_key: str, model: str,
                        system: str, user: str) -> str:
    """Call any OpenAI-compatible endpoint (Groq, Ollama, OpenAI)."""
    from openai import OpenAI
    client = OpenAI(base_url=base_url, api_key=api_key or "ollama")
    resp = client.chat.completions.create(
        model=model,
        max_tokens=4096,
        messages=[
            {"role": "system", "content": system},
            {"role": "user",   "content": user},
        ],
    )
    return resp.choices[0].message.content


def _call_anthropic(api_key: str, model: str, system: str, user: str) -> str:
    from anthropic import Anthropic
    client = Anthropic(api_key=api_key)
    msg = client.messages.create(
        model=model,
        max_tokens=4096,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    return msg.content[0].text


# ── Public API ────────────────────────────────────────────────────────────────
def get_provider_status() -> dict:
    """Return current provider config and whether it's ready."""
    provider = os.environ.get("LLM_PROVIDER", "groq").lower()
    cfg = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["groq"])
    model = os.environ.get("LLM_MODEL", cfg["model"])
    key_env = cfg["key_env"]

    if provider == "ollama":
        ready = True   # no key needed
        key_set = True
    else:
        key_set = bool(os.environ.get(key_env or "", "").strip())
        ready = key_set

    return {
        "provider": provider,
        "model":    model,
        "ready":    ready,
        "key_set":  key_set,
        "hint":     _SETUP_HINTS.get(provider, ""),
    }


def analyze_watchlist(scores: list[dict]) -> list[dict]:
    """Run AI analysis on a batch scores list.

    Provider is selected via LLM_PROVIDER env var (default: groq).
    API key read from the provider's key_env (e.g. GROQ_API_KEY).

    Raises:
        EnvironmentError: provider not ready (missing key / Ollama not running)
        RuntimeError: API call or JSON parse failed
    """
    status = get_provider_status()
    provider = status["provider"]
    cfg = _PROVIDER_DEFAULTS.get(provider, _PROVIDER_DEFAULTS["groq"])
    model = os.environ.get("LLM_MODEL", cfg["model"])

    if not status["ready"]:
        key_env = cfg.get("key_env", "")
        raise EnvironmentError(
            f"{key_env} belum diset untuk provider '{provider}'. "
            f"{status['hint']}"
        )

    valid = [s for s in scores if not s.get("error")]
    if not valid:
        raise ValueError("Tidak ada ticker valid untuk dianalisis.")

    enriched = _enrich_with_sector(valid)
    user_msg = _USER_TEMPLATE.format(table=_build_table(enriched))

    try:
        if provider == "anthropic":
            api_key = os.environ.get("ANTHROPIC_API_KEY", "")
            raw = _call_anthropic(api_key, model, SYSTEM_PROMPT, user_msg)
        else:
            api_key = os.environ.get(cfg.get("key_env") or "", "ollama")
            try:
                raw = _call_openai_compat(cfg["base_url"], api_key, model,
                                          SYSTEM_PROMPT, user_msg)
            except Exception as primary_err:
                # Auto-fallback to Ollama on rate limit or quota errors
                if provider != "ollama" and _is_rate_limit(primary_err):
                    ollama_cfg = _PROVIDER_DEFAULTS["ollama"]
                    ollama_model = os.environ.get("OLLAMA_MODEL",
                                                  ollama_cfg["model"])
                    try:
                        raw = _call_openai_compat(
                            ollama_cfg["base_url"], "ollama",
                            ollama_model, SYSTEM_PROMPT, user_msg,
                        )
                    except Exception as ollama_err:
                        raise RuntimeError(
                            f"Groq rate-limited dan Ollama juga gagal: "
                            f"{ollama_err}"
                        ) from ollama_err
                else:
                    raise
    except EnvironmentError:
        raise
    except RuntimeError:
        raise
    except Exception as e:
        raise RuntimeError(f"API call ke '{provider}' gagal: {e}") from e

    try:
        return _parse_response(raw)
    except Exception as e:
        raise RuntimeError(
            f"Gagal parse JSON dari '{provider}': {e}\nRaw:\n{raw[:400]}"
        ) from e
