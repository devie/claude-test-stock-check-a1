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

    # Major holders (percent breakdown)
    major_holders = []
    try:
        mh = t.major_holders
        if mh is not None and not mh.empty:
            for _, row in mh.iterrows():
                major_holders.append({
                    'value': _safe_str(row.iloc[0]),
                    'label': _safe_str(row.iloc[1]) if len(row) > 1 else '',
                })
    except Exception:
        pass

    # Institutional holders (top 10)
    inst_holders = []
    try:
        ih = t.institutional_holders
        if ih is not None and not ih.empty:
            # Column names vary between yfinance versions
            cols = list(ih.columns)
            for _, row in ih.head(10).iterrows():
                holder_name = _safe_str(row.get('Holder') or row.get('holder') or row.iloc[0])
                shares = None
                pct = None
                for col in cols:
                    cl = col.lower()
                    if 'share' in cl:
                        shares = _safe(row[col])
                    elif 'pct' in cl or '%' in cl or 'out' in cl:
                        pct = _safe(row[col])
                inst_holders.append({
                    'holder': holder_name,
                    'shares': shares,
                    'pct_held': pct,
                })
    except Exception:
        pass

    # Corporate calendar (earnings dates, ex-dividend, etc.)
    calendar_events = []
    try:
        cal = t.calendar
        if cal is not None and isinstance(cal, dict):
            for k, v in cal.items():
                if isinstance(v, list):
                    for item in v:
                        try:
                            date_str = item.strftime('%Y-%m-%d') if hasattr(item, 'strftime') else str(item)
                            calendar_events.append({'event': k, 'date': date_str})
                        except Exception:
                            pass
                else:
                    try:
                        date_str = v.strftime('%Y-%m-%d') if hasattr(v, 'strftime') else str(v)
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
        'subsidiaries_note': 'Informasi anak perusahaan tidak tersedia melalui sumber data yang digunakan saat ini.',
    }
