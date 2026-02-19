"""Industry-specific configuration, detection, and ratio calculations."""

# ── Detection map ────────────────────────────────────────────────────────────
# List of (industry_key, [sector_keywords], [industry_keywords])
# Checked in order — first match wins. More-specific entries come first.
INDUSTRY_MAP = [
    ('logistik_transportasi', ['industrials'], [
        'transport', 'logistic', 'trucking', 'shipping', 'airline', 'freight',
        'delivery', 'courier', 'railroad', 'marine',
    ]),
    ('perbankan', ['financial services', 'finance'], [
        'bank', 'diversified bank', 'regional bank', 'banks',
    ]),
    ('telekomunikasi', ['communication services', 'telecommunications'], [
        'telecom', 'wireless', 'integrated telecommunication', 'communication',
    ]),
    ('energi_pertambangan', ['energy', 'basic materials'], [
        'oil', 'gas', 'coal', 'mining', 'metals', 'steel', 'gold', 'mineral',
        'chemical', 'fertilizer',
    ]),
    ('consumer_goods', ['consumer defensive', 'consumer cyclical'], [
        'food', 'beverage', 'tobacco', 'retail', 'packaged', 'grocery',
        'supermarket', 'household', 'cosmetic', 'staple',
    ]),
    ('manufaktur', ['industrials'], [
        'industrial', 'machinery', 'auto', 'cement', 'building material',
        'electrical equipment', 'aerospace', 'defense', 'conglomerate',
    ]),
    ('properti_konstruksi', ['real estate'], [
        'real estate', 'reit', 'property', 'residential', 'commercial',
        'construction', 'infrastructure',
    ]),
    ('healthcare', ['healthcare'], [
        'pharmaceutical', 'hospital', 'biotech', 'drug', 'medical',
        'healthcare provider', 'life sciences',
    ]),
]

# ── Static config per industry ───────────────────────────────────────────────
INDUSTRY_CONFIG = {
    'perbankan': {
        'label': 'Perbankan',
        'icon': '🏦',
        'peers_IDX': ['BBCA.JK', 'BBRI.JK', 'BMRI.JK'],
        'peers_US':  ['JPM', 'BAC', 'WFC'],
        'peer_metrics': ['PBV', 'ROE', 'DER'],
        'valuation_metric': 'PBV',
        'valuation_bands': {'cheap': [0, 1.5], 'fair': [1.5, 2.5], 'expensive': [2.5, 5.0]},
        'thesis': {
            'bull': (
                'Suku bunga tinggi memperlebar NIM; kredit konsumen & UMKM tumbuh kencang; '
                'digitalisasi menekan BOPO dan membuka fee-based income baru.'
            ),
            'bear': (
                'Kenaikan NPL saat ekonomi melambat menggerus provisi; persaingan produk '
                'simpanan menekan biaya dana; regulasi modal lebih ketat membatasi ekspansi.'
            ),
            'base': (
                'NIM stabil di kisaran historis; kredit tumbuh 8–12% YoY; efisiensi digital '
                'berlanjut; valuasi PBV wajar 1.5–2.5x untuk bank tier-1.'
            ),
        },
    },
    'telekomunikasi': {
        'label': 'Telekomunikasi',
        'icon': '📡',
        'peers_IDX': ['TLKM.JK', 'ISAT.JK', 'EXCL.JK'],
        'peers_US':  ['T', 'VZ', 'TMUS'],
        'peer_metrics': ['EV/EBITDA', 'EBITDA Margin', 'DER'],
        'valuation_metric': 'EV/EBITDA',
        'valuation_bands': {'cheap': [0, 5], 'fair': [5, 8], 'expensive': [8, 13]},
        'thesis': {
            'bull': (
                'Monetisasi 5G perluas ARPU; konsolidasi industri kurangi perang harga; '
                'data center & B2B cloud jadi engine pertumbuhan baru.'
            ),
            'bear': (
                'CapEx 5G besar menekan FCF; OTT menggerus revenue voice & SMS; '
                'kompetisi harga menekan ARPU mobile.'
            ),
            'base': (
                'Revenue tumbuh moderat 5–8% didorong data; EBITDA margin stabil 40–50%; '
                'dividend yield menarik bagi income investor.'
            ),
        },
    },
    'energi_pertambangan': {
        'label': 'Energi & Pertambangan',
        'icon': '⛏️',
        'peers_IDX': ['ADRO.JK', 'PTBA.JK', 'ITMG.JK'],
        'peers_US':  ['XOM', 'CVX', 'COP'],
        'peer_metrics': ['EV/EBITDA', 'Net Debt/EBITDA', 'FCF Yield'],
        'valuation_metric': 'EV/EBITDA',
        'valuation_bands': {'cheap': [0, 4], 'fair': [4, 7], 'expensive': [7, 12]},
        'thesis': {
            'bull': (
                'Supercycle harga komoditas angkat revenue; transisi energi ciptakan demand '
                'mineral baterai; dividend yield tinggi menarik income investor.'
            ),
            'bear': (
                'Perlambatan Tiongkok tekan harga komoditas; regulasi lingkungan & carbon tax '
                'naikkan biaya; risiko stranded asset di batubara thermal.'
            ),
            'base': (
                'Harga komoditas di kisaran mid-cycle; CapEx efisiensi jaga FCF; '
                'eksplorasi terbatas pertahankan supply-demand balance.'
            ),
        },
    },
    'consumer_goods': {
        'label': 'Consumer Goods / Retail',
        'icon': '🛒',
        'peers_IDX': ['UNVR.JK', 'ICBP.JK', 'MYOR.JK'],
        'peers_US':  ['PG', 'KO', 'WMT'],
        'peer_metrics': ['PER', 'EBITDA Margin', 'ROE'],
        'valuation_metric': 'PER',
        'valuation_bands': {'cheap': [0, 15], 'fair': [15, 25], 'expensive': [25, 40]},
        'thesis': {
            'bull': (
                'Pertumbuhan kelas menengah dorong premiumisasi; penetrasi e-commerce '
                'perluas jangkauan; pricing power jaga margin di tengah inflasi.'
            ),
            'bear': (
                'Input cost (komoditas, packaging) menekan gross margin; '
                'private label gerus market share; daya beli konsumen melemah.'
            ),
            'base': (
                'Volume tumbuh 4–7% via distribusi & inovasi produk; margin stabil; '
                'valuasi premium justified oleh brand moat.'
            ),
        },
    },
    'manufaktur': {
        'label': 'Manufaktur',
        'icon': '🏭',
        'peers_IDX': ['ASII.JK', 'SMGR.JK', 'INTP.JK'],
        'peers_US':  ['CAT', 'GE', 'MMM'],
        'peer_metrics': ['PER', 'EV/EBITDA', 'Asset Turnover'],
        'valuation_metric': 'EV/EBITDA',
        'valuation_bands': {'cheap': [0, 6], 'fair': [6, 10], 'expensive': [10, 15]},
        'thesis': {
            'bull': (
                'Ekspansi infrastruktur tingkatkan demand semen/baja; substitusi impor '
                'dorong utilisasi kapasitas; diversifikasi produk perluas margin.'
            ),
            'bear': (
                'Harga energi & bahan baku naik tekan gross margin; over-capacity industri '
                'picu perang harga; perlambatan konstruksi properti.'
            ),
            'base': (
                'Utilisasi kapasitas moderat 70–80%; revenue tumbuh sejalan GDP 5–7%; '
                'CapEx maintenance pertahankan efisiensi.'
            ),
        },
    },
    'properti_konstruksi': {
        'label': 'Properti & Konstruksi',
        'icon': '🏗️',
        'peers_IDX': ['BSDE.JK', 'SMRA.JK', 'PWON.JK'],
        'peers_US':  ['PLD', 'AMT', 'SPG'],
        'peer_metrics': ['PBV', 'PER', 'Gross Margin'],
        'valuation_metric': 'PBV',
        'valuation_bands': {'cheap': [0, 0.5], 'fair': [0.5, 1.0], 'expensive': [1.0, 2.0]},
        'thesis': {
            'bull': (
                'Suku bunga turun dorong permintaan KPR; program rumah subsidi serap '
                'inventory; recurring income (mal/hotel) tumbuh stabil.'
            ),
            'bear': (
                'Oversupply komersial tekan harga; suku bunga tinggi berat cicilan; '
                'proyek mangkrak akibat ketidakpastian regulasi lahan.'
            ),
            'base': (
                'Marketing sales tumbuh 5–10%; recurring income jadi buffer; '
                'valuasi diskon terhadap NAV tetap ada di mayoritas emiten.'
            ),
        },
    },
    'logistik_transportasi': {
        'label': 'Logistik & Transportasi',
        'icon': '🚚',
        'peers_IDX': ['SMDR.JK', 'BIRD.JK', 'GIAA.JK'],
        'peers_US':  ['UPS', 'FDX', 'DAL'],
        'peer_metrics': ['EV/EBITDA', 'Net Margin', 'Asset Turnover'],
        'valuation_metric': 'EV/EBITDA',
        'valuation_bands': {'cheap': [0, 5], 'fair': [5, 9], 'expensive': [9, 14]},
        'thesis': {
            'bull': (
                'Boom e-commerce pacu last-mile delivery; digitalisasi cold chain & '
                'warehouse automation tekan biaya; rute baru tingkatkan utilisasi aset.'
            ),
            'bear': (
                'Kenaikan BBM langsung pukul biaya operasional; platform digital logistik '
                'perketat kompetisi; volume kargo bersifat siklikal.'
            ),
            'base': (
                'Volume tumbuh seiring penetrasi e-commerce; margin stabil via efisiensi '
                'rute; CapEx moderat untuk fleet maintenance.'
            ),
        },
    },
    'healthcare': {
        'label': 'Healthcare & Pharmaceuticals',
        'icon': '💊',
        'peers_IDX': ['KLBF.JK', 'SIDO.JK', 'MIKA.JK'],
        'peers_US':  ['JNJ', 'PFE', 'UNH'],
        'peer_metrics': ['PER', 'Gross Margin', 'ROE'],
        'valuation_metric': 'PER',
        'valuation_bands': {'cheap': [0, 15], 'fair': [15, 25], 'expensive': [25, 40]},
        'thesis': {
            'bull': (
                'Aging population tingkatkan demand layanan; penetrasi BPJS/JKN perluas '
                'pasien rumah sakit; pipeline obat baru mendorong pertumbuhan.'
            ),
            'bear': (
                'Regulasi tarif BPJS menekan margin; paten obat expired buka persaingan '
                'generik; biaya R&D tinggi tanpa jaminan approval.'
            ),
            'base': (
                'Revenue tumbuh 8–12% seiring awareness kesehatan; margin stabil karena '
                'pricing power produk branded; ekspansi organik rs/klinik terkendali.'
            ),
        },
    },
}

_UNKNOWN_CONFIG = {
    'label': 'General',
    'icon': '📊',
    'peers_IDX': [],
    'peers_US': [],
    'peer_metrics': ['PER', 'PBV', 'ROE'],
    'valuation_metric': 'PER',
    'valuation_bands': {'cheap': [0, 10], 'fair': [10, 20], 'expensive': [20, 35]},
    'thesis': {
        'bull': (
            'Pertumbuhan revenue di atas ekspektasi; ekspansi margin dari efisiensi '
            'operasional; katalis spesifik mendorong re-rating valuasi.'
        ),
        'bear': (
            'Tekanan kompetitif menekan margin; pertumbuhan melambat di bawah konsensus; '
            'risiko makro menurunkan appetite investor.'
        ),
        'base': (
            'Pertumbuhan moderat sejalan industri; margin stabil; '
            'valuasi wajar berdasarkan rata-rata historis.'
        ),
    },
}


def detect_industry(sector: str, industry_name: str) -> str:
    """Return industry_key by matching sector/industry strings.

    Two-pass strategy:
      1. Check the specific industry_name against each entry's i_kws first —
         this avoids broad sector labels (like 'industrials') grabbing
         unrelated sub-industries.
      2. Fall back to sector-keyword matching for cases where yfinance only
         returns a broad sector string.
    """
    s = (sector or '').lower()
    i = (industry_name or '').lower()

    # Pass 1: specific industry-name match (higher confidence)
    for key, _s_kws, i_kws in INDUSTRY_MAP:
        if any(kw in i for kw in i_kws):
            return key

    # Pass 2: broad sector match (fallback)
    for key, s_kws, _i_kws in INDUSTRY_MAP:
        if any(kw in s for kw in s_kws):
            return key

    return 'unknown'


def get_industry_config(industry_key: str) -> dict:
    return INDUSTRY_CONFIG.get(industry_key, _UNKNOWN_CONFIG)


def _s(v):
    """Safe float conversion; returns None on failure."""
    try:
        return float(v) if v is not None else None
    except Exception:
        return None


def calc_specific_ratios(industry_key: str, ratios: dict, highlights: dict,
                         price_summary: dict, info: dict) -> dict:
    """Compute industry-relevant ratios from aggregated data."""
    # Standard ratios already computed by calc_all_ratios
    per       = _s(ratios.get('PER'))
    pbv       = _s(ratios.get('PBV'))
    roe       = _s(ratios.get('ROE'))
    roa       = _s(ratios.get('ROA'))
    npm       = _s(ratios.get('NPM'))
    gpm       = _s(ratios.get('GPM'))
    der       = _s(ratios.get('DER'))
    ev_ebitda = _s(ratios.get('EV/EBITDA'))

    # Raw financial figures from highlights (absolute values in local currency)
    revenue = _s(highlights.get('Total Revenue'))
    ebitda  = _s(highlights.get('EBITDA'))
    fcf     = _s(highlights.get('Free Cash Flow'))
    capex   = _s(highlights.get('Capital Expenditure'))  # usually negative

    # Market cap from price summary
    mkt_cap = _s(price_summary.get('market_cap'))

    # Extra fields from raw info dict
    total_debt   = _s(info.get('totalDebt')) or 0
    cash         = _s(info.get('cash') or info.get('cashAndCashEquivalents') or 0) or 0
    total_assets = _s(info.get('totalAssets'))
    nim_raw      = _s(info.get('netInterestMargin'))
    rev_growth_r = _s(info.get('revenueGrowth'))

    # Derived metrics
    ebitda_margin  = round(ebitda / revenue * 100, 2)   if (ebitda  and revenue)              else None
    fcf_yield      = round(fcf    / mkt_cap * 100, 2)   if (fcf     and mkt_cap)               else None
    capex_rev      = round(abs(capex) / revenue * 100, 2) if (capex and revenue)               else None
    net_debt       = total_debt - cash
    nd_ebitda      = round(net_debt / ebitda, 2)         if (ebitda  and ebitda != 0)           else None
    asset_turnover = round(revenue  / total_assets, 2)   if (revenue and total_assets)          else None
    nim            = round(nim_raw  * 100, 2)             if nim_raw  is not None                else None
    rev_growth     = round(rev_growth_r * 100, 2)         if rev_growth_r is not None            else None

    by_industry = {
        'perbankan': {
            'NIM (%)':        nim,
            'PBV (x)':        pbv,
            'ROE (%)':        roe,
            'ROA (%)':        roa,
            'DER (x)':        der,
            'Net Margin (%)': npm,
        },
        'telekomunikasi': {
            'EV/EBITDA (x)':       ev_ebitda,
            'EBITDA Margin (%)':   ebitda_margin,
            'Net Debt/EBITDA (x)': nd_ebitda,
            'CapEx/Revenue (%)':   capex_rev,
            'Revenue Growth (%)':  rev_growth,
        },
        'energi_pertambangan': {
            'EV/EBITDA (x)':       ev_ebitda,
            'EBITDA Margin (%)':   ebitda_margin,
            'Net Debt/EBITDA (x)': nd_ebitda,
            'FCF Yield (%)':       fcf_yield,
            'CapEx/Revenue (%)':   capex_rev,
        },
        'consumer_goods': {
            'PER (x)':           per,
            'Gross Margin (%)':  gpm,
            'EBITDA Margin (%)': ebitda_margin,
            'Asset Turnover (x)':asset_turnover,
            'ROE (%)':           roe,
        },
        'manufaktur': {
            'EV/EBITDA (x)':      ev_ebitda,
            'Gross Margin (%)':   gpm,
            'Asset Turnover (x)': asset_turnover,
            'CapEx/Revenue (%)':  capex_rev,
            'ROE (%)':            roe,
        },
        'properti_konstruksi': {
            'PBV (x)':             pbv,
            'Gross Margin (%)':    gpm,
            'Net Debt/EBITDA (x)': nd_ebitda,
            'Revenue Growth (%)':  rev_growth,
            'ROE (%)':             roe,
        },
        'logistik_transportasi': {
            'EV/EBITDA (x)':       ev_ebitda,
            'Net Margin (%)':      npm,
            'Asset Turnover (x)':  asset_turnover,
            'CapEx/Revenue (%)':   capex_rev,
            'Net Debt/EBITDA (x)': nd_ebitda,
        },
        'healthcare': {
            'PER (x)':           per,
            'Gross Margin (%)':  gpm,
            'EBITDA Margin (%)': ebitda_margin,
            'ROE (%)':           roe,
            'Net Margin (%)':    npm,
        },
    }

    default = {
        'PER (x)':            per,
        'PBV (x)':            pbv,
        'ROE (%)':            roe,
        'Net Margin (%)':     npm,
        'Revenue Growth (%)': rev_growth,
    }

    return by_industry.get(industry_key, default)


def detect_valuation_zone(specific_ratios: dict, config: dict) -> dict:
    """Determine where the current valuation sits within the industry bands."""
    metric = config.get('valuation_metric', 'PER')
    bands  = config.get('valuation_bands', {})

    # Find value: key starts with the metric name
    current = None
    for k, v in specific_ratios.items():
        if k.startswith(metric):
            current = v
            break

    zone = 'unknown'
    if current is not None and current > 0 and bands:
        cheap_max = bands.get('cheap', [0, 0])[1]
        fair_max  = bands.get('fair',  [0, 0])[1]
        if current <= cheap_max:
            zone = 'cheap'
        elif current <= fair_max:
            zone = 'fair'
        else:
            zone = 'expensive'

    return {
        'metric':  metric,
        'current': current,
        'bands':   bands,
        'zone':    zone,
    }
