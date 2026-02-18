/**
 * Table rendering helpers
 */
const Tables = {
    /**
     * Render a key-value table (e.g. ratios)
     */
    keyValue(data, options = {}) {
        const { title, className = '' } = options;
        let html = '';
        if (title) html += `<div class="card-title">${title}</div>`;
        html += `<table class="data-table ${className}"><tbody>`;
        for (const [key, value] of Object.entries(data)) {
            const display = Tables.formatValue(value);
            html += `<tr><td>${key}</td><td>${display}</td></tr>`;
        }
        html += '</tbody></table>';
        return html;
    },

    // ── Ratio signal thresholds ────────────────────────────────────────────
    // Each entry: { dir: 'higher'|'lower'|'range', green, gold }
    // 'higher' = higher is better; 'lower' = lower is better (but > 0)
    // 'range'  = good is within [green[0], green[1]], gold within [gold[0], gold[1]]
    RATIO_THRESHOLDS: {
        'PER':           { dir: 'lower',  green: 15,   gold: 25  },
        'PBV':           { dir: 'lower',  green: 1.5,  gold: 3   },
        'EV/EBITDA':     { dir: 'lower',  green: 8,    gold: 15  },
        'PEG':           { dir: 'lower',  green: 1,    gold: 2   },
        'ROE':           { dir: 'higher', green: 15,   gold: 8   },
        'ROA':           { dir: 'higher', green: 10,   gold: 5   },
        'NPM':           { dir: 'higher', green: 15,   gold: 5   },
        'GPM':           { dir: 'higher', green: 40,   gold: 20  },
        'Beta':          { dir: 'range',  green: [0, 1], gold: [-0.5, 1.5] },
        'DER':           { dir: 'lower',  green: 0.5,  gold: 1.5 },
        'Current Ratio': { dir: 'higher', green: 2,    gold: 1   },
        'Dividend Yield':{ dir: 'higher', green: 3,    gold: 1   },
    },

    /**
     * Returns 'green' | 'gold' | 'red' | null for a ratio value.
     */
    _ratioSignal(metric, value) {
        if (value == null || !isFinite(value)) return null;
        const cfg = Tables.RATIO_THRESHOLDS[metric];
        if (!cfg) return null;

        if (cfg.dir === 'higher') {
            if (value < 0)          return 'red';
            if (value >= cfg.green) return 'green';
            if (value >= cfg.gold)  return 'gold';
            return 'red';
        }
        if (cfg.dir === 'lower') {
            if (value <= 0)         return 'red';
            if (value <= cfg.green) return 'green';
            if (value <= cfg.gold)  return 'gold';
            return 'red';
        }
        if (cfg.dir === 'range') {
            const [gLo, gHi] = cfg.green;
            const [yLo, yHi] = cfg.gold;
            if (value >= gLo && value <= gHi) return 'green';
            if (value >= yLo && value <= yHi) return 'gold';
            return 'red';
        }
        return null;
    },

    // Signal dot colors
    _SIGNAL_COLORS: { green: '#4CAF50', gold: '#FFC107', red: '#f44336' },
    _SIGNAL_BG:     { green: 'rgba(76,175,80,0.10)', gold: 'rgba(255,193,7,0.12)', red: 'rgba(244,67,54,0.10)' },

    /**
     * Render a ratio key-value table with green/gold/red signal indicators.
     * @param {Object} rawData  - { metricName: numericValue }
     * @param {Object} suffixes - { metricName: '%'|'x'|'' }
     */
    keyValueRatios(rawData, suffixes = {}) {
        let html = `<table class="data-table"><tbody>`;
        for (const [key, value] of Object.entries(rawData)) {
            const signal = Tables._ratioSignal(key, value);
            const color  = signal ? Tables._SIGNAL_COLORS[signal] : null;
            const bg     = signal ? Tables._SIGNAL_BG[signal]     : '';
            const suffix = suffixes[key] || '';
            const dot    = color
                ? `<span style="color:${color};font-size:0.7em;margin-right:5px;vertical-align:middle">●</span>`
                : '';
            let formatted;
            if (value == null || !isFinite(value)) {
                formatted = '<span style="color:var(--text-muted)">N/A</span>';
            } else {
                const colorStyle = color ? `color:${color};font-weight:600` : '';
                formatted = `<span style="${colorStyle}">${Tables.addSeparator(value.toFixed(2))}${suffix}</span>`;
            }
            html += `<tr>
                <td>${key}</td>
                <td style="background:${bg};border-radius:4px;padding:4px 8px">${dot}${formatted}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        return html;
    },

    /**
     * Render a comparison table (tickers as columns)
     */
    comparison(metrics, tickers, data) {
        let html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Metric</th>';
        for (const t of tickers) {
            html += `<th>${t}</th>`;
        }
        html += '</tr></thead><tbody>';

        const largeMetrics = ['Market Cap'];
        const pctMetrics = ['ROE', 'ROA', 'NPM', 'GPM', 'Dividend Yield'];
        const ratioMetrics = ['PER', 'PBV', 'EV/EBITDA', 'PEG', 'DER', 'Current Ratio', 'Beta'];

        for (const metric of metrics) {
            html += `<tr><td>${metric}</td>`;
            for (const t of tickers) {
                const td = data[t];
                const rawVal = td?.metrics?.[metric] ?? null;
                let val = '<span style="color:var(--text-muted)">N/A</span>';

                if (rawVal != null) {
                    const v = rawVal;
                    if (largeMetrics.includes(metric)) {
                        val = Tables.formatValue(v, true);
                    } else if (metric === 'Current Price') {
                        val = Tables.formatPrice(v);
                    } else if (pctMetrics.includes(metric)) {
                        val = Tables.formatRatio(v, '%');
                    } else if (ratioMetrics.includes(metric)) {
                        val = Tables.formatRatio(v, 'x');
                    } else {
                        val = Tables.formatValue(v);
                    }

                    // Apply signal coloring for known ratio metrics
                    const signal = Tables._ratioSignal(metric, v);
                    if (signal) {
                        const color = Tables._SIGNAL_COLORS[signal];
                        const bg    = Tables._SIGNAL_BG[signal];
                        const dot   = `<span style="color:${color};font-size:0.65em;margin-right:4px;vertical-align:middle">●</span>`;
                        val = `<span style="color:${color};font-weight:600">${val}</span>`;
                        html += `<td style="background:${bg};border-radius:4px">${dot}${val}</td>`;
                        continue;
                    }
                } else if (td?.error) {
                    val = '<span class="val-negative">Error</span>';
                }
                html += `<td>${val}</td>`;
            }
            html += '</tr>';
        }

        html += '</tbody></table></div>';
        return html;
    },

    // Key items to highlight in financial statements
    KEY_INCOME_ITEMS: [
        'Total Revenue', 'Cost Of Revenue', 'Gross Profit', 'Operating Expense',
        'Operating Income', 'Net Income', 'EBITDA', 'Basic EPS', 'Diluted EPS',
    ],
    KEY_BALANCE_ITEMS: [
        'Total Assets', 'Current Assets', 'Cash And Cash Equivalents',
        'Net Receivables', 'Total Liabilities Net Minority Interest',
        'Current Liabilities', 'Total Debt', 'Stockholders Equity',
    ],
    KEY_CASHFLOW_ITEMS: [
        'Operating Cash Flow', 'Capital Expenditure', 'Free Cash Flow',
        'Investing Cash Flow', 'Financing Cash Flow',
    ],

    /**
     * Render financial statement table (periods as columns)
     */
    financialStatement(statementData, title, currency = '') {
        if (!statementData || Object.keys(statementData).length === 0) {
            return `<div class="card-title">${title}</div><p style="color:var(--text-muted)">No data available</p>`;
        }

        // Get all periods (dates)
        const allPeriods = new Set();
        for (const rowData of Object.values(statementData)) {
            for (const period of Object.keys(rowData)) {
                allPeriods.add(period);
            }
        }
        const periods = [...allPeriods].sort().reverse();

        // Determine which key items apply
        const allItems = Object.keys(statementData);
        let keyItems = [];
        if (allItems.some(i => Tables.KEY_INCOME_ITEMS.includes(i))) keyItems = Tables.KEY_INCOME_ITEMS;
        else if (allItems.some(i => Tables.KEY_BALANCE_ITEMS.includes(i))) keyItems = Tables.KEY_BALANCE_ITEMS;
        else if (allItems.some(i => Tables.KEY_CASHFLOW_ITEMS.includes(i))) keyItems = Tables.KEY_CASHFLOW_ITEMS;

        const uid = 'stmt-' + Math.random().toString(36).substring(2, 8);

        let html = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
            <div class="card-title" style="margin:0">${title}</div>
            ${keyItems.length > 0 ? `<label style="font-size:0.8em;color:var(--text-secondary);cursor:pointer">
                <input type="checkbox" id="${uid}-toggle" checked onchange="Tables.toggleKeyItems('${uid}')"> Key items only
            </label>` : ''}
        </div>`;
        html += `<div style="overflow-x:auto"><table class="data-table" id="${uid}"><thead><tr><th>Item</th>`;
        for (const p of periods) {
            html += `<th>${p.substring(0, 4)}</th>`;
        }
        html += '</tr></thead><tbody>';

        for (const [item, values] of Object.entries(statementData)) {
            const isKey = keyItems.length === 0 || keyItems.includes(item);
            html += `<tr class="${isKey ? 'key-item' : 'minor-item'}" ${!isKey ? 'style="display:none"' : ''}>`;
            html += `<td style="${isKey ? 'font-weight:600' : ''}">${item}</td>`;
            for (const p of periods) {
                const v = values[p];
                html += `<td>${Tables.formatValue(v, true, currency)}</td>`;
            }
            html += '</tr>';
        }

        html += '</tbody></table></div>';
        return html;
    },

    toggleKeyItems(uid) {
        const checked = document.getElementById(`${uid}-toggle`).checked;
        const table = document.getElementById(uid);
        table.querySelectorAll('.minor-item').forEach(row => {
            row.style.display = checked ? 'none' : '';
        });
    },

    /**
     * Render trend table
     */
    trendTable(trendData, title) {
        if (!trendData || trendData.length === 0) return '';

        let html = `<div class="card-title">${title}</div>`;
        html += '<table class="data-table"><thead><tr><th>Period</th><th>Value</th><th>Growth</th></tr></thead><tbody>';
        for (const row of trendData) {
            const growthClass = row.growth_pct != null
                ? (row.growth_pct >= 0 ? 'val-positive' : 'val-negative') : '';
            const growthStr = row.growth_pct != null ? `${row.growth_pct > 0 ? '+' : ''}${row.growth_pct}%` : '-';
            html += `<tr>
                <td>${row.period.substring(0, 10)}</td>
                <td>${Tables.formatValue(row.value, true)}</td>
                <td class="${growthClass}">${growthStr}</td>
            </tr>`;
        }
        html += '</tbody></table>';
        return html;
    },

    /**
     * Add thousand separators to a number string
     */
    addSeparator(numStr) {
        const parts = numStr.split('.');
        parts[0] = parts[0].replace(/\B(?=(\d{3})+(?!\d))/g, ',');
        return parts.join('.');
    },

    /**
     * Format a value for display
     * @param {*} v - value
     * @param {boolean} large - use B/T/M/K suffix for large numbers
     * @param {string} currency - currency prefix (e.g. 'IDR', 'USD')
     */
    formatValue(v, large = false, currency = '') {
        if (v == null || v === 'N/A') return '<span style="color:var(--text-muted)">N/A</span>';
        if (typeof v === 'string') return v;
        if (typeof v === 'number') {
            const neg = v < 0;
            const abs = Math.abs(v);
            let formatted;

            if (large && abs >= 1e12) {
                formatted = Tables.addSeparator((abs / 1e12).toFixed(2)) + 'T';
            } else if (large && abs >= 1e9) {
                formatted = Tables.addSeparator((abs / 1e9).toFixed(2)) + 'B';
            } else if (large && abs >= 1e6) {
                formatted = Tables.addSeparator((abs / 1e6).toFixed(2)) + 'M';
            } else if (large && abs >= 1e3) {
                formatted = Tables.addSeparator(Math.round(abs).toString());
            } else if (abs >= 1000) {
                formatted = Tables.addSeparator(abs.toFixed(2));
            } else {
                formatted = abs.toFixed(2);
            }

            const prefix = currency ? `<span style="color:var(--text-muted);font-size:0.85em">${currency} </span>` : '';
            const sign = neg ? '-' : '';
            const colorClass = neg ? ' style="color:var(--red)"' : '';
            return `<span${colorClass}>${sign}${prefix}${formatted}</span>`;
        }
        return String(v);
    },

    /**
     * Format price with currency
     */
    formatPrice(v, currency = 'IDR') {
        if (v == null) return '<span style="color:var(--text-muted)">N/A</span>';
        return Tables.formatValue(v, false, currency);
    },

    /**
     * Format ratio (no currency, 2 decimal, with suffix like % or x)
     */
    formatRatio(v, suffix = '') {
        if (v == null) return '<span style="color:var(--text-muted)">N/A</span>';
        if (typeof v !== 'number') return String(v);
        const formatted = Tables.addSeparator(v.toFixed(2));
        return `${formatted}${suffix}`;
    },
};
