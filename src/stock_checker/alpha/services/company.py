"""Company information service using yfinance."""

import math
from datetime import datetime
import yfinance as yf


def _safe(val):
    if val is None:
        return None
    try:
        f = float(val)
        if math.isnan(f) or math.isinf(f):
            return None
        return f
    except (TypeError, ValueError):
        return None


def _safe_str(val):
    if val is None:
        return None
    return str(val)


def get_company_info(symbol):
    """Fetch company information for a ticker.

    Returns dict with:
      overview, officers, major_holders, institutional_holders, calendar
    """
    t = yf.Ticker(symbol)
    info = t.info or {}

    # Company overview
    overview = {
        'name': info.get('longName') or info.get('shortName', symbol),
        'description': info.get('longBusinessSummary') or 'Informasi tidak tersedia.',
        'website': info.get('website') or '',
        'employees': _safe(info.get('fullTimeEmployees')),
        'city': info.get('city') or '',
        'state': info.get('state') or '',
        'country': info.get('country') or '',
        'sector': info.get('sector') or '',
        'industry': info.get('industry') or '',
        'exchange': info.get('exchange') or '',
    }

    # Company officers (directors, commissioners, key executives)
    officers_raw = info.get('companyOfficers') or []
    officers = []
    for o in officers_raw:
        officers.append({
            'name': o.get('name', ''),
            'title': o.get('title', ''),
            'age': o.get('age'),
            'total_pay': _safe(o.get('totalPay')),
        })

    # Major holders — map raw yfinance values to labelled rows
    # Newer yfinance returns a DataFrame with numeric index and columns [0, 1] or ['Value','']
    # where col-0 is the numeric value and col-1 is the description label.
    # Known label strings (may be empty in some versions → use positional fallback labels).
    _MAJOR_FALLBACK_LABELS = [
        'Insider Ownership (%)',
        'Institutions % of Float',
        'Institutional Ownership (%)',
        '# Institutions Holding',
    ]
    major_holders = []
    try:
        mh = t.major_holders
        if mh is not None and not mh.empty:
            for idx, (_, row) in enumerate(mh.iterrows()):
                raw_val = row.iloc[0]
                raw_lbl = _safe_str(row.iloc[1]) if len(row) > 1 else ''
                lbl = (raw_lbl.strip() or _MAJOR_FALLBACK_LABELS[idx]) if idx < len(_MAJOR_FALLBACK_LABELS) else (raw_lbl or str(idx))
                # Format value: float like 0.597 → "59.70%", large int → comma-separated
                try:
                    fval = float(raw_val)
                    # If value looks like a decimal ratio (< 1.5) and label suggests %
                    if fval < 1.5 and '%' in lbl.upper():
                        val_str = f"{fval * 100:.2f}%"
                    elif fval >= 1.5 and fval < 100 and '%' in lbl.upper():
                        val_str = f"{fval:.2f}%"
                    else:
                        val_str = f"{int(fval):,}" if fval == int(fval) else f"{fval:,.2f}"
                except (TypeError, ValueError):
                    val_str = _safe_str(raw_val) or '—'
                major_holders.append({'label': lbl, 'value': val_str})
    except Exception:
        pass

    # Institutional holders — keep only valid, positive-pct rows; collect up to 20 for front-end filtering
    # Explicit column preference: pctHeld > % Out > pctHeld-like; never pick pctChange.
    inst_holders = []
    try:
        ih = t.institutional_holders
        if ih is not None and not ih.empty:
            cols = list(ih.columns)
            cols_lower = [c.lower() for c in cols]
            # Determine which column is the ownership %; prefer exact matches
            pct_col = None
            for candidate in ('pctheld', '% out', 'pct_held', 'percentheld'):
                for i, cl in enumerate(cols_lower):
                    if cl == candidate:
                        pct_col = cols[i]
                        break
                if pct_col:
                    break
            # Fallback: any column with 'pct' that is NOT 'pctchange' or 'pct_change'
            if pct_col is None:
                for i, cl in enumerate(cols_lower):
                    if 'pct' in cl and 'change' not in cl:
                        pct_col = cols[i]
                        break

            shares_col = next((cols[i] for i, cl in enumerate(cols_lower) if 'share' in cl and 'pct' not in cl), None)
            holder_col = next((cols[i] for i, cl in enumerate(cols_lower) if 'holder' in cl), cols[0])

            for _, row in ih.iterrows():
                holder_name = _safe_str(row[holder_col]) if holder_col else None
                shares = _safe(row[shares_col]) if shares_col else None
                pct = _safe(row[pct_col]) if pct_col else None
                if holder_name and pct is not None and pct > 0:
                    inst_holders.append({
                        'holder': holder_name,
                        'shares': shares,
                        'pct_held': pct,
                    })
    except Exception:
        pass

    # Corporate calendar — only include entries whose date field matches YYYY-MM-DD
    import re as _re
    _DATE_RE = _re.compile(r'^\d{4}-\d{2}-\d{2}$')
    calendar_events = []
    try:
        cal = t.calendar
        if cal is not None and isinstance(cal, dict):
            for k, v in cal.items():
                if isinstance(v, list):
                    for item in v:
                        try:
                            date_str = item.strftime('%Y-%m-%d') if hasattr(item, 'strftime') else str(item)
                            if _DATE_RE.match(date_str):
                                calendar_events.append({'event': k, 'date': date_str})
                        except Exception:
                            pass
                else:
                    try:
                        date_str = v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)
                        if _DATE_RE.match(date_str):
                            calendar_events.append({'event': k, 'date': date_str})
                    except Exception:
                        pass
    except Exception:
        pass

    # Recent dividends / actions (last 3 months)
    recent_dividends = []
    try:
        actions = t.actions
        if actions is not None and not actions.empty and 'Dividends' in actions.columns:
            divs = actions['Dividends'][actions['Dividends'] > 0]
            for date, amount in divs.tail(5).items():
                recent_dividends.append({
                    'date': date.strftime('%Y-%m-%d') if hasattr(date, 'strftime') else str(date),
                    'amount': _safe(amount),
                })
    except Exception:
        pass

    # Sort calendar by date
    calendar_events.sort(key=lambda e: e.get('date', ''))

    return {
        'ticker': symbol,
        'overview': overview,
        'officers': officers,
        'major_holders': major_holders,
        'institutional_holders': inst_holders,
        'calendar': calendar_events,
        'recent_dividends': recent_dividends,
        'subsidiaries_note': 'Subsidiary information (direct and indirect holdings with ownership percentages) is not available through the current data source (yfinance). For complete subsidiary data, refer to the company\'s annual report or IDX disclosure filings.',
    }
