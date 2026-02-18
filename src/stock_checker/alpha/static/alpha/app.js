/**
 * Stock Alpha - Main SPA Application
 */
const App = {
    baseUrl: '/alpha',

    async api(path, options = {}) {
        const url = this.baseUrl + path;
        const config = {
            headers: { 'Content-Type': 'application/json' },
            ...options,
        };
        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }
        const resp = await fetch(url, config);
        if (!resp.ok) {
            const err = await resp.json().catch(() => ({ error: resp.statusText }));
            throw new Error(err.error || 'Request failed');
        }
        // Check if response is file download (Content-Disposition: attachment)
        const cd = resp.headers.get('content-disposition') || '';
        if (cd.includes('attachment')) {
            return resp.blob();
        }
        return resp.json();
    },

    showLoading() { document.getElementById('loading').classList.remove('hidden'); },
    hideLoading() { document.getElementById('loading').classList.add('hidden'); },

    toast(message, type = 'info') {
        const container = document.getElementById('toast-container');
        const el = document.createElement('div');
        el.className = `toast toast-${type}`;
        el.textContent = message;
        container.appendChild(el);
        setTimeout(() => el.remove(), 4000);
    },

    render(html) {
        const el = document.getElementById('page-content');
        el.innerHTML = html;
        el.classList.add('fade-in');
        setTimeout(() => el.classList.remove('fade-in'), 300);
    },

    renderSkeleton(type = 'detail') {
        const skeletons = {
            detail: `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-card"></div>
                <div class="grid grid-3"><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div><div class="skeleton skeleton-card"></div></div>
                <div class="skeleton skeleton-chart"></div>`,
            compare: `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-card"></div>
                <div class="grid grid-2"><div class="skeleton skeleton-chart"></div><div class="skeleton skeleton-chart"></div></div>`,
            list: `
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-card"></div>
                <div class="skeleton skeleton-card"></div>
                <div class="skeleton skeleton-card"></div>`,
        };
        document.getElementById('page-content').innerHTML = skeletons[type] || skeletons.list;
    },

    renderError(message, retryFn) {
        let html = `<div class="error-state"><h3>Something went wrong</h3><p>${message}</p>`;
        if (retryFn) {
            html += `<button class="btn btn-primary" id="btn-retry">Try Again</button>`;
        }
        html += '</div>';
        this.render(html);
        if (retryFn) {
            document.getElementById('btn-retry').onclick = retryFn;
        }
    },

    // ====== PAGE RENDERERS ======

    // --- Dashboard ---
    _marketIndices: [
        { symbol: '^JKSE', label: 'IHSG' },
        { symbol: '^JKLQ45', label: 'LQ45' },
        { symbol: '^GSPC', label: 'S&P 500' },
        { symbol: '^IXIC', label: 'NASDAQ' },
        { symbol: '^N225', label: 'NIKKEI' },
        { symbol: '^HSI', label: 'HANG SENG' },
        { symbol: '^FTSE', label: 'FTSE 100' },
        { symbol: '^GDAXI', label: 'DAX' },
    ],
    _dashboardIndicators: ['SMA20', 'SMA50'],
    _dashboardTicker: 'BBCA.JK',
    _dashboardPeriod: '1y',

    async renderDashboard() {
        let watchlistsHtml = '';
        let notesHtml = '';
        try {
            const watchlists = await this.api('/api/watchlists');
            if (watchlists.length > 0) {
                watchlistsHtml = watchlists.map(w => `
                    <div class="card" style="cursor:pointer" onclick="Router.navigate('#watchlists')">
                        <div class="card-title">${w.name}</div>
                        <p style="color:var(--text-secondary);font-size:0.9em">${w.description || 'No description'}</p>
                        <div class="ticker-chips">
                            ${w.items.map(i => `<span class="ticker-chip" onclick="event.stopPropagation();Router.navigate('#detail/${i.ticker}')">${i.ticker}</span>`).join('')}
                        </div>
                    </div>
                `).join('');
            } else {
                watchlistsHtml = '<div class="empty-state"><p>No watchlists yet. Create one from the Watchlists page.</p></div>';
            }

            const notes = await this.api('/api/notes');
            if (notes.length > 0) {
                notesHtml = notes.slice(0, 5).map(n => `
                    <div class="card">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <span class="badge badge-blue">${n.ticker}</span>
                            <span style="color:var(--text-muted);font-size:0.8em">${n.updated_at.substring(0,10)}</span>
                        </div>
                        <div class="card-title" style="margin-top:8px">${n.title}</div>
                        <p style="color:var(--text-secondary);font-size:0.9em">${(n.content || '').substring(0, 150)}${n.content && n.content.length > 150 ? '...' : ''}</p>
                    </div>
                `).join('');
            } else {
                notesHtml = '<div class="empty-state"><p>No notes yet.</p></div>';
            }
        } catch (e) {
            watchlistsHtml = '<div class="empty-state"><p>No watchlists yet.</p></div>';
            notesHtml = '<div class="empty-state"><p>No notes yet.</p></div>';
        }

        const availableIndicators = [
            { id: 'SMA20', label: 'SMA 20', group: 'Moving Avg' },
            { id: 'SMA50', label: 'SMA 50', group: 'Moving Avg' },
            { id: 'SMA200', label: 'SMA 200', group: 'Moving Avg' },
            { id: 'EMA12', label: 'EMA 12', group: 'Moving Avg' },
            { id: 'EMA26', label: 'EMA 26', group: 'Moving Avg' },
            { id: 'BB20', label: 'Bollinger', group: 'Bands' },
            { id: 'RSI14', label: 'RSI 14', group: 'Oscillator' },
            { id: 'MACD', label: 'MACD', group: 'Oscillator' },
        ];

        const indicatorChips = availableIndicators.map(ind => {
            const active = this._dashboardIndicators.includes(ind.id);
            return `<label class="indicator-chip ${active ? 'active' : ''}" title="${ind.group}">
                <input type="checkbox" value="${ind.id}" class="dash-ind-check" ${active ? 'checked' : ''} style="display:none">
                ${ind.label}
            </label>`;
        }).join('');

        const periodOptions = [
            { v: '1mo', l: '1M' }, { v: '3mo', l: '3M' }, { v: '6mo', l: '6M' },
            { v: '1y', l: '1Y' }, { v: '2y', l: '2Y' }, { v: '5y', l: '5Y' },
        ].map(p => `<button class="btn btn-sm ${p.v === this._dashboardPeriod ? 'btn-primary' : 'btn-secondary'} dash-period-btn" data-period="${p.v}">${p.l}</button>`).join('');

        const indexChips = this._marketIndices.map(idx =>
            `<span class="index-chip" data-symbol="${idx.symbol}">${idx.label}</span>`
        ).join('');

        this.render(`
            <div class="section-header">
                <h2>Dashboard</h2>
                <button class="btn btn-sm btn-secondary" id="btn-dash-screenshot">Screenshot</button>
            </div>

            <div class="card">
                <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:12px">
                    <div style="display:flex;align-items:center;gap:8px">
                        <input type="text" id="dash-ticker" value="${this._dashboardTicker}" placeholder="BBCA.JK"
                            style="width:120px;background:var(--bg-input);border:1px solid var(--border);color:var(--text-primary);padding:6px 10px;border-radius:var(--radius)" />
                        <button class="btn btn-primary btn-sm" id="btn-dash-load">Load Chart</button>
                    </div>
                    <div style="display:flex;gap:4px">${periodOptions}</div>
                </div>
                <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px;align-items:center">
                    <span style="color:var(--text-muted);font-size:0.8em">Indicators:</span>
                    ${indicatorChips}
                    <div style="display:flex;align-items:center;gap:4px;margin-left:8px">
                        <input type="text" id="dash-custom-ind" placeholder="e.g. SMA100, EMA50"
                            style="width:120px;background:var(--bg-input);border:1px solid var(--border);color:var(--text-primary);padding:4px 8px;border-radius:var(--radius);font-size:0.8em" />
                        <button class="btn btn-sm btn-secondary" id="btn-add-ind">Add</button>
                    </div>
                </div>
                <div id="dash-price-chart"><div class="skeleton skeleton-chart"></div></div>
            </div>

            <div style="margin-bottom:16px">
                <h3 style="margin-bottom:8px;color:var(--text-secondary)">Market Indices</h3>
                <div class="ticker-chips">${indexChips}</div>
            </div>

            <div class="grid grid-2">
                <div>
                    <h3 style="margin-bottom:12px">Watchlists</h3>
                    ${watchlistsHtml}
                </div>
                <div>
                    <h3 style="margin-bottom:12px">Recent Notes</h3>
                    ${notesHtml}
                </div>
            </div>
            <div style="margin-top:20px">
                <h3 style="margin-bottom:12px">Quick Access</h3>
                <div class="ticker-chips">
                    ${['BBCA.JK','BBRI.JK','BMRI.JK','TLKM.JK','ASII.JK','UNVR.JK','ICBP.JK','BBNI.JK']
                        .map(t => `<span class="ticker-chip" onclick="App._dashboardTicker='${t}';document.getElementById('dash-ticker').value='${t}';App._loadDashChart()">${t}</span>`).join('')}
                </div>
            </div>
        `);

        // Event: load chart
        document.getElementById('btn-dash-load').onclick = () => this._loadDashChart();
        document.getElementById('dash-ticker').addEventListener('keydown', e => {
            if (e.key === 'Enter') this._loadDashChart();
        });

        // Event: period buttons
        document.querySelectorAll('.dash-period-btn').forEach(btn => {
            btn.onclick = () => {
                this._dashboardPeriod = btn.dataset.period;
                document.querySelectorAll('.dash-period-btn').forEach(b =>
                    b.className = `btn btn-sm ${b.dataset.period === this._dashboardPeriod ? 'btn-primary' : 'btn-secondary'} dash-period-btn`
                );
                this._loadDashChart();
            };
        });

        // Event: indicator checkboxes
        document.querySelectorAll('.dash-ind-check').forEach(cb => {
            cb.onchange = () => {
                const label = cb.parentElement;
                if (cb.checked) {
                    this._dashboardIndicators.push(cb.value);
                    label.classList.add('active');
                } else {
                    this._dashboardIndicators = this._dashboardIndicators.filter(i => i !== cb.value);
                    label.classList.remove('active');
                }
                this._loadDashChart();
            };
        });

        // Event: add custom indicator
        document.getElementById('btn-add-ind').onclick = () => {
            const input = document.getElementById('dash-custom-ind');
            const val = input.value.trim().toUpperCase();
            if (val && !this._dashboardIndicators.includes(val)) {
                this._dashboardIndicators.push(val);
                input.value = '';
                this._loadDashChart();
                // Re-render to show updated chips
                this.renderDashboard();
            }
        };

        // Event: index chips
        document.querySelectorAll('.index-chip').forEach(chip => {
            chip.onclick = () => {
                const symbol = chip.dataset.symbol;
                this._dashboardTicker = symbol;
                document.getElementById('dash-ticker').value = symbol;
                this._loadDashChart();
            };
        });

        // Event: screenshot
        document.getElementById('btn-dash-screenshot').onclick = () => this.screenshotToClipboard();

        // Auto-load chart
        this._loadDashChart();
    },

    async _loadDashChart() {
        const ticker = (document.getElementById('dash-ticker')?.value || this._dashboardTicker).trim().toUpperCase();
        this._dashboardTicker = ticker;
        if (!ticker) return;

        const chartDiv = document.getElementById('dash-price-chart');
        if (!chartDiv) return;
        chartDiv.innerHTML = '<div class="skeleton skeleton-chart"></div>';

        try {
            const data = await this.api('/api/price-history', {
                method: 'POST',
                body: {
                    ticker,
                    period: this._dashboardPeriod,
                    indicators: this._dashboardIndicators,
                },
            });
            if (data.error) {
                chartDiv.innerHTML = `<p class="val-negative">${data.error}</p>`;
                return;
            }
            chartDiv.innerHTML = '<div id="dash-chart-container"></div>';
            Charts.priceChart('dash-chart-container', data, data.indicators || {});
        } catch (e) {
            chartDiv.innerHTML = `<p class="val-negative">Error: ${e.message}</p>`;
        }
    },

    _computeRecommendations(fin, trends) {
        const ps = fin.price_summary || {};
        const ratios = fin.ratios || {};
        const result = { short: null, medium: null, long: null };

        // --- Short-term (1-3 months): price position in 52-week range ---
        const cur = ps.current_price;
        const hi52 = ps['52w_high'];
        const lo52 = ps['52w_low'];
        let shortScore = 0;
        const shortReasons = [];
        if (cur != null && hi52 != null && lo52 != null && hi52 !== lo52) {
            const pctInRange = (cur - lo52) / (hi52 - lo52);
            if (pctInRange < 0.3) { shortScore += 1; shortReasons.push(`Price near 52W low (${(pctInRange * 100).toFixed(0)}% of range)`); }
            else if (pctInRange > 0.8) { shortScore -= 1; shortReasons.push(`Price near 52W high (${(pctInRange * 100).toFixed(0)}% of range)`); }
            else { shortReasons.push(`Price at ${(pctInRange * 100).toFixed(0)}% of 52W range`); }
        }
        result.short = { score: shortScore, reasons: shortReasons };

        // --- Medium-term (3-12 months): PER valuation + Net Income CAGR ---
        let medScore = 0;
        const medReasons = [];
        const per = ratios['PER'];
        if (per != null) {
            if (per > 0 && per < 10) { medScore += 1; medReasons.push(`Low PER (${per.toFixed(1)}x) — potentially undervalued`); }
            else if (per > 30) { medScore -= 1; medReasons.push(`High PER (${per.toFixed(1)}x) — expensive valuation`); }
            else { medReasons.push(`PER ${per.toFixed(1)}x — moderate valuation`); }
        }
        if (trends?.annual?.['Net Income']?.cagr != null) {
            const cagr = trends.annual['Net Income'].cagr;
            if (cagr > 10) { medScore += 1; medReasons.push(`Net Income CAGR +${cagr}% — strong earnings growth`); }
            else if (cagr < -5) { medScore -= 1; medReasons.push(`Net Income CAGR ${cagr}% — declining earnings`); }
            else { medReasons.push(`Net Income CAGR ${cagr > 0 ? '+' : ''}${cagr}%`); }
        }
        result.medium = { score: medScore, reasons: medReasons };

        // --- Long-term (1-3 years): ROE + DER + Revenue CAGR ---
        let longScore = 0;
        const longReasons = [];
        const roe = ratios['ROE'];
        if (roe != null) {
            if (roe > 15) { longScore += 1; longReasons.push(`Strong ROE (${roe.toFixed(1)}%) — efficient capital use`); }
            else if (roe < 5) { longScore -= 1; longReasons.push(`Weak ROE (${roe.toFixed(1)}%)`); }
            else { longReasons.push(`ROE ${roe.toFixed(1)}%`); }
        }
        const der = ratios['DER'];
        if (der != null) {
            if (der < 0.5) { longScore += 1; longReasons.push(`Low DER (${der.toFixed(2)}x) — conservative leverage`); }
            else if (der > 2) { longScore -= 1; longReasons.push(`High DER (${der.toFixed(2)}x) — high leverage risk`); }
            else { longReasons.push(`DER ${der.toFixed(2)}x`); }
        }
        if (trends?.annual?.['Total Revenue']?.cagr != null) {
            const cagr = trends.annual['Total Revenue'].cagr;
            if (cagr > 10) { longScore += 1; longReasons.push(`Revenue CAGR +${cagr}% — strong top-line growth`); }
            else if (cagr < 0) { longScore -= 1; longReasons.push(`Revenue CAGR ${cagr}% — shrinking revenue`); }
            else { longReasons.push(`Revenue CAGR +${cagr}%`); }
        }
        result.long = { score: longScore, reasons: longReasons };

        return result;
    },

    _recLabel(score) {
        if (score >= 1) return { text: 'BUY', cls: 'badge-green' };
        if (score <= -1) return { text: 'SELL', cls: 'badge-red' };
        return { text: 'HOLD', cls: 'badge-orange' };
    },

    _renderRecommendationBox(recs) {
        const terms = [
            { key: 'short', label: 'Short-term', sub: '1-3 months' },
            { key: 'medium', label: 'Medium-term', sub: '3-12 months' },
            { key: 'long', label: 'Long-term', sub: '1-3 years' },
        ];
        const cols = terms.map(t => {
            const r = recs[t.key];
            if (!r || r.reasons.length === 0) return `<div class="rec-col"><div class="rec-col-header">${t.label}<br><span style="font-size:0.75em;color:var(--text-muted)">${t.sub}</span></div><p style="color:var(--text-muted);font-size:0.85em">Insufficient data</p></div>`;
            const badge = this._recLabel(r.score);
            return `<div class="rec-col">
                <div class="rec-col-header">${t.label}<br><span style="font-size:0.75em;color:var(--text-muted)">${t.sub}</span></div>
                <div style="margin:8px 0"><span class="badge ${badge.cls}" style="font-size:1em;padding:4px 14px">${badge.text}</span></div>
                <ul style="list-style:none;padding:0;margin:0">${r.reasons.map(reason => `<li style="color:var(--text-secondary);font-size:0.85em;margin-bottom:4px;padding-left:10px;border-left:2px solid var(--border)">${reason}</li>`).join('')}</ul>
            </div>`;
        }).join('');
        return `<div class="card">
            <div class="card-title">Recommendation Summary</div>
            <div class="grid grid-3">${cols}</div>
            <p style="color:var(--text-muted);font-size:0.75em;margin-top:12px;font-style:italic">Disclaimer: This is an automated analysis based on financial ratios and historical trends. It is not financial advice. Always do your own research before making investment decisions.</p>
        </div>`;
    },

    async _loadDetailChart(ticker) {
        if (!ticker) return;
        const chartDiv = document.getElementById('detail-price-chart');
        if (!chartDiv) return;
        chartDiv.innerHTML = '<div class="skeleton skeleton-chart"></div>';

        try {
            const data = await this.api('/api/price-history', {
                method: 'POST',
                body: {
                    ticker,
                    period: this._detailPeriod,
                    indicators: this._detailIndicators,
                },
            });
            if (data.error) {
                chartDiv.innerHTML = `<p class="val-negative">${data.error}</p>`;
                return;
            }
            chartDiv.innerHTML = '<div id="detail-chart-container"></div>';
            Charts.priceChart('detail-chart-container', data, data.indicators || {});
        } catch (e) {
            chartDiv.innerHTML = `<p class="val-negative">Error: ${e.message}</p>`;
        }
    },

    // --- Detail ---
    _detailIndicators: ['SMA20', 'SMA50'],
    _detailPeriod: '1y',

    async renderDetail(ticker) {
        if (!ticker) {
            this.render('<div class="empty-state"><h3>Enter a ticker to analyze</h3></div>');
            return;
        }
        this.renderSkeleton('detail');
        this.showLoading();
        try {
            const [fin, trends] = await Promise.all([
                this.api('/api/financials', { method: 'POST', body: { ticker } }),
                this.api('/api/trends', { method: 'POST', body: { ticker } }),
            ]);

            const fv = Tables.formatValue;
            const ps = fin.price_summary || {};
            const hl = fin.highlights || {};
            const ccy = ps.currency || '';

            // Price summary card
            const priceSummaryHtml = `
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px">
                        <div>
                            <span style="font-size:2em;font-weight:700">${Tables.formatPrice(ps.current_price, ccy)}</span>
                        </div>
                        <div style="display:flex;gap:16px;flex-wrap:wrap">
                            <div><span style="color:var(--text-muted);font-size:0.8em">Mkt Cap</span><br>${fv(ps.market_cap, true, ccy)}</div>
                            <div><span style="color:var(--text-muted);font-size:0.8em">52W High</span><br>${Tables.formatPrice(ps['52w_high'], ccy)}</div>
                            <div><span style="color:var(--text-muted);font-size:0.8em">52W Low</span><br>${Tables.formatPrice(ps['52w_low'], ccy)}</div>
                            <div><span style="color:var(--text-muted);font-size:0.8em">Shares</span><br>${fv(ps.shares_outstanding, true)}</div>
                            <div><span style="color:var(--text-muted);font-size:0.8em">Avg Vol</span><br>${fv(ps.avg_volume, true)}</div>
                        </div>
                    </div>
                </div>`;

            // Highlights card
            let highlightsHtml = '';
            if (Object.keys(hl).length > 0) {
                highlightsHtml = '<div class="card"><div class="card-title">Latest Year Highlights</div><div class="grid grid-3">' +
                    Object.entries(hl).map(([k, v]) => `
                        <div style="padding:8px;background:var(--bg-input);border-radius:var(--radius)">
                            <div style="color:var(--text-muted);font-size:0.8em">${k}</div>
                            <div style="font-size:1.1em;font-weight:600">${fv(v, true, ccy)}</div>
                        </div>
                    `).join('') + '</div></div>';
            }

            // Ratios - split into categories
            const ratioCategories = {
                'Valuation': ['PER', 'PBV', 'EV/EBITDA', 'PEG'],
                'Profitability': ['ROE', 'ROA', 'NPM', 'GPM'],
                'Risk & Leverage': ['Beta', 'DER', 'Current Ratio', 'Dividend Yield'],
            };
            // Format ratios with appropriate suffixes
            const ratioSuffix = { 'ROE': '%', 'ROA': '%', 'NPM': '%', 'GPM': '%', 'Dividend Yield': '%' };
            const ratioSuffixX = { 'PER': 'x', 'PBV': 'x', 'EV/EBITDA': 'x', 'PEG': 'x', 'DER': 'x', 'Current Ratio': 'x' };
            let ratiosHtml = '<div class="grid grid-3">';
            for (const [cat, keys] of Object.entries(ratioCategories)) {
                const filtered = {};
                keys.forEach(k => {
                    if (fin.ratios[k] !== undefined) {
                        const suffix = ratioSuffix[k] || ratioSuffixX[k] || '';
                        filtered[k] = Tables.formatRatio(fin.ratios[k], suffix);
                    }
                });
                ratiosHtml += `<div class="card"><div class="card-title">${cat}</div>${Tables.keyValue(filtered)}</div>`;
            }
            ratiosHtml += '</div>';

            // Anomalies
            let anomalyHtml = '';
            if (fin.anomalies && fin.anomalies.length > 0) {
                anomalyHtml = '<div class="card"><div class="card-title">Anomaly Alerts</div>' +
                    fin.anomalies.map(a => `
                        <div class="anomaly-alert anomaly-${a.severity || 'info'}">
                            ${a.message || `${a.type}: ${a.label} = ${a.value} (z=${a.z_score})`}
                        </div>
                    `).join('') + '</div>';
            }

            // Trend charts
            const trendMetrics = ['Total Revenue', 'Net Income', 'Operating Cash Flow', 'Free Cash Flow', 'Basic EPS', 'Total Assets']
                .filter(m => trends.annual && trends.annual[m]);
            const trendChartsHtml = trendMetrics.length > 0
                ? '<div class="grid grid-2">' + trendMetrics.map((m, i) =>
                    `<div class="card"><div id="trend-chart-${i}"></div>${
                        trends.annual[m].cagr != null
                        ? `<div style="text-align:center;margin-top:4px"><span class="badge ${trends.annual[m].cagr >= 0 ? 'badge-green' : 'badge-red'}">CAGR: ${trends.annual[m].cagr > 0 ? '+' : ''}${trends.annual[m].cagr}%</span></div>`
                        : ''
                    }</div>`
                ).join('') + '</div>'
                : '';

            // Financial statement tabs
            const stmtTabs = `
                <div class="card">
                    <div style="display:flex;gap:8px;margin-bottom:12px">
                        <button class="btn btn-sm btn-primary" onclick="App._showStmt('income')">Income Statement</button>
                        <button class="btn btn-sm btn-secondary" onclick="App._showStmt('balance')">Balance Sheet</button>
                        <button class="btn btn-sm btn-secondary" onclick="App._showStmt('cashflow')">Cash Flow</button>
                        <button class="btn btn-sm btn-secondary" onclick="App._showStmt('quarterly')">Quarterly</button>
                    </div>
                    <div id="stmt-income">${Tables.financialStatement(fin.income_statement, 'Income Statement (Annual)', ccy)}</div>
                    <div id="stmt-balance" class="hidden">${Tables.financialStatement(fin.balance_sheet, 'Balance Sheet', ccy)}</div>
                    <div id="stmt-cashflow" class="hidden">${Tables.financialStatement(fin.cash_flow, 'Cash Flow', ccy)}</div>
                    <div id="stmt-quarterly" class="hidden">${Tables.financialStatement(fin.quarterly_income, 'Income Statement (Quarterly)', ccy)}</div>
                </div>`;

            // Price chart section
            const detailIndicators = [
                { id: 'SMA20', label: 'SMA 20' }, { id: 'SMA50', label: 'SMA 50' },
                { id: 'SMA200', label: 'SMA 200' }, { id: 'EMA12', label: 'EMA 12' },
                { id: 'EMA26', label: 'EMA 26' }, { id: 'BB20', label: 'Bollinger' },
                { id: 'RSI14', label: 'RSI 14' }, { id: 'MACD', label: 'MACD' },
            ];
            const detIndChips = detailIndicators.map(ind => {
                const active = this._detailIndicators.includes(ind.id);
                return `<label class="indicator-chip ${active ? 'active' : ''}">
                    <input type="checkbox" value="${ind.id}" class="det-ind-check" ${active ? 'checked' : ''} style="display:none">
                    ${ind.label}
                </label>`;
            }).join('');
            const detPeriodBtns = [
                { v: '1mo', l: '1M' }, { v: '3mo', l: '3M' }, { v: '6mo', l: '6M' },
                { v: '1y', l: '1Y' }, { v: '2y', l: '2Y' }, { v: '5y', l: '5Y' },
            ].map(p => `<button class="btn btn-sm ${p.v === this._detailPeriod ? 'btn-primary' : 'btn-secondary'} det-period-btn" data-period="${p.v}">${p.l}</button>`).join('');

            // Recommendation box
            const recs = this._computeRecommendations(fin, trends);
            const recommendationHtml = this._renderRecommendationBox(recs);

            const priceChartHtml = `
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:center;flex-wrap:wrap;gap:8px;margin-bottom:8px">
                        <div class="card-title" style="margin:0">Price Chart</div>
                        <div style="display:flex;gap:4px">${detPeriodBtns}</div>
                    </div>
                    <div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:8px;align-items:center">
                        <span style="color:var(--text-muted);font-size:0.8em">Indicators:</span>
                        ${detIndChips}
                        <div style="display:flex;align-items:center;gap:4px;margin-left:8px">
                            <input type="text" id="det-custom-ind" placeholder="e.g. SMA100"
                                style="width:100px;background:var(--bg-input);border:1px solid var(--border);color:var(--text-primary);padding:4px 8px;border-radius:var(--radius);font-size:0.8em" />
                            <button class="btn btn-sm btn-secondary" id="btn-det-add-ind">+</button>
                        </div>
                    </div>
                    <div id="detail-price-chart"><div class="skeleton skeleton-chart"></div></div>
                </div>`;

            this.render(`
                <div class="section-header">
                    <h2>${fin.name || ticker} <span style="color:var(--text-muted);font-weight:400">(${fin.ticker})</span></h2>
                    <div style="display:flex;gap:8px;align-items:center">
                        <span class="badge badge-blue">${fin.sector}</span>
                        <span class="badge badge-purple">${fin.industry}</span>
                        <button class="btn btn-sm btn-primary" onclick="Router.navigate('#model/${ticker}')">DCF Model</button>
                        <button class="btn btn-sm btn-secondary" id="btn-save-snapshot">Save Data</button>
                        <button class="btn btn-sm btn-secondary" id="btn-detail-screenshot">Screenshot</button>
                    </div>
                </div>
                ${priceSummaryHtml}
                ${recommendationHtml}
                ${priceChartHtml}
                ${highlightsHtml}
                ${ratiosHtml}
                ${anomalyHtml}
                ${trendChartsHtml}
                ${stmtTabs}
            `);

            // Save snapshot button
            document.getElementById('btn-save-snapshot').onclick = () =>
                this.saveSnapshot(ticker, fin.ratios);

            // Screenshot button
            document.getElementById('btn-detail-screenshot').onclick = () =>
                this.screenshotToClipboard();

            // Detail price chart events
            document.querySelectorAll('.det-period-btn').forEach(btn => {
                btn.onclick = () => {
                    this._detailPeriod = btn.dataset.period;
                    document.querySelectorAll('.det-period-btn').forEach(b =>
                        b.className = `btn btn-sm ${b.dataset.period === this._detailPeriod ? 'btn-primary' : 'btn-secondary'} det-period-btn`
                    );
                    this._loadDetailChart(ticker);
                };
            });
            document.querySelectorAll('.det-ind-check').forEach(cb => {
                cb.onchange = () => {
                    const label = cb.parentElement;
                    if (cb.checked) {
                        this._detailIndicators.push(cb.value);
                        label.classList.add('active');
                    } else {
                        this._detailIndicators = this._detailIndicators.filter(i => i !== cb.value);
                        label.classList.remove('active');
                    }
                    this._loadDetailChart(ticker);
                };
            });
            document.getElementById('btn-det-add-ind').onclick = () => {
                const input = document.getElementById('det-custom-ind');
                const val = input.value.trim().toUpperCase();
                if (val && !this._detailIndicators.includes(val)) {
                    this._detailIndicators.push(val);
                    input.value = '';
                    this._loadDetailChart(ticker);
                }
            };

            // Load detail price chart
            this._loadDetailChart(ticker);

            // Render trend charts after DOM is ready
            trendMetrics.forEach((m, i) => {
                const td = trends.annual[m].data;
                Charts.trendLine(
                    `trend-chart-${i}`, m,
                    td.map(d => d.period.substring(0, 10)),
                    td.map(d => d.value),
                    td.map(d => d.growth_pct)
                );
            });
        } catch (e) {
            this.renderError(e.message, () => this.renderDetail(ticker));
        }
        this.hideLoading();
    },

    _showStmt(which) {
        ['income', 'balance', 'cashflow', 'quarterly'].forEach(id => {
            document.getElementById(`stmt-${id}`).classList.toggle('hidden', id !== which);
        });
        // Update button styles
        const parent = document.getElementById(`stmt-${which}`).parentElement;
        parent.querySelectorAll('.btn').forEach((btn, i) => {
            const targets = ['income', 'balance', 'cashflow', 'quarterly'];
            btn.className = `btn btn-sm ${targets[i] === which ? 'btn-primary' : 'btn-secondary'}`;
        });
    },

    async saveSnapshot(ticker, ratios) {
        try {
            await this.api('/api/snapshots', { method: 'POST', body: { ticker, data: ratios } });
            this.toast('Snapshot saved!', 'success');
        } catch (e) { this.toast(e.message, 'error'); }
    },

    // --- Compare ---
    _lastCompareResult: null,

    async renderCompare() {
        const presets = {
            'IDX Banks': 'BBCA.JK, BBRI.JK, BMRI.JK, BBNI.JK',
            'IDX Telco': 'TLKM.JK, ISAT.JK, EXCL.JK',
            'IDX Consumer': 'UNVR.JK, ICBP.JK, INDF.JK, MYOR.JK',
            'IDX Mining': 'ADRO.JK, PTBA.JK, ANTM.JK, INCO.JK',
        };
        const presetButtons = Object.entries(presets).map(([name, tickers]) =>
            `<span class="ticker-chip" onclick="document.getElementById('compare-tickers').value='${tickers}'">${name}</span>`
        ).join('');

        this.render(`
            <div class="section-header"><h2>Compare Tickers</h2></div>
            <div class="card">
                <div class="form-group">
                    <label>Tickers (comma-separated, max 8)</label>
                    <input type="text" id="compare-tickers" placeholder="BBCA.JK, BBRI.JK, BMRI.JK" />
                </div>
                <div style="margin-bottom:12px">
                    <span style="color:var(--text-muted);font-size:0.8em">Quick presets:</span>
                    <div class="ticker-chips">${presetButtons}</div>
                </div>
                <div class="form-group">
                    <label>Categories</label>
                    <div style="display:flex;gap:8px;flex-wrap:wrap">
                        <label style="font-size:0.85em;cursor:pointer"><input type="checkbox" class="cat-check" value="valuation" checked> Valuation</label>
                        <label style="font-size:0.85em;cursor:pointer"><input type="checkbox" class="cat-check" value="profitability" checked> Profitability</label>
                        <label style="font-size:0.85em;cursor:pointer"><input type="checkbox" class="cat-check" value="risk" checked> Risk</label>
                        <label style="font-size:0.85em;cursor:pointer"><input type="checkbox" class="cat-check" value="market" checked> Market</label>
                    </div>
                </div>
                <button class="btn btn-primary" id="btn-compare">Compare</button>
            </div>
            <div id="compare-results"></div>
        `);

        document.getElementById('btn-compare').onclick = () => this._runCompare();
        document.getElementById('compare-tickers').addEventListener('keydown', e => {
            if (e.key === 'Enter') this._runCompare();
        });
    },

    async _runCompare() {
        const input = document.getElementById('compare-tickers').value;
        const tickers = input.split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
        if (tickers.length < 2) { this.toast('Enter at least 2 tickers', 'error'); return; }

        const categories = [...document.querySelectorAll('.cat-check:checked')].map(cb => cb.value);

        this.showLoading();
        try {
            const result = await this.api('/api/compare', {
                method: 'POST',
                body: { tickers, categories },
            });
            this._lastCompareResult = result;

            // Summary row: name + sector
            let summaryHtml = '<div class="card"><table class="data-table"><thead><tr><th></th>';
            result.tickers.forEach(t => { summaryHtml += `<th>${t}</th>`; });
            summaryHtml += '</tr></thead><tbody>';
            summaryHtml += '<tr><td style="font-weight:600">Name</td>';
            result.tickers.forEach(t => {
                const d = result.data[t];
                summaryHtml += `<td>${d?.name || t}</td>`;
            });
            summaryHtml += '</tr><tr><td style="font-weight:600">Sector</td>';
            result.tickers.forEach(t => {
                const d = result.data[t];
                summaryHtml += `<td>${d?.sector || 'N/A'}</td>`;
            });
            summaryHtml += '</tr></tbody></table></div>';

            // Main comparison table
            let tableHtml = '<div class="card">' +
                Tables.comparison(result.metrics, result.tickers, result.data) +
                '</div>';

            // Bar charts - group by category
            const chartMetrics = result.metrics.filter(m => m !== 'Market Cap' && m !== 'Current Price');
            let chartsHtml = '<div class="grid grid-2">';
            chartMetrics.forEach((m, i) => {
                chartsHtml += `<div class="card"><div id="cmp-chart-${i}"></div></div>`;
            });
            chartsHtml += '</div>';

            // Radar chart
            const radarMetrics = result.metrics.filter(m =>
                !['Market Cap', 'Current Price', 'Dividend Yield'].includes(m)
            );
            let radarHtml = '<div class="card"><div id="radar-chart"></div></div>';

            // Export buttons
            const exportHtml = `<div style="margin-top:12px;display:flex;gap:8px">
                <button class="btn btn-secondary btn-sm" onclick="App._exportCompare('csv')">Export CSV</button>
                <button class="btn btn-secondary btn-sm" onclick="App._exportCompare('json')">Export JSON</button>
                <button class="btn btn-secondary btn-sm" onclick="App._exportCompare('pdf')">Export PDF</button>
            </div>`;

            document.getElementById('compare-results').innerHTML =
                summaryHtml + tableHtml + chartsHtml + radarHtml + exportHtml;

            // Render bar charts + radar (setTimeout ensures DOM is settled)
            setTimeout(() => {
                chartMetrics.forEach((m, i) => {
                    const vals = result.tickers.map(t => result.data[t]?.metrics?.[m] ?? null);
                    Charts.comparisonBar(`cmp-chart-${i}`, result.tickers, m, vals);
                });

                const radarData = {};
                result.tickers.forEach(t => {
                    radarData[t] = {};
                    radarMetrics.forEach(m => {
                        radarData[t][m] = result.data[t]?.metrics?.[m] ?? 0;
                    });
                });
                Charts.radarChart('radar-chart', result.tickers, radarMetrics, radarData);
            }, 50);
        } catch (e) {
            document.getElementById('compare-results').innerHTML =
                `<div class="card"><p class="val-negative">Error: ${e.message}</p></div>`;
        }
        this.hideLoading();
    },

    async _exportCompare(format) {
        if (!this._lastCompareResult) { this.toast('No comparison data', 'error'); return; }
        try {
            const blob = await this.api(`/api/export/${format}`, {
                method: 'POST',
                body: {
                    data: this._lastCompareResult.data,
                    title: 'Ticker Comparison Report',
                    filename: `comparison.${format}`,
                },
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `comparison.${format}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) { this.toast(`Export failed: ${e.message}`, 'error'); }
    },

    // --- Model ---
    async renderModel(ticker) {
        if (!ticker) {
            this.render('<div class="empty-state"><h3>Enter a ticker in the nav bar, then click Model</h3></div>');
            return;
        }

        this.render(`
            <div class="section-header">
                <h2>Modelling: ${ticker}</h2>
                <div style="display:flex;gap:8px">
                    <button class="btn btn-sm btn-secondary" onclick="Router.navigate('#detail/${ticker}')">Back to Detail</button>
                    <button class="btn btn-sm btn-secondary" onclick="App._saveValuation('${ticker}')">Save Results</button>
                </div>
            </div>

            <div class="grid grid-2">
                <div class="card">
                    <div class="card-title">DCF Valuation</div>
                    <div id="dcf-form">${Forms.dcfForm()}</div>
                    <button class="btn btn-primary" id="btn-dcf">Run DCF</button>
                    <div id="dcf-results" style="margin-top:16px"></div>
                </div>
                <div class="card">
                    <div class="card-title">Scenario Analysis</div>
                    <div id="scenario-form">${Forms.scenarioForm()}</div>
                    <div class="form-row">
                        ${Forms.group('WACC (%)', 'scenario_wacc', 'number', 10, { step: '0.5', min: '1', max: '30' })}
                        ${Forms.group('Terminal Growth (%)', 'scenario_tg', 'number', 3, { step: '0.5', min: '0', max: '10' })}
                    </div>
                    <button class="btn btn-primary" id="btn-scenario">Run Scenarios</button>
                    <div id="scenario-results" style="margin-top:16px"></div>
                </div>
            </div>

            <div class="grid grid-2">
                <div class="card">
                    <div class="card-title">Sensitivity Matrix</div>
                    <p style="color:var(--text-muted);font-size:0.85em;margin-bottom:12px">WACC vs Growth Rate heatmap showing intrinsic value per share</p>
                    <button class="btn btn-primary" id="btn-sensitivity">Generate Heatmap</button>
                    <div id="sensitivity-results" style="margin-top:16px"></div>
                </div>
                <div class="card">
                    <div class="card-title">Linear Projection</div>
                    <div class="form-row">
                        <div class="form-group">
                            <label>Metric</label>
                            <select id="proj-metric">
                                <option value="Total Revenue">Total Revenue</option>
                                <option value="Net Income">Net Income</option>
                                <option value="Operating Cash Flow">Operating Cash Flow</option>
                                <option value="Free Cash Flow">Free Cash Flow</option>
                                <option value="Gross Profit">Gross Profit</option>
                                <option value="Basic EPS">Basic EPS</option>
                            </select>
                        </div>
                        ${Forms.group('Periods Ahead', 'proj_periods', 'number', 4, { step: '1', min: '1', max: '10' })}
                    </div>
                    <button class="btn btn-primary" id="btn-projection">Project</button>
                    <div id="projection-results" style="margin-top:16px"></div>
                </div>
            </div>
        `);

        this._modelTicker = ticker;
        this._modelResults = {};

        // DCF
        document.getElementById('btn-dcf').onclick = async () => {
            const vals = Forms.readValues('dcf-form');
            this.showLoading();
            try {
                const result = await this.api('/api/model/dcf', {
                    method: 'POST',
                    body: {
                        ticker,
                        growth_rate: vals.growth_rate / 100,
                        terminal_growth: vals.terminal_growth / 100,
                        wacc: vals.wacc / 100,
                        projection_years: vals.projection_years,
                    },
                });
                this._modelResults.dcf = result;
                if (result.error) {
                    document.getElementById('dcf-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    const upside = result.upside_pct != null
                        ? `<span class="${result.upside_pct >= 0 ? 'val-positive' : 'val-negative'}" style="font-size:1.2em;font-weight:700">${result.upside_pct > 0 ? '+' : ''}${result.upside_pct}%</span>`
                        : '';
                    const verdict = result.upside_pct != null
                        ? (result.upside_pct > 20 ? '<span class="badge badge-green">Undervalued</span>'
                           : result.upside_pct < -20 ? '<span class="badge badge-red">Overvalued</span>'
                           : '<span class="badge badge-orange">Fair Value</span>')
                        : '';
                    document.getElementById('dcf-results').innerHTML = `
                        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px">
                            <div>
                                <div style="color:var(--text-muted);font-size:0.8em">Intrinsic Value / Share</div>
                                <div style="font-size:1.8em;font-weight:700">${result.intrinsic_per_share != null ? Tables.addSeparator(result.intrinsic_per_share.toFixed(2)) : 'N/A'}</div>
                            </div>
                            <div style="text-align:right">
                                <div style="color:var(--text-muted);font-size:0.8em">Current: ${result.current_price != null ? Tables.addSeparator(result.current_price.toFixed(2)) : 'N/A'}</div>
                                <div>${upside} ${verdict}</div>
                            </div>
                        </div>
                        ${Tables.keyValue({
                            'FCF Base': Tables.formatValue(result.fcf_base, true),
                            'Sum PV of FCFs': Tables.formatValue(result.sum_pv_fcf, true),
                            'PV Terminal Value': Tables.formatValue(result.pv_terminal, true),
                            'Enterprise Value': Tables.formatValue(result.enterprise_value, true),
                            'Net Debt': Tables.formatValue(result.net_debt, true),
                            'Shares Outstanding': Tables.formatValue(result.shares_outstanding, true),
                        })}
                        <div id="dcf-chart" style="margin-top:12px"></div>
                    `;
                    // FCF projection chart (use setTimeout to ensure DOM is settled)
                    setTimeout(() => {
                        Charts.trendLine('dcf-chart', 'Projected FCF',
                            result.projected_fcf.map((_, i) => `Y${i + 1}`),
                            result.projected_fcf,
                            null
                        );
                    }, 50);
                }
            } catch (e) {
                document.getElementById('dcf-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // Scenario
        document.getElementById('btn-scenario').onclick = async () => {
            const vals = Forms.readValues('scenario-form');
            const wacc = (parseFloat(document.getElementById('scenario_wacc').value) || 10) / 100;
            const tg = (parseFloat(document.getElementById('scenario_tg').value) || 3) / 100;
            this.showLoading();
            try {
                const result = await this.api('/api/model/scenario', {
                    method: 'POST',
                    body: {
                        ticker,
                        scenarios: { bull: vals.bull / 100, base: vals.base / 100, bear: vals.bear / 100 },
                        wacc: wacc,
                        terminal_growth: tg,
                    },
                });
                this._modelResults.scenario = result;
                if (result.error) {
                    document.getElementById('scenario-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    const cp = result.current_price;
                    let html = '<table class="data-table"><thead><tr><th>Scenario</th><th>Growth</th><th>Intrinsic/Share</th><th>vs Current</th></tr></thead><tbody>';
                    const scenarioColors = { bull: 'badge-green', base: 'badge-blue', bear: 'badge-red' };
                    for (const [name, data] of Object.entries(result.scenarios)) {
                        const iv = data.intrinsic_per_share;
                        const diff = (iv && cp) ? ((iv - cp) / cp * 100).toFixed(1) : null;
                        const diffClass = diff != null ? (diff >= 0 ? 'val-positive' : 'val-negative') : '';
                        html += `<tr>
                            <td><span class="badge ${scenarioColors[name] || 'badge-blue'}">${name.charAt(0).toUpperCase() + name.slice(1)}</span></td>
                            <td>${(vals[name] || 0)}%</td>
                            <td style="font-weight:600">${iv != null ? Tables.addSeparator(iv.toFixed(2)) : 'N/A'}</td>
                            <td class="${diffClass}">${diff != null ? `${diff > 0 ? '+' : ''}${diff}%` : '-'}</td>
                        </tr>`;
                    }
                    html += '</tbody></table>';
                    if (cp) html += `<p style="margin-top:8px;color:var(--text-secondary)">Current price: ${Tables.addSeparator(cp.toFixed(2))}</p>`;

                    // Scenario bar chart
                    html += '<div id="scenario-chart" style="margin-top:12px"></div>';
                    document.getElementById('scenario-results').innerHTML = html;

                    const names = Object.keys(result.scenarios);
                    const values = names.map(n => result.scenarios[n].intrinsic_per_share || 0);
                    setTimeout(() => {
                        Charts.comparisonBar('scenario-chart', names.map(n => n.charAt(0).toUpperCase() + n.slice(1)), 'Intrinsic Value / Share', values);
                    }, 50);
                }
            } catch (e) {
                document.getElementById('scenario-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // Sensitivity
        document.getElementById('btn-sensitivity').onclick = async () => {
            this.showLoading();
            try {
                const result = await this.api('/api/model/sensitivity', {
                    method: 'POST',
                    body: { ticker },
                });
                this._modelResults.sensitivity = result;
                if (result.error) {
                    document.getElementById('sensitivity-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    document.getElementById('sensitivity-results').innerHTML = '<div id="sens-heatmap"></div>';
                    setTimeout(() => {
                        Charts.heatmap('sens-heatmap', 'Intrinsic Value / Share',
                            result.growth_labels, result.wacc_labels, result.matrix);
                    }, 50);
                }
            } catch (e) {
                document.getElementById('sensitivity-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // Projection
        document.getElementById('btn-projection').onclick = async () => {
            const metric = document.getElementById('proj-metric').value;
            const periods = parseInt(document.getElementById('proj_periods').value) || 4;
            this.showLoading();
            try {
                const result = await this.api('/api/model/projection', {
                    method: 'POST',
                    body: { ticker, metric, periods_ahead: periods },
                });
                this._modelResults.projection = result;
                if (result.error) {
                    document.getElementById('projection-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    document.getElementById('projection-results').innerHTML =
                        `<div id="proj-chart"></div>
                         <div style="margin-top:8px;display:flex;gap:16px;flex-wrap:wrap">
                            <span class="badge badge-blue">R² = ${result.r_squared}</span>
                            <span class="badge badge-green">Slope = ${Tables.formatValue(result.slope, true)}/yr</span>
                         </div>`;
                    setTimeout(() => {
                        Charts.projectionChart('proj-chart', `${metric} Projection`,
                            result.historical_labels.map(l => l.substring(0, 4)),
                            null,
                            result.fitted,
                            result.projections
                        );
                    }, 50);
                }
            } catch (e) {
                document.getElementById('projection-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };
    },

    async _saveValuation(ticker) {
        if (!this._modelResults || Object.keys(this._modelResults).length === 0) {
            this.toast('Run a model first before saving', 'error');
            return;
        }
        try {
            await this.api('/api/valuations', {
                method: 'POST',
                body: {
                    ticker,
                    model_type: 'dcf',
                    assumptions: this._modelResults.dcf ? {
                        growth_rate: Forms.readValues('dcf-form').growth_rate,
                        wacc: Forms.readValues('dcf-form').wacc,
                    } : {},
                    results: this._modelResults,
                },
            });
            this.toast('Valuation saved!', 'success');
        } catch (e) { this.toast(e.message, 'error'); }
    },

    // --- Notes ---
    async renderNotes() {
        this.showLoading();
        try {
            const notes = await this.api('/api/notes');
            let listHtml = '';
            if (notes.length > 0) {
                listHtml = notes.map(n => `
                    <div class="card">
                        <div style="display:flex;justify-content:space-between;align-items:start">
                            <div>
                                <span class="badge badge-blue">${n.ticker}</span>
                                ${n.tags.map(t => `<span class="badge badge-purple">${t}</span>`).join(' ')}
                            </div>
                            <div style="display:flex;gap:4px">
                                <button class="btn btn-sm btn-secondary" onclick="App.editNote(${n.id})">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="App.deleteNote(${n.id})">Del</button>
                            </div>
                        </div>
                        <div class="card-title" style="margin-top:8px">${n.title}</div>
                        <p style="color:var(--text-secondary);font-size:0.9em;white-space:pre-wrap">${n.content || ''}</p>
                        <p style="color:var(--text-muted);font-size:0.8em;margin-top:8px">${n.updated_at.substring(0,10)}</p>
                    </div>
                `).join('');
            } else {
                listHtml = '<div class="empty-state"><p>No notes yet. Create one below.</p></div>';
            }

            this.render(`
                <div class="section-header"><h2>Notes</h2></div>
                <div class="card">
                    <div class="card-title">New Note</div>
                    <div class="form-row">
                        ${Forms.group('Ticker', 'note-ticker', 'text', '', { placeholder: 'BBCA.JK' })}
                        ${Forms.group('Title', 'note-title', 'text', '', { placeholder: 'Analysis title' })}
                    </div>
                    ${Forms.group('Content', 'note-content', 'textarea', '', { placeholder: 'Your analysis notes...' })}
                    ${Forms.group('Tags (comma-separated)', 'note-tags', 'text', '', { placeholder: 'banking, analysis' })}
                    <button class="btn btn-primary" id="btn-save-note">Save Note</button>
                </div>
                <div id="notes-list">${listHtml}</div>
            `);

            document.getElementById('btn-save-note').onclick = async () => {
                const ticker = document.getElementById('note-ticker').value.trim();
                const title = document.getElementById('note-title').value.trim();
                const content = document.getElementById('note-content').value;
                const tags = document.getElementById('note-tags').value;
                if (!ticker || !title) { this.toast('Ticker and title required', 'error'); return; }
                try {
                    await this.api('/api/notes', { method: 'POST', body: { ticker, title, content, tags } });
                    this.toast('Note saved', 'success');
                    this.renderNotes();
                } catch (e) { this.toast(e.message, 'error'); }
            };
        } catch (e) {
            this.render(`<div class="card"><p class="val-negative">${e.message}</p></div>`);
        }
        this.hideLoading();
    },

    async deleteNote(id) {
        if (!confirm('Delete this note?')) return;
        try {
            await this.api(`/api/notes/${id}`, { method: 'DELETE' });
            this.toast('Note deleted', 'success');
            this.renderNotes();
        } catch (e) { this.toast(e.message, 'error'); }
    },

    async editNote(id) {
        try {
            const notes = await this.api('/api/notes');
            const note = notes.find(n => n.id === id);
            if (!note) { this.toast('Note not found', 'error'); return; }
            document.getElementById('note-ticker').value = note.ticker;
            document.getElementById('note-title').value = note.title;
            document.getElementById('note-content').value = note.content || '';
            document.getElementById('note-tags').value = (note.tags || []).join(', ');
            // Change save button to update
            const btn = document.getElementById('btn-save-note');
            btn.textContent = 'Update Note';
            btn.onclick = async () => {
                const ticker = document.getElementById('note-ticker').value.trim();
                const title = document.getElementById('note-title').value.trim();
                const content = document.getElementById('note-content').value;
                const tags = document.getElementById('note-tags').value;
                try {
                    await this.api(`/api/notes/${id}`, { method: 'PUT', body: { title, content, tags } });
                    this.toast('Note updated', 'success');
                    this.renderNotes();
                } catch (e) { this.toast(e.message, 'error'); }
            };
            window.scrollTo({ top: 0, behavior: 'smooth' });
        } catch (e) { this.toast(e.message, 'error'); }
    },

    // --- Watchlists ---
    async renderWatchlists() {
        this.showLoading();
        try {
            const watchlists = await this.api('/api/watchlists');
            let listHtml = '';
            if (watchlists.length > 0) {
                listHtml = watchlists.map(w => `
                    <div class="card">
                        <div style="display:flex;justify-content:space-between;align-items:center">
                            <div class="card-title" style="margin:0">${w.name}</div>
                            <button class="btn btn-sm btn-danger" onclick="App.deleteWatchlist(${w.id})">Delete</button>
                        </div>
                        <p style="color:var(--text-secondary);font-size:0.9em;margin:4px 0">${w.description || ''}</p>
                        <div class="ticker-chips">
                            ${w.items.map(i => `
                                <span class="ticker-chip">
                                    <span onclick="Router.navigate('#detail/${i.ticker}')">${i.ticker}</span>
                                    <span style="cursor:pointer;color:var(--red);margin-left:4px" onclick="App.removeFromWatchlist(${w.id},'${i.ticker}')">&times;</span>
                                </span>
                            `).join('')}
                        </div>
                        <div style="margin-top:8px;display:flex;gap:8px">
                            <input type="text" id="add-ticker-${w.id}" placeholder="Add ticker" style="width:120px;background:var(--bg-input);border:1px solid var(--border);color:var(--text-primary);padding:4px 8px;border-radius:var(--radius);font-size:0.85em" />
                            <button class="btn btn-sm btn-secondary" onclick="App.addToWatchlist(${w.id})">Add</button>
                        </div>
                    </div>
                `).join('');
            } else {
                listHtml = '<div class="empty-state"><p>No watchlists yet.</p></div>';
            }

            this.render(`
                <div class="section-header"><h2>Watchlists</h2></div>
                <div class="card">
                    <div class="card-title">New Watchlist</div>
                    <div class="form-row">
                        ${Forms.group('Name', 'wl-name', 'text', '', { placeholder: 'Banking Stocks' })}
                        ${Forms.group('Description', 'wl-desc', 'text', '', { placeholder: 'Optional description' })}
                    </div>
                    <button class="btn btn-primary" id="btn-create-wl">Create</button>
                </div>
                <div id="watchlists-list">${listHtml}</div>
            `);

            document.getElementById('btn-create-wl').onclick = async () => {
                const name = document.getElementById('wl-name').value.trim();
                if (!name) { this.toast('Name required', 'error'); return; }
                const desc = document.getElementById('wl-desc').value.trim();
                try {
                    await this.api('/api/watchlists', { method: 'POST', body: { name, description: desc } });
                    this.toast('Watchlist created', 'success');
                    this.renderWatchlists();
                } catch (e) { this.toast(e.message, 'error'); }
            };
        } catch (e) {
            this.render(`<div class="card"><p class="val-negative">${e.message}</p></div>`);
        }
        this.hideLoading();
    },

    async addToWatchlist(wid) {
        const input = document.getElementById(`add-ticker-${wid}`);
        const ticker = input.value.trim();
        if (!ticker) return;
        try {
            await this.api(`/api/watchlists/${wid}/items`, { method: 'POST', body: { ticker } });
            this.toast(`${ticker.toUpperCase()} added`, 'success');
            this.renderWatchlists();
        } catch (e) { this.toast(e.message, 'error'); }
    },

    async removeFromWatchlist(wid, ticker) {
        try {
            await this.api(`/api/watchlists/${wid}/items`, { method: 'DELETE', body: { ticker } });
            this.toast(`${ticker} removed`, 'success');
            this.renderWatchlists();
        } catch (e) { this.toast(e.message, 'error'); }
    },

    async deleteWatchlist(wid) {
        if (!confirm('Delete this watchlist?')) return;
        try {
            await this.api(`/api/watchlists/${wid}`, { method: 'DELETE' });
            this.toast('Watchlist deleted', 'success');
            this.renderWatchlists();
        } catch (e) { this.toast(e.message, 'error'); }
    },

    // --- Screenshot ---
    async screenshotToClipboard() {
        const target = document.getElementById('page-content');
        if (!target) return;
        this.toast('Capturing screenshot...', 'info');
        try {
            const canvas = await html2canvas(target, {
                backgroundColor: '#0f0f1a',
                scale: 2,
                useCORS: true,
                logging: false,
            });
            canvas.toBlob(async (blob) => {
                if (!blob) { this.toast('Screenshot failed', 'error'); return; }
                try {
                    await navigator.clipboard.write([
                        new ClipboardItem({ 'image/png': blob })
                    ]);
                    this.toast('Screenshot copied to clipboard!', 'success');
                } catch (clipErr) {
                    // Fallback: download as PNG
                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'screenshot.png';
                    a.click();
                    URL.revokeObjectURL(url);
                    this.toast('Clipboard unavailable — downloaded as PNG', 'info');
                }
            }, 'image/png');
        } catch (e) {
            this.toast(`Screenshot error: ${e.message}`, 'error');
        }
    },

    // --- Export helper ---
    async exportData(format, data) {
        try {
            const blob = await this.api(`/api/export/${format}`, {
                method: 'POST',
                body: { data },
            });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `export.${format}`;
            a.click();
            URL.revokeObjectURL(url);
        } catch (e) {
            this.toast(`Export failed: ${e.message}`, 'error');
        }
    },
};

// ====== INIT ======
document.addEventListener('DOMContentLoaded', () => {
    // Register routes
    Router.register('dashboard', () => App.renderDashboard());
    Router.register('detail', (ticker) => App.renderDetail(ticker));
    Router.register('compare', () => App.renderCompare());
    Router.register('model', (ticker) => App.renderModel(ticker));
    Router.register('notes', () => App.renderNotes());
    Router.register('watchlists', () => App.renderWatchlists());

    // Global ticker search
    document.getElementById('btn-go-detail').onclick = () => {
        const ticker = document.getElementById('global-ticker').value.trim().toUpperCase();
        if (ticker) Router.navigate(`#detail/${ticker}`);
    };
    document.getElementById('global-ticker').addEventListener('keydown', (e) => {
        if (e.key === 'Enter') {
            const ticker = e.target.value.trim().toUpperCase();
            if (ticker) Router.navigate(`#detail/${ticker}`);
        }
    });

    // Scroll-to-top button visibility
    const scrollBtn = document.getElementById('scroll-top');
    window.addEventListener('scroll', () => {
        scrollBtn.style.display = window.scrollY > 300 ? 'block' : 'none';
    });

    Router.init();
});
