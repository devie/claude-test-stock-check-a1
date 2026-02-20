"""Industry-specific configuration, detection, and ratio calculations."""

# ── Detection map ────────────────────────────────────────────────────────────
# List of (industry_key, [sector_keywords], [industry_keywords])
# Checked in order — first match wins. More-specific entries come first.
INDUSTRY_MAP = [
    # Most-specific entries first — prevents broad keywords from grabbing sub-industries
    ('teknologi', ['technology'], [
        'software', 'internet', 'fintech', 'e-commerce', 'saas',
        'semiconductor', 'tech', 'data', 'cloud', 'digital', 'information technology',
    ]),
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
            'bull': {
                'en': (
                    'High interest rates widen NIM; consumer & SME loans grow strongly; '
                    'digitalization lowers cost-to-income and opens new fee-based revenue.'
                ),
                'id': (
                    'Suku bunga tinggi memperlebar NIM; kredit konsumen & UMKM tumbuh kencang; '
                    'digitalisasi menekan BOPO dan membuka fee-based income baru.'
                ),
            },
            'bear': {
                'en': (
                    'Rising NPLs during economic slowdown erode provisions; deposit competition '
                    'pressures funding costs; stricter capital regulations limit expansion.'
                ),
                'id': (
                    'Kenaikan NPL saat ekonomi melambat menggerus provisi; persaingan produk '
                    'simpanan menekan biaya dana; regulasi modal lebih ketat membatasi ekspansi.'
                ),
            },
            'base': {
                'en': (
                    'NIM stable within historical range; credit grows 8–12% YoY; digital '
                    'efficiency continues; fair PBV valuation 1.5–2.5x for tier-1 banks.'
                ),
                'id': (
                    'NIM stabil di kisaran historis; kredit tumbuh 8–12% YoY; efisiensi digital '
                    'berlanjut; valuasi PBV wajar 1.5–2.5x untuk bank tier-1.'
                ),
            },
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
            'bull': {
                'en': (
                    '5G monetization expands ARPU; industry consolidation reduces price wars; '
                    'data center & B2B cloud become new growth engines.'
                ),
                'id': (
                    'Monetisasi 5G perluas ARPU; konsolidasi industri kurangi perang harga; '
                    'data center & B2B cloud jadi engine pertumbuhan baru.'
                ),
            },
            'bear': {
                'en': (
                    'Heavy 5G CapEx pressures FCF; OTT erodes voice & SMS revenue; '
                    'price competition compresses mobile ARPU.'
                ),
                'id': (
                    'CapEx 5G besar menekan FCF; OTT menggerus revenue voice & SMS; '
                    'kompetisi harga menekan ARPU mobile.'
                ),
            },
            'base': {
                'en': (
                    'Revenue grows moderately 5–8% driven by data; EBITDA margin stable at '
                    '40–50%; dividend yield attractive for income investors.'
                ),
                'id': (
                    'Revenue tumbuh moderat 5–8% didorong data; EBITDA margin stabil 40–50%; '
                    'dividend yield menarik bagi income investor.'
                ),
            },
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
            'bull': {
                'en': (
                    'Commodity price supercycle lifts revenue; energy transition creates battery '
                    'mineral demand; high dividend yield attracts income investors.'
                ),
                'id': (
                    'Supercycle harga komoditas angkat revenue; transisi energi ciptakan demand '
                    'mineral baterai; dividend yield tinggi menarik income investor.'
                ),
            },
            'bear': {
                'en': (
                    'China slowdown pressures commodity prices; environmental regulations & '
                    'carbon tax raise costs; stranded asset risk in thermal coal.'
                ),
                'id': (
                    'Perlambatan Tiongkok tekan harga komoditas; regulasi lingkungan & carbon tax '
                    'naikkan biaya; risiko stranded asset di batubara thermal.'
                ),
            },
            'base': {
                'en': (
                    'Commodity prices at mid-cycle range; capital efficiency preserves FCF; '
                    'limited exploration maintains supply-demand balance.'
                ),
                'id': (
                    'Harga komoditas di kisaran mid-cycle; CapEx efisiensi jaga FCF; '
                    'eksplorasi terbatas pertahankan supply-demand balance.'
                ),
            },
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
            'bull': {
                'en': (
                    'Middle-class growth drives premiumization; e-commerce penetration expands '
                    'reach; pricing power protects margins amid inflation.'
                ),
                'id': (
                    'Pertumbuhan kelas menengah dorong premiumisasi; penetrasi e-commerce '
                    'perluas jangkauan; pricing power jaga margin di tengah inflasi.'
                ),
            },
            'bear': {
                'en': (
                    'Input costs (commodities, packaging) pressure gross margin; private labels '
                    'erode market share; consumer purchasing power weakens.'
                ),
                'id': (
                    'Input cost (komoditas, packaging) menekan gross margin; '
                    'private label gerus market share; daya beli konsumen melemah.'
                ),
            },
            'base': {
                'en': (
                    'Volume grows 4–7% via distribution & product innovation; margins stable; '
                    'premium valuation justified by brand moat.'
                ),
                'id': (
                    'Volume tumbuh 4–7% via distribusi & inovasi produk; margin stabil; '
                    'valuasi premium justified oleh brand moat.'
                ),
            },
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
            'bull': {
                'en': (
                    'Infrastructure expansion raises demand for cement/steel; import substitution '
                    'drives capacity utilization; product diversification expands margins.'
                ),
                'id': (
                    'Ekspansi infrastruktur tingkatkan demand semen/baja; substitusi impor '
                    'dorong utilisasi kapasitas; diversifikasi produk perluas margin.'
                ),
            },
            'bear': {
                'en': (
                    'Rising energy & raw material prices compress gross margin; industry '
                    'over-capacity triggers price wars; property construction slowdown.'
                ),
                'id': (
                    'Harga energi & bahan baku naik tekan gross margin; over-capacity industri '
                    'picu perang harga; perlambatan konstruksi properti.'
                ),
            },
            'base': {
                'en': (
                    'Moderate capacity utilization at 70–80%; revenue grows in line with GDP '
                    'at 5–7%; maintenance CapEx preserves efficiency.'
                ),
                'id': (
                    'Utilisasi kapasitas moderat 70–80%; revenue tumbuh sejalan GDP 5–7%; '
                    'CapEx maintenance pertahankan efisiensi.'
                ),
            },
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
            'bull': {
                'en': (
                    'Rate cuts boost mortgage demand; subsidized housing program absorbs '
                    'inventory; recurring income (mall/hotel) grows steadily.'
                ),
                'id': (
                    'Suku bunga turun dorong permintaan KPR; program rumah subsidi serap '
                    'inventory; recurring income (mal/hotel) tumbuh stabil.'
                ),
            },
            'bear': {
                'en': (
                    'Commercial oversupply pressures prices; high rates burden installments; '
                    'stalled projects due to land regulation uncertainty.'
                ),
                'id': (
                    'Oversupply komersial tekan harga; suku bunga tinggi berat cicilan; '
                    'proyek mangkrak akibat ketidakpastian regulasi lahan.'
                ),
            },
            'base': {
                'en': (
                    'Marketing sales grow 5–10%; recurring income provides buffer; '
                    'NAV discount valuation persists at most issuers.'
                ),
                'id': (
                    'Marketing sales tumbuh 5–10%; recurring income jadi buffer; '
                    'valuasi diskon terhadap NAV tetap ada di mayoritas emiten.'
                ),
            },
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
            'bull': {
                'en': (
                    'E-commerce boom accelerates last-mile delivery; cold chain digitalization '
                    '& warehouse automation cut costs; new routes improve asset utilization.'
                ),
                'id': (
                    'Boom e-commerce pacu last-mile delivery; digitalisasi cold chain & '
                    'warehouse automation tekan biaya; rute baru tingkatkan utilisasi aset.'
                ),
            },
            'bear': {
                'en': (
                    'Fuel price hikes directly hit operating costs; digital logistics platforms '
                    'intensify competition; cargo volumes are cyclical.'
                ),
                'id': (
                    'Kenaikan BBM langsung pukul biaya operasional; platform digital logistik '
                    'perketat kompetisi; volume kargo bersifat siklikal.'
                ),
            },
            'base': {
                'en': (
                    'Volume grows with e-commerce penetration; margins stable via route '
                    'efficiency; moderate CapEx for fleet maintenance.'
                ),
                'id': (
                    'Volume tumbuh seiring penetrasi e-commerce; margin stabil via efisiensi '
                    'rute; CapEx moderat untuk fleet maintenance.'
                ),
            },
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
            'bull': {
                'en': (
                    'Aging population raises service demand; BPJS/JKN penetration expands '
                    'hospital patient base; new drug pipeline drives growth.'
                ),
                'id': (
                    'Aging population tingkatkan demand layanan; penetrasi BPJS/JKN perluas '
                    'pasien rumah sakit; pipeline obat baru mendorong pertumbuhan.'
                ),
            },
            'bear': {
                'en': (
                    'BPJS tariff regulation pressures margins; expired drug patents open '
                    'generic competition; high R&D costs without guaranteed approval.'
                ),
                'id': (
                    'Regulasi tarif BPJS menekan margin; paten obat expired buka persaingan '
                    'generik; biaya R&D tinggi tanpa jaminan approval.'
                ),
            },
            'base': {
                'en': (
                    'Revenue grows 8–12% with health awareness; margins stable due to branded '
                    'product pricing power; organic hospital/clinic expansion manageable.'
                ),
                'id': (
                    'Revenue tumbuh 8–12% seiring awareness kesehatan; margin stabil karena '
                    'pricing power produk branded; ekspansi organik rs/klinik terkendali.'
                ),
            },
        },
    },
    'teknologi': {
        'label': 'Technology',
        'icon': '💻',
        'peers_IDX': ['BUKA.JK', 'GOTO.JK', 'EMTK.JK'],
        'peers_US':  ['AAPL', 'MSFT', 'GOOGL'],
        'peer_metrics': ['P/S', 'Gross Margin', 'Revenue Growth'],
        'valuation_metric': 'PER',
        'valuation_bands': {'cheap': [0, 20], 'fair': [20, 40], 'expensive': [40, 80]},
        'thesis': {
            'bull': {
                'en': (
                    'AI and cloud adoption accelerate revenue growth; high gross margins '
                    'expand as scale increases; platform network effects create durable moats.'
                ),
                'id': (
                    'Adopsi AI dan cloud pacu pertumbuhan revenue; gross margin tinggi '
                    'melebar seiring skala; efek jaringan platform ciptakan moat yang tahan lama.'
                ),
            },
            'bear': {
                'en': (
                    'Regulatory pressure on big tech increases compliance costs; macro slowdown '
                    'reduces enterprise IT spend; competition compresses SaaS pricing.'
                ),
                'id': (
                    'Tekanan regulasi pada big tech naikkan biaya kepatuhan; perlambatan makro '
                    'kurangi belanja IT enterprise; kompetisi menekan harga SaaS.'
                ),
            },
            'base': {
                'en': (
                    'Revenue grows 15–25% driven by cloud and digital services; '
                    'gross margin stable above 60%; R&D investment sustains competitive position.'
                ),
                'id': (
                    'Revenue tumbuh 15–25% didorong cloud & layanan digital; '
                    'gross margin stabil di atas 60%; investasi R&D pertahankan posisi kompetitif.'
                ),
            },
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
        'bull': {
            'en': (
                'Revenue growth above expectations; margin expansion from operational '
                'efficiency; specific catalysts drive valuation re-rating.'
            ),
            'id': (
                'Pertumbuhan revenue di atas ekspektasi; ekspansi margin dari efisiensi '
                'operasional; katalis spesifik mendorong re-rating valuasi.'
            ),
        },
        'bear': {
            'en': (
                'Competitive pressure compresses margins; growth slows below consensus; '
                'macro risks reduce investor appetite.'
            ),
            'id': (
                'Tekanan kompetitif menekan margin; pertumbuhan melambat di bawah konsensus; '
                'risiko makro menurunkan appetite investor.'
            ),
        },
        'base': {
            'en': (
                'Moderate growth in line with industry; margins stable; '
                'fair valuation based on historical averages.'
            ),
            'id': (
                'Pertumbuhan moderat sejalan industri; margin stabil; '
                'valuasi wajar berdasarkan rata-rata historis.'
            ),
        },
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
            'Gross Margin (%)':    gpm,
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
        'teknologi': {
            'PER (x)':            per,
            'Gross Margin (%)':   gpm,
            'EBITDA Margin (%)':  ebitda_margin,
            'Revenue Growth (%)': rev_growth,
            'FCF Yield (%)':      fcf_yield,
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
