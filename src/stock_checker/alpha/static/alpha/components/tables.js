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

    /**
     * Render a comparison table (tickers as columns)
     */
    comparison(metrics, tickers, data) {
        let html = '<div style="overflow-x:auto"><table class="data-table"><thead><tr><th>Metric</th>';
        for (const t of tickers) {
            html += `<th>${t}</th>`;
        }
        html += '</tr></thead><tbody>';

        for (const metric of metrics) {
            html += `<tr><td>${metric}</td>`;
            for (const t of tickers) {
                const td = data[t];
                let val = 'N/A';
                if (td && td.metrics && td.metrics[metric] != null) {
                    val = Tables.formatValue(td.metrics[metric]);
                } else if (td && td.error) {
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
    financialStatement(statementData, title) {
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
                html += `<td>${Tables.formatValue(v, true)}</td>`;
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
     * Format a value for display
     */
    formatValue(v, large = false) {
        if (v == null || v === 'N/A') return '<span style="color:var(--text-muted)">N/A</span>';
        if (typeof v === 'string') return v;
        if (typeof v === 'number') {
            if (large && Math.abs(v) >= 1e9) return (v / 1e9).toFixed(2) + 'B';
            if (large && Math.abs(v) >= 1e6) return (v / 1e6).toFixed(2) + 'M';
            if (large && Math.abs(v) >= 1e3) return (v / 1e3).toFixed(1) + 'K';
            return v.toFixed(2);
        }
        return String(v);
    },
};
