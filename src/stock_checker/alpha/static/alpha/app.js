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
    _dashboardTicker: '^JKSE',
    _dashboardPeriod: '1y',

    async renderDashboard() {
        let watchlistsHtml = '';
        let notesHtml = '';
        try {
            const watchlists = await this.api('/api/watchlists');
            if (watchlists.length > 0) {
                watchlistsHtml = watchlists.map(w => {
                    const tickerList = (w.items || []).map(i => i.ticker).filter(Boolean);
                    const compareLink = tickerList.length >= 2
                        ? `<button class="btn btn-sm btn-secondary" style="margin-top:8px" onclick="event.stopPropagation();App._compareWatchlist('${tickerList.join(',')}')">Compare All</button>`
                        : '';
                    return `
                    <div class="card" style="cursor:pointer" onclick="Router.navigate('#watchlists')">
                        <div class="card-title">${w.name}</div>
                        <p style="color:var(--text-secondary);font-size:0.9em">${w.description || 'No description'}</p>
                        <div class="ticker-chips">
                            ${tickerList.map(t => `<span class="ticker-chip" onclick="event.stopPropagation();Router.navigate('#detail/${t}')">${t}</span>`).join('')}
                        </div>
                        ${compareLink}
                    </div>`;
                }).join('');
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
            chartDiv.innerHTML = this._buildPriceStatsBar(data) + '<div id="dash-chart-container"></div>';
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

    _renderScoreGauges(scores) {
        const recColors = {
            'Strong Buy': '#4caf50',
            'Buy': '#8bc34a',
            'Hold': '#ff9800',
            'Avoid': '#f44336',
        };
        const recBadgeClass = {
            'Strong Buy': 'badge-green',
            'Buy': 'badge-green',
            'Hold': 'badge-orange',
            'Avoid': 'badge-red',
        };

        const qColor = (s) => s == null ? '#888' : s >= 70 ? '#4caf50' : s >= 50 ? '#ff9800' : '#f44336';

        // Q6: gauge with clickable label and breakdown panel
        const gauge = (label, score, color, type, breakdown) => {
            if (score == null) return `<div style="margin-bottom:12px"><div style="display:flex;justify-content:space-between;margin-bottom:4px"><span style="font-size:0.85em;color:var(--text-secondary)">${label}</span><span style="font-size:0.85em;color:var(--text-muted)">N/A</span></div><div style="height:8px;background:var(--bg-input);border-radius:4px"></div></div>`;
            const pct = Math.max(0, Math.min(100, score));
            const breakdownRows = breakdown ? Object.entries(breakdown)
                .filter(([, v]) => v != null)
                .map(([metric, val]) => {
                    const pv = Math.max(0, Math.min(100, val));
                    return `<div style="display:flex;align-items:center;gap:8px;margin-bottom:3px">
                        <span style="font-size:0.73em;color:var(--text-muted);width:110px;flex-shrink:0">${metric}</span>
                        <div style="flex:1;height:5px;background:var(--bg-card);border-radius:3px;overflow:hidden">
                            <div style="height:100%;width:${pv}%;background:${color};opacity:0.75;border-radius:3px"></div>
                        </div>
                        <span style="font-size:0.73em;font-weight:600;color:${color};width:28px;text-align:right">${pv.toFixed(0)}</span>
                    </div>`;
                }).join('') : '';
            return `<div style="margin-bottom:12px">
                <div style="display:flex;justify-content:space-between;margin-bottom:4px;cursor:pointer" onclick="App._toggleScoreBreakdown('${type}')">
                    <span style="font-size:0.85em;color:var(--text-secondary)">${label} <span style="color:var(--text-muted);font-size:0.75em">▾</span></span>
                    <span style="font-size:0.85em;font-weight:700;color:${color}">${pct.toFixed(1)}</span>
                </div>
                <div style="height:8px;background:var(--bg-input);border-radius:4px;overflow:hidden">
                    <div style="height:100%;width:${pct}%;background:${color};border-radius:4px;transition:width 0.6s ease"></div>
                </div>
                <div id="score-breakdown-${type}" class="hidden" style="margin-top:6px;padding:8px;background:var(--bg-input);border-radius:4px">
                    ${breakdownRows || '<p style="font-size:0.75em;color:var(--text-muted);margin:0">Breakdown unavailable</p>'}
                </div>
            </div>`;
        };

        const rec = scores.recommendation;
        const recHtml = rec
            ? `<div style="text-align:center;margin-bottom:16px"><span class="badge ${recBadgeClass[rec] || 'badge-blue'}" style="font-size:1.1em;padding:5px 18px">${rec}</span></div>`
            : '';

        const sd = scores.score_details || {};

        return `<div class="card">
            <div class="card-title">Composite Scores</div>
            ${recHtml}
            ${gauge('Quality', scores.quality_score, qColor(scores.quality_score), 'quality', sd.quality)}
            ${gauge('Valuation', scores.valuation_score, qColor(scores.valuation_score), 'valuation', sd.valuation)}
            ${gauge('Risk', scores.risk_score, qColor(scores.risk_score), 'risk', sd.risk)}
            ${scores.composite_score != null ? `<div style="padding-top:8px;border-top:1px solid var(--border);display:flex;justify-content:space-between;align-items:center"><span style="font-size:0.85em;color:var(--text-secondary)">Composite</span><span style="font-weight:700;font-size:1.1em;color:${qColor(scores.composite_score)}">${scores.composite_score.toFixed(1)} / 100</span></div>` : ''}
        </div>`;
    },

    _renderTechSignals(data) {
        if (!data || !data.indicators) return '';

        const ind = data.indicators;
        const prices = data.prices || [];
        if (prices.length === 0) return '';

        const lastClose = prices[prices.length - 1]?.close ?? null;

        const getLastVal = (arr) => {
            if (!arr || arr.length === 0) return null;
            const v = arr[arr.length - 1];
            return (v == null || isNaN(v)) ? null : v;
        };

        const rsi = getLastVal(ind.RSI14);
        const macd = getLastVal(ind.MACD);
        const macdSignal = getLastVal(ind.MACD_signal);
        const sma20 = getLastVal(ind.SMA20);
        const sma50 = getLastVal(ind.SMA50);
        const sma200 = getLastVal(ind.SMA200);

        const signals = [];

        // RSI
        if (rsi != null) {
            let s, cls;
            if (rsi < 30) { s = 'Oversold — potential buy signal'; cls = 'badge-green'; }
            else if (rsi > 70) { s = 'Overbought — potential sell signal'; cls = 'badge-red'; }
            else { s = 'Neutral zone'; cls = 'badge-blue'; }
            signals.push({ label: `RSI (${rsi.toFixed(1)})`, signal: s, cls });
        }

        // MACD
        if (macd != null && macdSignal != null) {
            const s = macd > macdSignal ? 'Bullish — MACD above signal' : 'Bearish — MACD below signal';
            const cls = macd > macdSignal ? 'badge-green' : 'badge-red';
            signals.push({ label: `MACD (${macd.toFixed(2)})`, signal: s, cls });
        }

        // SMA20 vs SMA50
        if (lastClose != null && sma20 != null && sma50 != null) {
            let s, cls;
            if (lastClose > sma20 && lastClose > sma50) { s = 'Uptrend — price above SMA20 & SMA50'; cls = 'badge-green'; }
            else if (lastClose < sma20 && lastClose < sma50) { s = 'Downtrend — price below SMA20 & SMA50'; cls = 'badge-red'; }
            else { s = 'Mixed — between moving averages'; cls = 'badge-orange'; }
            signals.push({ label: 'SMA20 vs SMA50', signal: s, cls });
        }

        // Golden / Death Cross (SMA50 vs SMA200)
        if (sma50 != null && sma200 != null) {
            const s = sma50 > sma200 ? 'Golden Cross — SMA50 above SMA200 (bullish)' : 'Death Cross — SMA50 below SMA200 (bearish)';
            const cls = sma50 > sma200 ? 'badge-green' : 'badge-red';
            signals.push({ label: 'SMA50 vs SMA200', signal: s, cls });
        }

        if (signals.length === 0) return '';

        return `<div class="card"><div class="card-title">Technical Signals</div>
            <table class="data-table"><tbody>
                ${signals.map(s => `<tr><td style="font-size:0.85em;color:var(--text-muted);white-space:nowrap">${s.label}</td><td><span class="badge ${s.cls}" style="font-size:0.8em">${s.signal}</span></td></tr>`).join('')}
            </tbody></table>
            <p style="color:var(--text-muted);font-size:0.72em;margin-top:8px;font-style:italic">Based on latest available price data. Not investment advice.</p>
        </div>`;
    },

    /** Simple markdown → HTML renderer (no external deps) */
    _md(raw) {
        if (!raw) return '';
        const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
        const inline = s => esc(s)
            .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.+?)\*/g, '<em>$1</em>')
            .replace(/`(.+?)`/g, '<code style="background:rgba(255,255,255,0.1);padding:1px 5px;border-radius:3px;font-family:monospace;font-size:0.9em">$1</code>')
            .replace(/\[(.+?)\]\((.+?)\)/g, '<a href="$2" target="_blank" rel="noopener" style="color:var(--accent)">$1</a>');
        const lines = raw.split('\n');
        const parts = [];
        let inUl = false, inOl = false;
        const closeList = () => {
            if (inUl) { parts.push('</ul>'); inUl = false; }
            if (inOl) { parts.push('</ol>'); inOl = false; }
        };
        lines.forEach(line => {
            if (/^### /.test(line))      { closeList(); parts.push(`<h5 style="margin:10px 0 4px;color:var(--text-primary);font-size:0.95em">${inline(line.slice(4))}</h5>`); }
            else if (/^## /.test(line))  { closeList(); parts.push(`<h4 style="margin:12px 0 5px;color:var(--text-primary)">${inline(line.slice(3))}</h4>`); }
            else if (/^# /.test(line))   { closeList(); parts.push(`<h3 style="margin:14px 0 6px;color:var(--text-primary)">${inline(line.slice(2))}</h3>`); }
            else if (/^---+$/.test(line.trim())) { closeList(); parts.push('<hr style="border:none;border-top:1px solid var(--border);margin:10px 0">'); }
            else if (/^> /.test(line))   { closeList(); parts.push(`<blockquote style="border-left:3px solid var(--accent);margin:5px 0;padding:4px 10px;color:var(--text-secondary);background:rgba(255,255,255,0.03);border-radius:0 4px 4px 0">${inline(line.slice(2))}</blockquote>`); }
            else if (/^[-*+] /.test(line)) {
                if (!inUl) { closeList(); parts.push('<ul style="margin:5px 0;padding-left:18px">'); inUl = true; }
                parts.push(`<li style="margin:2px 0;color:var(--text-secondary)">${inline(line.slice(2))}</li>`);
            }
            else if (/^\d+\. /.test(line)) {
                if (!inOl) { closeList(); parts.push('<ol style="margin:5px 0;padding-left:18px">'); inOl = true; }
                parts.push(`<li style="margin:2px 0;color:var(--text-secondary)">${inline(line.replace(/^\d+\. /,''))}</li>`);
            }
            else if (line.trim() === '') { closeList(); parts.push('<div style="height:6px"></div>'); }
            else { closeList(); parts.push(`<p style="margin:3px 0;color:var(--text-secondary)">${inline(line)}</p>`); }
        });
        closeList();
        return parts.join('');
    },

    /** Price stats bar: last date, last close, day change, refresh time */
    _buildPriceStatsBar(data) {
        const prices = data.close || [];
        const dates  = data.dates  || [];
        if (prices.length === 0) return '';
        const lastClose = prices[prices.length - 1];
        const prevClose = prices.length > 1 ? prices[prices.length - 2] : null;
        const lastDate  = dates[dates.length - 1] || '';
        const change    = (lastClose != null && prevClose != null) ? lastClose - prevClose : null;
        const changePct = (change != null && prevClose) ? change / prevClose * 100 : null;
        const fmtP = p  => p != null ? Tables.addSeparator(p.toFixed(2)) : 'N/A';
        const changeHtml = change != null
            ? `<span class="${change >= 0 ? 'val-positive' : 'val-negative'}" style="font-size:0.95em">${change >= 0 ? '+' : ''}${fmtP(change)} (${changePct >= 0 ? '+' : ''}${changePct.toFixed(2)}%)</span>`
            : '';
        const now = new Date();
        const timeStr = now.toLocaleTimeString('id-ID', { hour:'2-digit', minute:'2-digit', second:'2-digit' });
        return `<div style="display:flex;justify-content:space-between;align-items:center;padding:5px 10px;background:var(--bg-input);border-radius:var(--radius);margin-bottom:6px;font-size:0.82em;flex-wrap:wrap;gap:4px">
            <div style="display:flex;gap:14px;align-items:center">
                <span style="color:var(--text-muted)">${lastDate}</span>
                <span style="font-weight:700;font-size:1.05em;color:var(--text-primary)">${fmtP(lastClose)}</span>
                ${changeHtml}
            </div>
            <span style="color:var(--text-muted);font-size:0.9em">Diperbarui ${timeStr}</span>
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
            chartDiv.innerHTML = this._buildPriceStatsBar(data) + '<div id="detail-chart-container"></div>';
            Charts.priceChart('detail-chart-container', data, data.indicators || {});

            // Populate technical signals card
            const sigDiv = document.getElementById('tech-signals-container');
            if (sigDiv) {
                sigDiv.innerHTML = this._renderTechSignals(data);
            }
        } catch (e) {
            chartDiv.innerHTML = `<p class="val-negative">Error: ${e.message}</p>`;
        }
    },

    // --- Detail ---
    _detailIndicators: ['SMA20', 'SMA50'],
    _detailPeriod: '1y',
    _detailTab: 'overview',
    _expandedRatioCards: new Set(),
    _pendingModelTicker: null,
    _lastCurrentPrice: null,
    _lastDetailRatios: null,
    _lastDetailRatioSuffixes: null,

    // Q1: 4-tab switcher for detail page
    _switchDetailTab(tab) {
        this._detailTab = tab;
        ['overview', 'financials', 'trends', 'valuation'].forEach(t => {
            const panel = document.getElementById(`detail-tab-${t}`);
            const btn = document.getElementById(`dtab-btn-${t}`);
            if (panel) panel.classList.toggle('hidden', t !== tab);
            if (btn) btn.className = `btn btn-sm ${t === tab ? 'btn-primary' : 'btn-secondary'}`;
        });
    },

    // Q2: Ratio card with N/A filtering
    _renderRatioCardHtml(cardId, title, entries, ratioSuffixes) {
        const isExpanded = this._expandedRatioCards.has(cardId);
        const isNA = (v) => v == null || v === undefined || v === 'N/A' || v === '—' || v === '' || !isFinite(parseFloat(v));
        const validEntries = entries.filter(([, v]) => !isNA(v));
        const hiddenCount = entries.length - validEntries.length;
        const displayEntries = isExpanded ? entries : validEntries;
        const fmtRatio = (k, v) => {
            if (isNA(v)) return '<span style="color:var(--text-muted)">N/A</span>';
            const n = parseFloat(v);
            const suffix = ratioSuffixes[k] || '';
            const neg = n < 0;
            const formatted = Tables.addSeparator(Math.abs(n).toFixed(2));
            return `<span style="${neg ? 'color:var(--red)' : ''}">${neg ? '-' : ''}${formatted}${suffix}</span>`;
        };
        let html = `<div class="card"><div class="card-title">${title}</div>`;
        if (displayEntries.length === 0) {
            html += '<p style="color:var(--text-muted);font-size:0.85em">No data available</p>';
        } else {
            html += '<table class="data-table"><tbody>';
            displayEntries.forEach(([k, v]) => {
                html += `<tr><td style="color:var(--text-muted);font-size:0.85em">${k}</td><td style="font-weight:600;text-align:right">${fmtRatio(k, v)}</td></tr>`;
            });
            html += '</tbody></table>';
        }
        if (hiddenCount > 0) {
            html += `<button class="btn btn-sm btn-secondary" style="margin-top:8px;width:100%;font-size:0.78em"
                onclick="App._toggleRatioCard('${cardId}')">
                ${isExpanded ? 'Hide N/A fields' : `Show ${hiddenCount} N/A field${hiddenCount !== 1 ? 's' : ''}`}
            </button>`;
        }
        return html + '</div>';
    },

    _buildRatioCardsHtml(ratios, ratioSuffixes) {
        const cats = {
            'Valuation': ['PER', 'PBV', 'EV/EBITDA', 'PEG'],
            'Profitability': ['ROE', 'ROA', 'NPM', 'GPM'],
            'Risk & Leverage': ['Beta', 'DER', 'Current Ratio', 'Dividend Yield'],
        };
        const cards = Object.entries(cats).map(([cat, keys]) => {
            const entries = keys.map(k => [k, ratios[k] !== undefined ? ratios[k] : null]);
            return this._renderRatioCardHtml(cat, cat, entries, ratioSuffixes);
        });
        return `<div class="grid grid-3">${cards.join('')}</div>`;
    },

    _toggleRatioCard(cardId) {
        if (this._expandedRatioCards.has(cardId)) {
            this._expandedRatioCards.delete(cardId);
        } else {
            this._expandedRatioCards.add(cardId);
        }
        const container = document.getElementById('ratio-cards-container');
        if (container && this._lastDetailRatios) {
            container.innerHTML = this._buildRatioCardsHtml(this._lastDetailRatios, this._lastDetailRatioSuffixes);
        }
    },

    // Q6: Score breakdown toggle
    _toggleScoreBreakdown(type) {
        const el = document.getElementById(`score-breakdown-${type}`);
        if (el) el.classList.toggle('hidden');
    },

    // Q5: Valuation synthesis
    SECTOR_WEIGHTS: {
        'perbankan':             { dcf: 0.10, pbv: 0.55, ddm: 0.25, roe: 0.10 },
        'telekomunikasi':        { dcf: 0.40, pbv: 0.15, ddm: 0.25, roe: 0.20 },
        'energi_pertambangan':   { dcf: 0.45, pbv: 0.20, ddm: 0.15, roe: 0.20 },
        'consumer_goods':        { dcf: 0.35, pbv: 0.25, ddm: 0.20, roe: 0.20 },
        'manufaktur':            { dcf: 0.40, pbv: 0.25, ddm: 0.15, roe: 0.20 },
        'properti_konstruksi':   { dcf: 0.30, pbv: 0.45, ddm: 0.10, roe: 0.15 },
        'logistik_transportasi': { dcf: 0.40, pbv: 0.20, ddm: 0.15, roe: 0.25 },
        'healthcare':            { dcf: 0.40, pbv: 0.20, ddm: 0.15, roe: 0.25 },
        'teknologi':             { dcf: 0.50, pbv: 0.15, ddm: 0.10, roe: 0.25 },
        '_default':              { dcf: 0.35, pbv: 0.25, ddm: 0.20, roe: 0.20 },
    },

    async _loadValuationSynthesis(ticker) {
        const el = document.getElementById('valuation-synthesis');
        if (!el) return;
        try {
            const [ind, dcfRes, pbvRes, ddmRes, roeRes] = await Promise.all([
                this.api('/api/industry', { method: 'POST', body: { ticker } }).catch(() => null),
                this.api('/api/model/dcf', { method: 'POST', body: { ticker, growth_rate: 0.10, terminal_growth: 0.03, wacc: 0.10, projection_years: 5 } }).catch(() => null),
                this.api('/api/model/pbv', { method: 'POST', body: { ticker, cost_of_equity: 0.10, terminal_growth: 0.05 } }).catch(() => null),
                this.api('/api/model/ddm', { method: 'POST', body: { ticker, growth_rate: 0.05, cost_of_equity: 0.10 } }).catch(() => null),
                this.api('/api/model/roe', { method: 'POST', body: { ticker, cost_of_equity: 0.10 } }).catch(() => null),
            ]);

            const industryKey = ind?.industry_key || '_default';
            const sectorLabel = ind?.label || 'General';
            const rawWeights = this.SECTOR_WEIGHTS[industryKey] || this.SECTOR_WEIGHTS['_default'];

            // Get current price from DCF result or stored value
            const cp = (dcfRes?.error ? null : dcfRes?.current_price) ?? this._lastCurrentPrice;
            if (cp != null) this._lastCurrentPrice = cp;

            const models = [
                { key: 'dcf', label: 'DCF', intrinsic: dcfRes?.error ? null : dcfRes?.intrinsic_per_share, weight: rawWeights.dcf },
                { key: 'pbv', label: 'PBV', intrinsic: pbvRes?.error ? null : pbvRes?.intrinsic_per_share, weight: rawWeights.pbv },
                { key: 'ddm', label: 'DDM', intrinsic: ddmRes?.error ? null : ddmRes?.intrinsic_per_share, weight: rawWeights.ddm },
                { key: 'roe', label: 'ROE Growth', intrinsic: roeRes?.error ? null : roeRes?.intrinsic_per_share, weight: rawWeights.roe },
            ];

            // Re-normalize weights for available models only
            const available = models.filter(m => m.intrinsic != null);
            const totalW = available.reduce((s, m) => s + m.weight, 0);
            if (totalW > 0) available.forEach(m => m.normWeight = m.weight / totalW);
            else available.forEach(m => m.normWeight = 1 / available.length);

            el.innerHTML = this._renderValuationSynthesis(models, cp, sectorLabel);
        } catch (e) {
            el.innerHTML = '';
        }
    },

    _renderValuationSynthesis(models, currentPrice, sectorLabel) {
        const available = models.filter(m => m.intrinsic != null && m.normWeight != null);
        const weightedFV = available.length > 0
            ? available.reduce((s, m) => s + m.intrinsic * m.normWeight, 0)
            : null;

        const upside = (weightedFV != null && currentPrice != null && currentPrice > 0)
            ? (weightedFV - currentPrice) / currentPrice * 100
            : null;
        const upsideHtml = upside != null ? (() => {
            const cls = upside > 5 ? 'badge-green' : upside < -5 ? 'badge-red' : 'badge-orange';
            const verdict = upside > 5 ? 'Undervalued' : upside < -5 ? 'Overvalued' : 'Fair Value';
            return `<span class="badge ${cls}" style="font-size:1em;padding:4px 12px">${upside > 0 ? '+' : ''}${upside.toFixed(1)}% ${verdict}</span>`;
        })() : '';

        let rows = models.map(m => {
            const available2 = m.intrinsic != null;
            const normW = m.normWeight != null ? `${(m.normWeight * 100).toFixed(0)}%` : '—';
            const contrib = (m.intrinsic != null && m.normWeight != null) ? Tables.addSeparator((m.intrinsic * m.normWeight).toFixed(2)) : '—';
            return `<tr style="opacity:${available2 ? 1 : 0.45}">
                <td style="font-size:0.85em">${m.label}</td>
                <td style="font-weight:600;text-align:right">${m.intrinsic != null ? Tables.addSeparator(m.intrinsic.toFixed(2)) : 'N/A'}</td>
                <td style="text-align:right;font-size:0.85em;color:var(--text-muted)">${normW}</td>
                <td style="text-align:right;font-size:0.85em">${contrib}</td>
            </tr>`;
        }).join('');

        const fvRow = weightedFV != null ? `<tr style="border-top:2px solid var(--border);font-weight:700">
            <td colspan="3">Weighted Fair Value</td>
            <td style="text-align:right;font-size:1.05em">${Tables.addSeparator(weightedFV.toFixed(2))}</td>
        </tr>` : '';

        return `<div class="card" style="border-left:3px solid var(--accent)">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:12px;flex-wrap:wrap;gap:8px">
                <div class="card-title" style="margin:0">Valuation Synthesis</div>
                ${upsideHtml}
            </div>
            <table class="data-table">
                <thead><tr><th>Model</th><th style="text-align:right">Intrinsic</th><th style="text-align:right">Weight</th><th style="text-align:right">Contribution</th></tr></thead>
                <tbody>${rows}${fvRow}</tbody>
            </table>
            ${currentPrice != null ? `<div style="display:flex;justify-content:space-between;margin-top:8px;padding-top:8px;border-top:1px solid var(--border)">
                <span style="font-size:0.82em;color:var(--text-muted)">Current Price</span>
                <span style="font-weight:600">${Tables.addSeparator(currentPrice.toFixed(2))}</span>
            </div>` : ''}
            <p style="color:var(--text-muted);font-size:0.75em;margin-top:10px">Weights auto-set for ${sectorLabel}. Adjust individual model inputs below for custom assumptions.</p>
        </div>`;
    },

    // Q8: Sensitivity heat map color helper
    _sensitivityCellColor(intrinsic, currentPrice) {
        if (currentPrice == null || currentPrice <= 0 || intrinsic == null) return { bg: '#37474f', text: '#fff' };
        const pct = (intrinsic - currentPrice) / currentPrice * 100;
        if (pct > 30)       return { bg: '#1b5e20', text: '#fff' };
        if (pct > 15)       return { bg: '#388e3c', text: '#fff' };
        if (pct > 5)        return { bg: '#81c784', text: '#333' };
        if (pct >= -5)      return { bg: '#fff176', text: '#333' };
        if (pct >= -15)     return { bg: '#e57373', text: '#fff' };
        if (pct >= -30)     return { bg: '#c62828', text: '#fff' };
        return { bg: '#7f0000', text: '#fff' };
    },

    _renderSensitivityHeatmap(result, currentPrice) {
        const { growth_labels, wacc_labels, matrix } = result;
        // Find nearest cell to current price
        let nearestI = -1, nearestJ = -1, nearestDiff = Infinity;
        if (currentPrice != null) {
            matrix.forEach((row, i) => row.forEach((val, j) => {
                if (val == null) return;
                const diff = Math.abs(val - currentPrice);
                if (diff < nearestDiff) { nearestDiff = diff; nearestI = i; nearestJ = j; }
            }));
        }

        let html = `<div style="overflow-x:auto">
            <table style="border-collapse:collapse;font-size:0.78em;width:100%">
                <thead><tr>
                    <th style="padding:4px 8px;color:var(--text-muted);font-size:0.85em">WACC \\ Growth</th>
                    ${growth_labels.map(g => `<th style="padding:4px 8px;color:var(--text-muted);font-weight:600;text-align:center">${g}</th>`).join('')}
                </tr></thead>
                <tbody>
                ${matrix.map((row, i) => `<tr>
                    <td style="padding:4px 8px;color:var(--text-muted);font-weight:600;white-space:nowrap">${wacc_labels[i]}</td>
                    ${row.map((val, j) => {
                        const { bg, text } = this._sensitivityCellColor(val, currentPrice);
                        const isNearest = (i === nearestI && j === nearestJ);
                        const outline = isNearest ? 'outline:2px solid var(--accent);outline-offset:-2px;' : '';
                        return `<td style="padding:5px 8px;background:${bg};color:${text};text-align:center;font-weight:${isNearest ? '700' : '400'};${outline}border:1px solid rgba(0,0,0,0.15)">
                            ${val != null ? Tables.addSeparator(val.toFixed(0)) : '–'}
                        </td>`;
                    }).join('')}
                </tr>`).join('')}
                </tbody>
            </table>
        </div>
        <div style="display:flex;gap:4px;margin-top:10px;flex-wrap:wrap;align-items:center">
            <span style="font-size:0.75em;color:var(--text-muted);margin-right:4px">Upside:</span>
            ${[
                { bg: '#1b5e20', text: '#fff', label: '>+30%' },
                { bg: '#388e3c', text: '#fff', label: '+15–30%' },
                { bg: '#81c784', text: '#333', label: '+5–15%' },
                { bg: '#fff176', text: '#333', label: '±5%' },
                { bg: '#e57373', text: '#fff', label: '-5–15%' },
                { bg: '#c62828', text: '#fff', label: '-15–30%' },
                { bg: '#7f0000', text: '#fff', label: '<-30%' },
            ].map(c => `<span style="background:${c.bg};color:${c.text};padding:2px 7px;border-radius:3px;font-size:0.72em;font-weight:600">${c.label}</span>`).join('')}
        </div>
        ${currentPrice != null ? `<p style="font-size:0.75em;color:var(--text-muted);margin-top:6px">Current price: ${Tables.addSeparator(currentPrice.toFixed(2))} · Highlighted cell = nearest to current price</p>` : ''}`;
        return html;
    },

    // ── Industry analysis helpers ────────────────────────────────────────────

    _fmtIndRatio(key, val) {
        if (val == null) return '<span style="color:var(--text-muted)">N/A</span>';
        const n = parseFloat(val);
        if (!isFinite(n)) return '<span style="color:var(--text-muted)">N/A</span>';
        const neg = n < 0;
        const absStr = Tables.addSeparator(Math.abs(n).toFixed(2));
        const formatted = (neg ? '-' : '') + absStr;
        if (key.includes('(%)')) return `<span style="${neg ? 'color:var(--red)' : ''}">${formatted}%</span>`;
        if (key.includes('(x)')) return `<span style="${neg ? 'color:var(--red)' : ''}">${formatted}x</span>`;
        return `<span>${formatted}</span>`;
    },

    _renderIndustryRatioTable(ratios) {
        if (!ratios) return '<p style="color:var(--text-muted);font-size:0.85em">N/A</p>';
        let html = '<table class="data-table"><tbody>';
        for (const [key, val] of Object.entries(ratios)) {
            html += `<tr>
                <td style="color:var(--text-muted);font-size:0.85em">${key}</td>
                <td style="font-weight:600;text-align:right">${this._fmtIndRatio(key, val)}</td>
            </tr>`;
        }
        return html + '</tbody></table>';
    },

    _renderValuationBand(val) {
        if (!val || !val.bands) return '<p style="color:var(--text-muted);font-size:0.85em">N/A</p>';
        const { metric, current, bands, zone } = val;
        const cur = current != null ? parseFloat(current) : null;
        const max = (cur != null && cur > bands.expensive[1]) ? cur * 1.2 : bands.expensive[1];
        const pct = v => Math.max(0, (v / max) * 100);
        const cW  = pct(bands.cheap[1] - (bands.cheap[0] || 0)).toFixed(1);
        const fW  = pct(bands.fair[1]  -  bands.fair[0]).toFixed(1);
        const eW  = pct(Math.min(bands.expensive[1], max) - bands.expensive[0]).toFixed(1);
        const ptrL = cur != null ? Math.min(97, Math.max(3, (cur / max) * 100)).toFixed(1) : null;
        const zoneColor = { cheap: '#4caf50', fair: '#ff9800', expensive: '#f44336', unknown: '#888' }[zone] || '#888';
        const zoneLabel = { cheap: 'Murah', fair: 'Wajar', expensive: 'Mahal', unknown: '–' }[zone] || zone;
        const ptrHtml = ptrL != null ? `
            <div style="position:absolute;left:${ptrL}%;top:0;transform:translateX(-50%);pointer-events:none">
                <div style="font-size:0.68em;font-weight:700;color:${zoneColor};white-space:nowrap;text-align:center;line-height:1.3">${Tables.addSeparator(cur.toFixed(2))}x</div>
                <div style="width:2px;height:20px;background:${zoneColor};margin:2px auto 0;border-radius:1px"></div>
            </div>` : '';
        return `<div style="font-size:0.78em;color:var(--text-muted);font-weight:600;margin-bottom:6px">${metric} Band</div>
            <div style="position:relative;padding-top:28px">
                ${ptrHtml}
                <div style="display:flex;height:18px;border-radius:3px;overflow:hidden;font-size:0.62em">
                    <div style="width:${cW}%;background:rgba(76,175,80,0.3);display:flex;align-items:center;justify-content:center;color:#aaa;min-width:0">Murah</div>
                    <div style="width:${fW}%;background:rgba(255,152,0,0.3);display:flex;align-items:center;justify-content:center;color:#aaa;min-width:0">Wajar</div>
                    <div style="width:${eW}%;background:rgba(244,67,54,0.25);display:flex;align-items:center;justify-content:center;color:#aaa;min-width:0">Mahal</div>
                </div>
            </div>
            <div style="display:flex;justify-content:space-between;font-size:0.68em;color:var(--text-muted);margin-top:3px">
                <span>0</span><span>${bands.cheap[1]}x</span><span>${bands.fair[1]}x</span><span>${parseFloat(max).toFixed(1)}x</span>
            </div>
            <div style="margin-top:8px;font-size:0.82em">
                Zona: <span style="font-weight:700;color:${zoneColor}">${zoneLabel}</span>
                ${cur != null ? `<span style="color:var(--text-muted)"> (${Tables.addSeparator(cur.toFixed(2))}x)</span>` : ''}
            </div>`;
    },

    _renderThesisGrid(thesis) {
        if (!thesis) return '';
        const items = [
            { key: 'bull', label: 'Bull Case', icon: '📈', color: '#4caf50' },
            { key: 'base', label: 'Base Case', icon: '📊', color: '#2196f3' },
            { key: 'bear', label: 'Bear Case', icon: '📉', color: '#f44336' },
        ];
        const getText = (v) => {
            if (!v) return '–';
            if (typeof v === 'object' && (v.en || v.id)) {
                return `<div style="margin-bottom:5px">${v.en || ''}</div>`
                     + `<div style="color:var(--text-muted);font-style:italic;border-top:1px solid var(--border);padding-top:5px;margin-top:2px">${v.id || ''}</div>`;
            }
            return v;
        };
        return `<div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Investment Thesis</div>
            <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:10px">
                ${items.map(({ key, label, icon, color }) => `
                    <div style="background:var(--bg-input);border:1px solid var(--border);border-radius:6px;padding:10px;border-top:3px solid ${color}">
                        <div style="font-size:0.78em;font-weight:700;color:${color};margin-bottom:6px">${icon} ${label}</div>
                        <div style="font-size:0.78em;color:var(--text-secondary);line-height:1.5">${getText(thesis[key])}</div>
                    </div>
                `).join('')}
            </div>`;
    },

    _renderPeerLinks(peers, currentTicker) {
        if (!peers?.tickers?.length) return '';
        const { tickers, metrics } = peers;
        return `<div style="font-size:0.8em;color:var(--text-muted);margin-bottom:6px">Key metrics: ${(metrics || []).join(', ')}</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px">
                ${tickers.map(t => `
                    <button class="btn btn-sm btn-secondary" style="font-size:0.78em"
                        onclick="App._triggerH2H('${currentTicker}','${t}')">
                        ${t} <span style="opacity:0.6">H2H →</span>
                    </button>
                `).join('')}
            </div>`;
    },

    _renderIndustryCard(ctx) {
        if (!ctx || ctx.error) return '';
        const { icon, label, sector, industry, specific_ratios, valuation, peers, thesis } = ctx;
        const header = `<div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
            <span style="font-size:1.8em;line-height:1">${icon}</span>
            <div>
                <div style="font-weight:700;font-size:1.05em">${label}</div>
                <div style="font-size:0.8em;color:var(--text-muted)">${sector || ''}${industry && industry !== 'N/A' ? ' · ' + industry : ''}</div>
            </div>
        </div>`;
        return `<div class="card">
            <div class="card-title">Industry Analysis</div>
            ${header}
            <div class="grid grid-2" style="gap:16px;margin-bottom:16px">
                <div>
                    <div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Key Industry Ratios</div>
                    ${this._renderIndustryRatioTable(specific_ratios)}
                </div>
                <div>
                    <div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Valuation Band</div>
                    ${this._renderValuationBand(valuation)}
                    ${peers?.tickers?.length ? `<div style="margin-top:14px">
                        <div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Peer Comparison</div>
                        ${this._renderPeerLinks(peers, ctx.ticker)}
                    </div>` : ''}
                </div>
            </div>
            ${this._renderThesisGrid(thesis)}
        </div>`;
    },

    _renderIndustryMini(ctx) {
        const { icon, label, specific_ratios, valuation, thesis } = ctx;
        return `<div style="font-size:1.0em;margin-bottom:10px">${icon} <span style="font-weight:700">${label}</span></div>
            ${this._renderIndustryRatioTable(specific_ratios)}
            <div style="margin-top:12px">${this._renderValuationBand(valuation)}</div>
            <div style="margin-top:14px">${this._renderThesisGrid(thesis)}</div>`;
    },

    _renderH2HIndustry(ctxA, ctxB, tA, tB) {
        if (!ctxA && !ctxB) return '';
        const lowerBetterKeys = ['PBV (x)', 'PER (x)', 'EV/EBITDA (x)', 'DER (x)',
                                  'Net Debt/EBITDA (x)', 'CapEx/Revenue (%)'];
        const sameIndustry = ctxA && ctxB && ctxA.industry_key === ctxB.industry_key;
        let html = '<div class="card"><div class="card-title">Industry Analysis</div>';
        if (sameIndustry) {
            html += `<div style="display:flex;align-items:center;gap:8px;margin-bottom:12px">
                <span style="font-size:1.4em">${ctxA.icon}</span>
                <span style="font-weight:700">${ctxA.label}</span>
                <span style="font-size:0.8em;color:var(--text-muted)">${ctxA.sector || ''}</span>
            </div>`;
            // Side-by-side ratio comparison table
            const rA = ctxA.specific_ratios || {};
            const rB = ctxB.specific_ratios || {};
            const allKeys = [...new Set([...Object.keys(rA), ...Object.keys(rB)])];
            html += `<div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Key Industry Ratios</div>`;
            html += `<table class="data-table" style="margin-bottom:16px"><thead><tr><th>Metric</th><th>${tA}</th><th>${tB}</th><th>Winner</th></tr></thead><tbody>`;
            allKeys.forEach(key => {
                const vA = rA[key] != null ? parseFloat(rA[key]) : null;
                const vB = rB[key] != null ? parseFloat(rB[key]) : null;
                const lB = lowerBetterKeys.includes(key);
                let clsA = '', clsB = '', winner = '—';
                if (vA != null && vB != null && isFinite(vA) && isFinite(vB) && vA !== vB) {
                    const aWins = lB ? vA < vB : vA > vB;
                    clsA = aWins ? 'badge-green' : 'badge-red';
                    clsB = aWins ? 'badge-red' : 'badge-green';
                    winner = aWins ? tA : tB;
                }
                html += `<tr>
                    <td style="font-size:0.85em;color:var(--text-muted)">${key}</td>
                    <td><span class="${clsA ? 'badge ' + clsA : ''}">${this._fmtIndRatio(key, vA)}</span></td>
                    <td><span class="${clsB ? 'badge ' + clsB : ''}">${this._fmtIndRatio(key, vB)}</span></td>
                    <td style="font-size:0.8em;color:var(--text-muted)">${winner}</td>
                </tr>`;
            });
            html += '</tbody></table>';
            // Valuation bands side by side
            html += `<div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);text-transform:uppercase;letter-spacing:0.05em;margin-bottom:8px">Valuation Band</div>`;
            html += `<div class="grid grid-2" style="gap:16px;margin-bottom:16px">
                <div><div style="font-size:0.8em;font-weight:600;color:var(--accent);margin-bottom:6px">${tA}</div>${this._renderValuationBand(ctxA.valuation)}</div>
                <div><div style="font-size:0.8em;font-weight:600;color:var(--accent);margin-bottom:6px">${tB}</div>${this._renderValuationBand(ctxB.valuation)}</div>
            </div>`;
            // Shared thesis
            html += this._renderThesisGrid(ctxA.thesis);
        } else {
            html += `<div class="grid grid-2" style="gap:16px">
                <div>${ctxA ? this._renderIndustryMini(ctxA) : '<p style="color:var(--text-muted)">N/A</p>'}</div>
                <div>${ctxB ? this._renderIndustryMini(ctxB) : '<p style="color:var(--text-muted)">N/A</p>'}</div>
            </div>`;
        }
        return html + '</div>';
    },

    async _loadIndustryCard(ticker) {
        const el = document.getElementById('industry-card-container');
        if (!el) return;
        try {
            const ctx = await this.api('/api/industry', { method: 'POST', body: { ticker } });
            const current = document.getElementById('industry-card-container');
            if (current) current.innerHTML = this._renderIndustryCard(ctx);
        } catch (_) {
            const el2 = document.getElementById('industry-card-container');
            if (el2) el2.innerHTML = '';
        }
    },

    async renderDetail(ticker) {
        if (!ticker) {
            this.render('<div class="empty-state"><h3>Enter a ticker to analyze</h3></div>');
            return;
        }
        this.renderSkeleton('detail');
        this.showLoading();
        // Reset detail tab on new ticker
        this._detailTab = 'overview';
        this._expandedRatioCards = new Set();
        try {
            const [fin, trends] = await Promise.all([
                this.api('/api/financials', { method: 'POST', body: { ticker } }),
                this.api('/api/trends', { method: 'POST', body: { ticker } }),
            ]);

            // Fetch scores async (non-blocking — fills in after main render)
            const scoresSkeletonHtml = '<div class="card"><div class="card-title">Composite Scores</div><div class="skeleton skeleton-card" style="height:80px"></div></div>';
            this.api('/api/scores', { method: 'POST', body: { ticker } }).then(sc => {
                const el = document.getElementById('score-gauges-container');
                if (el) el.innerHTML = this._renderScoreGauges(sc);
            }).catch(() => {
                const el = document.getElementById('score-gauges-container');
                if (el) el.innerHTML = '';
            });

            const fv = Tables.formatValue;
            const ps = fin.price_summary || {};
            const hl = fin.highlights || {};
            const ccy = ps.currency || '';

            // Q2: Store ratios for N/A filter re-render
            const ratioSuffixes = {
                'ROE': '%', 'ROA': '%', 'NPM': '%', 'GPM': '%', 'Dividend Yield': '%',
                'PER': 'x', 'PBV': 'x', 'EV/EBITDA': 'x', 'PEG': 'x', 'DER': 'x', 'Current Ratio': 'x',
            };
            this._lastDetailRatios = fin.ratios;
            this._lastDetailRatioSuffixes = ratioSuffixes;

            // Q7: Price summary with H2H button
            const priceSummaryHtml = `
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px">
                        <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
                            <span style="font-size:2em;font-weight:700">${Tables.formatPrice(ps.current_price, ccy)}</span>
                            <button class="btn btn-sm btn-secondary" onclick="App._triggerH2H('${ticker}','')">⇄ Compare H2H</button>
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

            // Highlights
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

            // Q2: Ratio cards (N/A filtered in overview)
            const ratioCardsHtml = this._buildRatioCardsHtml(fin.ratios, ratioSuffixes);

            // Full ratio table for Financials tab (all metrics, unfiltered)
            const allRatioSections = {
                'Valuation': ['PER', 'PBV', 'EV/EBITDA', 'PEG'],
                'Profitability': ['ROE', 'ROA', 'NPM', 'GPM'],
                'Risk & Leverage': ['Beta', 'DER', 'Current Ratio', 'Dividend Yield'],
            };
            let fullRatioHtml = '<div class="card" style="margin-top:0"><div class="card-title">All Ratios</div><div class="grid grid-3">';
            for (const [cat, keys] of Object.entries(allRatioSections)) {
                const rawForCat = {};
                keys.forEach(k => { if (fin.ratios[k] !== undefined) rawForCat[k] = fin.ratios[k]; });
                fullRatioHtml += `<div><div style="font-size:0.82em;font-weight:600;color:var(--text-secondary);margin-bottom:6px">${cat}</div>${Tables.keyValueRatios(rawForCat, ratioSuffixes)}</div>`;
            }
            fullRatioHtml += '</div></div>';

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
                    <div style="display:flex;gap:8px;margin-bottom:12px;flex-wrap:wrap">
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

            // Price chart section (for Trends tab)
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

            // Recommendation box
            const recs = this._computeRecommendations(fin, trends);
            const recommendationHtml = this._renderRecommendationBox(recs);

            // Q1: 4-tab layout
            this.render(`
                <div class="section-header">
                    <h2>${fin.name || ticker} <span style="color:var(--text-muted);font-weight:400">(${fin.ticker})</span></h2>
                    <div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">
                        <span class="badge badge-blue">${fin.sector}</span>
                        <span class="badge badge-purple">${fin.industry}</span>
                        <button class="btn btn-sm btn-secondary" id="btn-save-snapshot">Save Data</button>
                        <button class="btn btn-sm btn-secondary" id="btn-detail-screenshot">Screenshot</button>
                    </div>
                </div>

                <div style="display:flex;gap:4px;margin-bottom:16px;flex-wrap:wrap">
                    <button id="dtab-btn-overview" class="btn btn-sm btn-primary" onclick="App._switchDetailTab('overview')">Overview</button>
                    <button id="dtab-btn-financials" class="btn btn-sm btn-secondary" onclick="App._switchDetailTab('financials')">Financials</button>
                    <button id="dtab-btn-trends" class="btn btn-sm btn-secondary" onclick="App._switchDetailTab('trends')">Trends</button>
                    <button id="dtab-btn-valuation" class="btn btn-sm btn-secondary" onclick="App._switchDetailTab('valuation')">Valuation</button>
                </div>

                <div id="detail-tab-overview">
                    ${priceSummaryHtml}
                    ${recommendationHtml}
                    <div id="score-gauges-container">${scoresSkeletonHtml}</div>
                    ${highlightsHtml}
                    <div id="ratio-cards-container">${ratioCardsHtml}</div>
                    ${anomalyHtml}
                </div>

                <div id="detail-tab-financials" class="hidden">
                    ${stmtTabs}
                    ${fullRatioHtml}
                </div>

                <div id="detail-tab-trends" class="hidden">
                    ${priceChartHtml}
                    <div id="tech-signals-container"></div>
                    ${trendChartsHtml}
                </div>

                <div id="detail-tab-valuation" class="hidden">
                    <div id="industry-card-container"><div class="skeleton skeleton-card" style="height:200px"></div></div>
                    <div class="card" style="text-align:center;padding:24px">
                        <p style="color:var(--text-muted);font-size:0.9em;margin-bottom:12px">Run DCF, PBV, DDM, and ROE Growth models for ${ticker}</p>
                        <button class="btn btn-primary" onclick="App._pendingModelTicker='${ticker}'; Router.navigate('#model/${ticker}')">Open Valuation Models →</button>
                    </div>
                </div>
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

            // Load detail price chart and industry card
            this._loadDetailChart(ticker);
            this._loadIndustryCard(ticker);

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

    _compareMode: 'multi',
    _pendingCompareTickers: null,
    _pendingH2HTickers: null,

    _compareWatchlist(tickersCsv) {
        this._pendingCompareTickers = tickersCsv;
        Router.navigate('#compare');
    },

    _triggerH2H(tA, tB) {
        this._compareMode = 'h2h';
        this._pendingH2HTickers = [tA, tB];
        Router.navigate('#compare');
    },

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
            <div class="section-header">
                <h2>Compare Tickers</h2>
                <button class="btn btn-sm btn-secondary" onclick="App.screenshotToClipboard()">Screenshot</button>
            </div>
            <div style="display:flex;gap:4px;margin-bottom:16px">
                <button class="btn btn-sm ${this._compareMode === 'multi' ? 'btn-primary' : 'btn-secondary'}" id="tab-multi" onclick="App._switchCompareTab('multi')">Multi Compare</button>
                <button class="btn btn-sm ${this._compareMode === 'h2h' ? 'btn-primary' : 'btn-secondary'}" id="tab-h2h" onclick="App._switchCompareTab('h2h')">Head to Head</button>
            </div>
            <div id="compare-tab-multi" ${this._compareMode !== 'multi' ? 'class="hidden"' : ''}>
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
            </div>
            <div id="compare-tab-h2h" ${this._compareMode !== 'h2h' ? 'class="hidden"' : ''}>
                <div class="card">
                    <div class="grid grid-2" style="gap:12px;margin-bottom:12px">
                        <div class="form-group" style="margin:0">
                            <label>Ticker A</label>
                            <input type="text" id="h2h-ticker-a" placeholder="BBCA.JK" />
                        </div>
                        <div class="form-group" style="margin:0">
                            <label>Ticker B</label>
                            <input type="text" id="h2h-ticker-b" placeholder="BBRI.JK" />
                        </div>
                    </div>
                    <button class="btn btn-primary" id="btn-h2h">Compare Head to Head</button>
                </div>
                <div id="h2h-results"></div>
            </div>
        `);

        document.getElementById('btn-compare').onclick = () => this._runCompare();
        document.getElementById('compare-tickers').addEventListener('keydown', e => {
            if (e.key === 'Enter') this._runCompare();
        });
        document.getElementById('btn-h2h').onclick = () => this._runH2H();

        // Auto-fill + run compare if triggered from watchlist
        if (this._pendingCompareTickers) {
            const pending = this._pendingCompareTickers;
            this._pendingCompareTickers = null;
            document.getElementById('compare-tickers').value = pending.replace(/,/g, ', ');
            setTimeout(() => this._runCompare(), 50);
        }

        // Auto-fill + run H2H if triggered from peer links
        if (this._pendingH2HTickers) {
            const [pA, pB] = this._pendingH2HTickers;
            this._pendingH2HTickers = null;
            this._switchCompareTab('h2h');
            document.getElementById('h2h-ticker-a').value = pA;
            document.getElementById('h2h-ticker-b').value = pB;
            setTimeout(() => this._runH2H(), 50);
        }
    },

    _switchCompareTab(mode) {
        this._compareMode = mode;
        document.getElementById('compare-tab-multi').classList.toggle('hidden', mode !== 'multi');
        document.getElementById('compare-tab-h2h').classList.toggle('hidden', mode !== 'h2h');
        document.getElementById('tab-multi').className = `btn btn-sm ${mode === 'multi' ? 'btn-primary' : 'btn-secondary'}`;
        document.getElementById('tab-h2h').className = `btn btn-sm ${mode === 'h2h' ? 'btn-primary' : 'btn-secondary'}`;
    },

    async _runH2H() {
        const tA = (document.getElementById('h2h-ticker-a')?.value || '').trim().toUpperCase();
        const tB = (document.getElementById('h2h-ticker-b')?.value || '').trim().toUpperCase();
        if (!tA || !tB) { this.toast('Enter two tickers', 'error'); return; }

        const resultsDiv = document.getElementById('h2h-results');
        resultsDiv.innerHTML = '<div class="skeleton skeleton-card"></div>';
        this.showLoading();

        try {
            const [compareRes, scoresA, scoresB, industryA, industryB] = await Promise.all([
                this.api('/api/compare', { method: 'POST', body: { tickers: [tA, tB], categories: ['valuation', 'profitability', 'risk', 'market'] } }),
                this.api('/api/scores', { method: 'POST', body: { ticker: tA } }),
                this.api('/api/scores', { method: 'POST', body: { ticker: tB } }),
                this.api('/api/industry', { method: 'POST', body: { ticker: tA } }).catch(() => null),
                this.api('/api/industry', { method: 'POST', body: { ticker: tB } }).catch(() => null),
            ]);

            const _ratioSignal = (metric, vA, vB) => {
                const lowerBetter = ['PER', 'PBV', 'EV/EBITDA', 'PEG', 'DER', 'Beta'].includes(metric);
                if (vA == null || vB == null || !isFinite(vA) || !isFinite(vB)) return ['', ''];
                if (vA === vB) return ['', ''];
                const aWins = lowerBetter ? vA < vB : vA > vB;
                return aWins ? ['badge-green', 'badge-red'] : ['badge-red', 'badge-green'];
            };

            // Score gauges side by side
            const gaugeRow = (label, sA, sB) => {
                const fmt = (s) => s != null ? s.toFixed(1) : 'N/A';
                const colorFor = (s) => s == null ? '#888' : s >= 70 ? '#4caf50' : s >= 50 ? '#ff9800' : '#f44336';
                const bar = (s, c) => `<div style="height:6px;background:var(--bg-input);border-radius:3px;overflow:hidden;margin-top:3px"><div style="height:100%;width:${s == null ? 0 : Math.max(0,Math.min(100,s))}%;background:${c};border-radius:3px"></div></div>`;
                const cA = colorFor(sA), cB = colorFor(sB);
                return `<tr>
                    <td style="font-size:0.82em;color:var(--text-muted)">${label}</td>
                    <td><span style="font-weight:700;color:${cA}">${fmt(sA)}</span>${bar(sA, cA)}</td>
                    <td><span style="font-weight:700;color:${cB}">${fmt(sB)}</span>${bar(sB, cB)}</td>
                </tr>`;
            };

            const recBadge = (rec) => {
                if (!rec) return 'N/A';
                const cls = { 'Strong Buy': 'badge-green', 'Buy': 'badge-green', 'Hold': 'badge-orange', 'Avoid': 'badge-red' }[rec] || 'badge-blue';
                return `<span class="badge ${cls}">${rec}</span>`;
            };

            const scoreCard = `<div class="card">
                <div class="card-title">Score Comparison</div>
                <table class="data-table"><thead><tr><th></th><th>${tA}</th><th>${tB}</th></tr></thead><tbody>
                    <tr><td style="font-size:0.82em;color:var(--text-muted)">Recommendation</td><td>${recBadge(scoresA.recommendation)}</td><td>${recBadge(scoresB.recommendation)}</td></tr>
                    ${gaugeRow('Quality', scoresA.quality_score, scoresB.quality_score)}
                    ${gaugeRow('Valuation', scoresA.valuation_score, scoresB.valuation_score)}
                    ${gaugeRow('Risk', scoresA.risk_score, scoresB.risk_score)}
                    ${gaugeRow('Composite', scoresA.composite_score, scoresB.composite_score)}
                </tbody></table>
            </div>`;

            // Metrics comparison table
            const metricsHtml = '<div class="card">' + (() => {
                const largeMets = ['Market Cap'];
                const pctMets   = ['ROE', 'ROA', 'NPM', 'GPM', 'Dividend Yield'];
                const ratioMets = ['PER', 'PBV', 'EV/EBITDA', 'PEG', 'DER', 'Current Ratio', 'Beta'];
                const fmtMetric = (metric, v, ccy) => {
                    if (v == null || !isFinite(v)) return 'N/A';
                    if (largeMets.includes(metric))  return Tables.formatValue(v, true, ccy);
                    if (metric === 'Current Price')  return Tables.formatPrice(v, ccy || 'IDR');
                    if (pctMets.includes(metric))    return Tables.formatRatio(v, '%');
                    if (ratioMets.includes(metric))  return Tables.formatRatio(v, 'x');
                    return Tables.formatValue(v, false, ccy);
                };
                let html = `<table class="data-table"><thead><tr><th>Metric</th><th>${tA}</th><th>${tB}</th><th>Winner</th></tr></thead><tbody>`;
                compareRes.metrics.forEach(m => {
                    const dA   = compareRes.data[tA]?.metrics?.[m];
                    const dB   = compareRes.data[tB]?.metrics?.[m];
                    const ccyA = compareRes.data[tA]?.currency || '';
                    const ccyB = compareRes.data[tB]?.currency || '';
                    const [clsA, clsB] = _ratioSignal(m, dA, dB);
                    const winner = clsA === 'badge-green' ? tA : clsB === 'badge-green' ? tB : '—';
                    html += `<tr><td>${m}</td><td><span class="${clsA ? 'badge ' + clsA : ''}">${fmtMetric(m, dA, ccyA)}</span></td><td><span class="${clsB ? 'badge ' + clsB : ''}">${fmtMetric(m, dB, ccyB)}</span></td><td style="font-size:0.8em;color:var(--text-muted)">${winner}</td></tr>`;
                });
                html += '</tbody></table>';
                return html;
            })() + '</div>';

            // Verdict
            const scoreWinner = (sA, sB, label) => {
                if (sA == null && sB == null) return null;
                if (sA == null) return `${tB} leads on ${label}`;
                if (sB == null) return `${tA} leads on ${label}`;
                if (sA > sB) return `${tA} leads on ${label} (${sA.toFixed(1)} vs ${sB.toFixed(1)})`;
                if (sB > sA) return `${tB} leads on ${label} (${sB.toFixed(1)} vs ${sA.toFixed(1)})`;
                return `Tied on ${label}`;
            };
            const verdictLines = [
                scoreWinner(scoresA.quality_score, scoresB.quality_score, 'Quality'),
                scoreWinner(scoresA.valuation_score, scoresB.valuation_score, 'Valuation'),
                scoreWinner(scoresA.risk_score, scoresB.risk_score, 'Risk'),
            ].filter(Boolean);
            const overallWinner = (scoresA.composite_score ?? 0) > (scoresB.composite_score ?? 0) ? tA : tB;
            const verdictHtml = `<div class="card" style="border-left:3px solid var(--accent)">
                <div class="card-title">H2H Verdict</div>
                <p style="font-size:0.9em;color:var(--text-secondary);margin-bottom:8px"><b>${overallWinner}</b> wins overall on composite score.</p>
                <ul style="list-style:none;padding:0;margin:0">${verdictLines.map(l => `<li style="font-size:0.85em;color:var(--text-secondary);padding:3px 0;border-bottom:1px solid var(--border)">▸ ${l}</li>`).join('')}</ul>
            </div>`;

            const industryHtml = this._renderH2HIndustry(industryA, industryB, tA, tB);
            resultsDiv.innerHTML = verdictHtml + scoreCard + metricsHtml + industryHtml;
        } catch (e) {
            resultsDiv.innerHTML = `<div class="card"><p class="val-negative">Error: ${e.message}</p></div>`;
        }
        this.hideLoading();
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

            const narrativeHtml = this._generateCompareSummary(result);

            document.getElementById('compare-results').innerHTML =
                narrativeHtml + summaryHtml + tableHtml + chartsHtml + radarHtml + exportHtml;

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

    _generateCompareSummary(result) {
        const tickers = result.tickers;
        const data = result.data;

        // Returns {ticker, value} for best performer on a metric
        const best = (metric, lowerIsBetter = false) => {
            let bestTicker = null, bestVal = null;
            tickers.forEach(t => {
                const v = data[t]?.metrics?.[metric];
                if (v == null || !isFinite(v)) return;
                if (bestVal === null || (lowerIsBetter ? v < bestVal : v > bestVal)) {
                    bestVal = v; bestTicker = t;
                }
            });
            return { ticker: bestTicker, value: bestVal };
        };

        const fmt = (v, dec = 1) => v != null ? v.toFixed(dec) : 'N/A';
        const lines = [];

        // Valuation
        const cheapPER = best('PER', true);
        const cheapPBV = best('PBV', true);
        if (cheapPER.ticker) lines.push(`<b>${cheapPER.ticker}</b> trades at the lowest P/E (${fmt(cheapPER.value)}x) — cheapest on earnings basis.`);
        if (cheapPBV.ticker) lines.push(`<b>${cheapPBV.ticker}</b> has the lowest P/BV (${fmt(cheapPBV.value, 2)}x) — most attractive on book value.`);

        // Profitability
        const topROE = best('ROE');
        const topNPM = best('NPM');
        const topROA = best('ROA');
        if (topROE.ticker) lines.push(`<b>${topROE.ticker}</b> leads on ROE (${fmt(topROE.value)}%) — generates the most return from shareholders' equity.`);
        if (topNPM.ticker) lines.push(`<b>${topNPM.ticker}</b> has the highest net margin (${fmt(topNPM.value)}%) — retains the most profit per revenue dollar.`);
        if (topROA.ticker && topROA.ticker !== topROE.ticker) lines.push(`<b>${topROA.ticker}</b> leads on ROA (${fmt(topROA.value)}%) — best at converting assets into profit.`);

        // Risk
        const lowBeta = best('Beta', true);
        const lowDER  = best('DER', true);
        if (lowBeta.ticker && Math.abs(lowBeta.value) < 2) lines.push(`<b>${lowBeta.ticker}</b> shows the lowest beta (β ${fmt(lowBeta.value, 2)}) — least correlated with market swings.`);
        if (lowDER.ticker) lines.push(`<b>${lowDER.ticker}</b> carries the least leverage (DER ${fmt(lowDER.value, 2)}) — most conservative balance sheet.`);

        // Dividend
        const topDiv = best('Dividend Yield');
        if (topDiv.ticker && topDiv.value > 0) lines.push(`<b>${topDiv.ticker}</b> offers the highest dividend yield (${fmt(topDiv.value, 2)}%) — best for income investors.`);

        // Key metrics to watch
        const watchpoints = [];
        tickers.forEach(t => {
            const m = data[t]?.metrics;
            if (!m) return;
            if (m.PEG != null && isFinite(m.PEG) && m.PEG > 3)
                watchpoints.push(`${t} PEG ratio is elevated (${fmt(m.PEG)}x) — growth may already be priced into the stock.`);
            if (m.DER != null && isFinite(m.DER) && m.DER > 1.5)
                watchpoints.push(`${t} carries high leverage (DER ${fmt(m.DER, 2)}) — monitor debt servicing capacity.`);
            if (m.ROE != null && isFinite(m.ROE) && m.ROE < 8)
                watchpoints.push(`${t} ROE is below 8% — equity returns are relatively weak, worth investigating why.`);
            if (m.NPM != null && isFinite(m.NPM) && m.NPM < 5)
                watchpoints.push(`${t} net margin below 5% — thin profitability leaves little buffer for cost shocks.`);
        });

        // Null metric note
        const allNull = result.metrics.filter(m => tickers.every(t => data[t]?.metrics?.[m] == null));
        if (allNull.length > 0)
            watchpoints.push(`Metrics unavailable for all tickers: <i>${allNull.join(', ')}</i> — may be sector-specific (e.g. banks don't report GPM or EV/EBITDA).`);

        // Sector context
        const sectors = [...new Set(tickers.map(t => data[t]?.sector).filter(Boolean))];
        const sectorNote = sectors.length === 1
            ? `All tickers are in the <b>${sectors[0]}</b> sector — ratios are directly comparable.`
            : `Tickers span <b>${sectors.join(' / ')}</b> — exercise caution when comparing ratios cross-sector, as accounting treatment and capital structure norms differ significantly.`;

        return `
            <div class="card" style="border-left:3px solid var(--accent);margin-top:0">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                    <div class="card-title" style="margin:0">Comparison Summary</div>
                    <span style="font-size:0.75em;color:var(--text-muted)">auto-generated · English</span>
                </div>
                <p style="color:var(--text-muted);font-size:0.83em;margin:0 0 12px">${sectorNote}</p>
                <div style="display:flex;flex-direction:column;gap:7px;font-size:0.87em;color:var(--text-secondary)">
                    ${lines.map(l => `<div style="display:flex;gap:8px"><span style="color:var(--accent);flex-shrink:0">▸</span><span>${l}</span></div>`).join('')}
                </div>
                ${watchpoints.length > 0 ? `
                <div style="margin-top:14px;padding:10px 12px;background:rgba(255,152,0,0.07);border-radius:6px;border-left:2px solid #FF9800">
                    <div style="font-size:0.78em;font-weight:700;color:#FF9800;margin-bottom:7px;letter-spacing:0.04em">POINTS TO WATCH</div>
                    <div style="display:flex;flex-direction:column;gap:5px">
                        ${watchpoints.map(w => `<div style="font-size:0.82em;color:var(--text-secondary)">⚠ ${w}</div>`).join('')}
                    </div>
                </div>` : ''}
                <p style="color:var(--text-muted);font-size:0.72em;margin:12px 0 0;font-style:italic">
                    This summary is auto-generated from available market data. It is not investment advice — always conduct independent research before making investment decisions.
                </p>
            </div>`;
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
                    <button class="btn btn-sm btn-secondary" onclick="App.screenshotToClipboard()">Screenshot</button>
                </div>
            </div>

            <div id="valuation-synthesis"><div class="skeleton skeleton-card" style="height:120px;margin-bottom:16px"></div></div>

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

            <div class="grid grid-3" style="margin-top:0">
                <div class="card">
                    <div class="card-title">PBV Valuation</div>
                    <p style="color:var(--text-muted);font-size:0.82em;margin-bottom:12px">Justified Price-to-Book model — best for banks &amp; financials.</p>
                    <div class="form-row">
                        ${Forms.group('Cost of Equity (%)', 'pbv_coe', 'number', 10, { step: '0.5', min: '1', max: '30' })}
                        ${Forms.group('Terminal Growth (%)', 'pbv_tg', 'number', 5, { step: '0.5', min: '0', max: '15' })}
                    </div>
                    <button class="btn btn-primary" id="btn-pbv">Run PBV</button>
                    <div id="pbv-results" style="margin-top:16px"></div>
                </div>
                <div class="card">
                    <div class="card-title">DDM (Gordon Growth)</div>
                    <p style="color:var(--text-muted);font-size:0.82em;margin-bottom:12px">Dividend Discount Model — applies to dividend-paying stocks.</p>
                    <div class="form-row">
                        ${Forms.group('Dividend Growth (%)', 'ddm_g', 'number', 5, { step: '0.5', min: '0', max: '20' })}
                        ${Forms.group('Cost of Equity (%)', 'ddm_coe', 'number', 10, { step: '0.5', min: '1', max: '30' })}
                    </div>
                    <button class="btn btn-primary" id="btn-ddm">Run DDM</button>
                    <div id="ddm-results" style="margin-top:16px"></div>
                </div>
                <div class="card">
                    <div class="card-title">ROE Growth Model</div>
                    <p style="color:var(--text-muted);font-size:0.82em;margin-bottom:12px">Sustainable growth model based on ROE &amp; retention ratio.</p>
                    <div class="form-row">
                        ${Forms.group('Cost of Equity (%)', 'roe_coe', 'number', 10, { step: '0.5', min: '1', max: '30' })}
                    </div>
                    <button class="btn btn-primary" id="btn-roe-model">Run ROE Model</button>
                    <div id="roe-results" style="margin-top:16px"></div>
                </div>
            </div>
        `);

        this._modelTicker = ticker;
        this._modelResults = {};
        this._setupModelSync();

        // Q5: Load valuation synthesis asynchronously
        this._loadValuationSynthesis(ticker);

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
                // Q8: store current price for sensitivity heat map coloring
                if (result.current_price != null) this._lastCurrentPrice = result.current_price;
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

        // Sensitivity — Q8: color-coded HTML heat map
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
                    document.getElementById('sensitivity-results').innerHTML =
                        this._renderSensitivityHeatmap(result, this._lastCurrentPrice);
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
                    this.toast(`Data not available: ${result.error}`, 'info');
                    document.getElementById('projection-results').innerHTML =
                        `<p style="color:var(--text-muted);font-size:0.9em">⚠️ ${result.error} for this ticker. Try a different metric.</p>`;
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
                            result.historical_values || null,
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

        // PBV Model
        document.getElementById('btn-pbv').onclick = async () => {
            const coe = (parseFloat(document.getElementById('pbv_coe').value) || 10) / 100;
            const tg = (parseFloat(document.getElementById('pbv_tg').value) || 5) / 100;
            this.showLoading();
            try {
                const result = await this.api('/api/model/pbv', {
                    method: 'POST',
                    body: { ticker, cost_of_equity: coe, terminal_growth: tg },
                });
                this._modelResults.pbv = result;
                const el = document.getElementById('pbv-results');
                if (result.error) {
                    el.innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    const upside = result.upside_pct != null
                        ? `<span class="${result.upside_pct >= 0 ? 'val-positive' : 'val-negative'}" style="font-size:1.1em;font-weight:700">${result.upside_pct > 0 ? '+' : ''}${result.upside_pct}%</span>`
                        : '';
                    const verdict = result.upside_pct != null
                        ? (result.upside_pct > 20 ? '<span class="badge badge-green">Undervalued</span>'
                           : result.upside_pct < -20 ? '<span class="badge badge-red">Overvalued</span>'
                           : '<span class="badge badge-orange">Fair Value</span>')
                        : '';
                    el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                        <div><div style="color:var(--text-muted);font-size:0.8em">Intrinsic / Share</div>
                        <div style="font-size:1.6em;font-weight:700">${result.intrinsic_per_share != null ? Tables.addSeparator(result.intrinsic_per_share.toFixed(2)) : 'N/A'}</div></div>
                        <div style="text-align:right"><div style="color:var(--text-muted);font-size:0.8em">Current: ${result.current_price != null ? Tables.addSeparator(result.current_price.toFixed(2)) : 'N/A'}</div><div>${upside} ${verdict}</div></div>
                    </div>
                    ${Tables.keyValue({
                        'Justified PBV': result.justified_pbv != null ? result.justified_pbv.toFixed(2) + 'x' : 'N/A',
                        'Book Value / Share': Tables.formatValue(result.book_value_per_share),
                        'ROE Used': result.roe_used != null ? result.roe_used + '%' : 'N/A',
                        'Cost of Equity': result.cost_of_equity + '%',
                        'Terminal Growth': result.terminal_growth + '%',
                    })}`;
                }
            } catch (e) {
                document.getElementById('pbv-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // DDM
        document.getElementById('btn-ddm').onclick = async () => {
            const g = (parseFloat(document.getElementById('ddm_g').value) || 5) / 100;
            const coe = (parseFloat(document.getElementById('ddm_coe').value) || 10) / 100;
            this.showLoading();
            try {
                const result = await this.api('/api/model/ddm', {
                    method: 'POST',
                    body: { ticker, growth_rate: g, cost_of_equity: coe },
                });
                this._modelResults.ddm = result;
                const el = document.getElementById('ddm-results');
                if (result.error) {
                    el.innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    const upside = result.upside_pct != null
                        ? `<span class="${result.upside_pct >= 0 ? 'val-positive' : 'val-negative'}" style="font-size:1.1em;font-weight:700">${result.upside_pct > 0 ? '+' : ''}${result.upside_pct}%</span>`
                        : '';
                    const verdict = result.upside_pct != null
                        ? (result.upside_pct > 20 ? '<span class="badge badge-green">Undervalued</span>'
                           : result.upside_pct < -20 ? '<span class="badge badge-red">Overvalued</span>'
                           : '<span class="badge badge-orange">Fair Value</span>')
                        : '';
                    el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                        <div><div style="color:var(--text-muted);font-size:0.8em">Intrinsic / Share</div>
                        <div style="font-size:1.6em;font-weight:700">${result.intrinsic_per_share != null ? Tables.addSeparator(result.intrinsic_per_share.toFixed(2)) : 'N/A'}</div></div>
                        <div style="text-align:right"><div style="color:var(--text-muted);font-size:0.8em">Current: ${result.current_price != null ? Tables.addSeparator(result.current_price.toFixed(2)) : 'N/A'}</div><div>${upside} ${verdict}</div></div>
                    </div>
                    ${Tables.keyValue({
                        'Last Dividend': Tables.formatValue(result.last_dividend),
                        'D1 (Next Dividend)': Tables.formatValue(result.d1),
                        'Growth Rate': result.growth_rate + '%',
                        'Cost of Equity': result.cost_of_equity + '%',
                    })}`;
                }
            } catch (e) {
                document.getElementById('ddm-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // ROE Growth Model
        document.getElementById('btn-roe-model').onclick = async () => {
            const coe = (parseFloat(document.getElementById('roe_coe').value) || 10) / 100;
            this.showLoading();
            try {
                const result = await this.api('/api/model/roe', {
                    method: 'POST',
                    body: { ticker, cost_of_equity: coe },
                });
                this._modelResults.roe_model = result;
                const el = document.getElementById('roe-results');
                if (result.error) {
                    el.innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    const upside = result.upside_pct != null
                        ? `<span class="${result.upside_pct >= 0 ? 'val-positive' : 'val-negative'}" style="font-size:1.1em;font-weight:700">${result.upside_pct > 0 ? '+' : ''}${result.upside_pct}%</span>`
                        : '';
                    const verdict = result.upside_pct != null
                        ? (result.upside_pct > 20 ? '<span class="badge badge-green">Undervalued</span>'
                           : result.upside_pct < -20 ? '<span class="badge badge-red">Overvalued</span>'
                           : '<span class="badge badge-orange">Fair Value</span>')
                        : '';
                    el.innerHTML = `<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
                        <div><div style="color:var(--text-muted);font-size:0.8em">Intrinsic / Share</div>
                        <div style="font-size:1.6em;font-weight:700">${result.intrinsic_per_share != null ? Tables.addSeparator(result.intrinsic_per_share.toFixed(2)) : 'N/A'}</div></div>
                        <div style="text-align:right"><div style="color:var(--text-muted);font-size:0.8em">Current: ${result.current_price != null ? Tables.addSeparator(result.current_price.toFixed(2)) : 'N/A'}</div><div>${upside} ${verdict}</div></div>
                    </div>
                    ${Tables.keyValue({
                        'ROE': result.roe_used != null ? result.roe_used + '%' : 'N/A',
                        'Payout Ratio': result.payout_ratio != null ? result.payout_ratio + '%' : 'N/A',
                        'Retention Ratio': result.retention_ratio != null ? result.retention_ratio + '%' : 'N/A',
                        'Sustainable Growth': result.sustainable_g != null ? result.sustainable_g + '%' : 'N/A',
                        'EPS': Tables.formatValue(result.eps),
                        'Cost of Equity': result.cost_of_equity + '%',
                    })}`;
                }
            } catch (e) {
                document.getElementById('roe-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };
    },

    /** Sync shared inputs (WACC / CoE and Terminal Growth) across all model cards */
    _setupModelSync() {
        // Group: WACC / Cost of Equity fields
        const waccIds = ['wacc', 'scenario_wacc', 'pbv_coe', 'ddm_coe', 'roe_coe'];
        // Group: Terminal Growth fields
        const tgIds   = ['terminal_growth', 'scenario_tg', 'pbv_tg'];

        const syncGroup = (ids, sourceId) => {
            const src = document.getElementById(sourceId);
            if (!src) return;
            ids.forEach(id => {
                if (id === sourceId) return;
                const el = document.getElementById(id);
                if (el) el.value = src.value;
            });
        };

        waccIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', () => syncGroup(waccIds, id));
        });
        tgIds.forEach(id => {
            const el = document.getElementById(id);
            if (el) el.addEventListener('input', () => syncGroup(tgIds, id));
        });
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
    _noteEditorHtml(initialTicker = '', initialTitle = '', initialContent = '', initialTags = '') {
        const esc = s => s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
        const toolbar = [
            { icon: '<b>B</b>',  wrap: ['**','**'],    title: 'Bold (Ctrl+B)' },
            { icon: '<em>I</em>', wrap: ['*','*'],      title: 'Italic (Ctrl+I)' },
            { icon: '`</>`',     wrap: ['`','`'],       title: 'Inline code' },
            { icon: 'H2',        prefix: '## ',         title: 'Heading 2' },
            { icon: 'H3',        prefix: '### ',        title: 'Heading 3' },
            { icon: '—',         line: '---',           title: 'Divider' },
            { icon: '▸ List',    prefix: '- ',          title: 'Bullet list' },
            { icon: '❝',         prefix: '> ',          title: 'Blockquote' },
        ].map((b, i) => `<button type="button" class="btn btn-sm btn-secondary note-tb-btn" data-idx="${i}" title="${b.title}" style="padding:2px 7px;font-size:0.8em">${b.icon}</button>`).join('');

        return `
            <div class="form-row" style="gap:10px">
                ${Forms.group('Ticker', 'note-ticker', 'text', esc(initialTicker), { placeholder: 'BBCA.JK' })}
                ${Forms.group('Title', 'note-title', 'text', esc(initialTitle), { placeholder: 'Analysis title' })}
            </div>
            <div class="form-group">
                <label>Content <span style="color:var(--text-muted);font-size:0.78em;font-weight:400">(Markdown: **bold** *italic* # heading - list &gt; quote \`code\`)</span></label>
                <div style="display:flex;gap:4px;flex-wrap:wrap;margin-bottom:6px">${toolbar}</div>
                <div style="display:grid;grid-template-columns:1fr 1fr;gap:8px">
                    <textarea id="note-content" name="note-content" rows="10"
                        style="font-family:monospace;font-size:0.85em;resize:vertical;min-height:180px"
                        placeholder="Tulis analisis kamu dengan markdown...">${esc(initialContent)}</textarea>
                    <div id="note-preview"
                        style="min-height:180px;padding:8px 10px;background:var(--bg-input);border:1px solid var(--border);border-radius:var(--radius);overflow-y:auto;font-size:0.88em;line-height:1.6"></div>
                </div>
                <div style="font-size:0.75em;color:var(--text-muted);margin-top:4px">Editor kiri · Preview kanan (live)</div>
            </div>
            ${Forms.group('Tags (pisahkan koma)', 'note-tags', 'text', esc(initialTags), { placeholder: 'banking, analisis' })}`;
    },

    _initNoteEditor() {
        const ta = document.getElementById('note-content');
        const preview = document.getElementById('note-preview');
        if (!ta || !preview) return;

        const update = () => { preview.innerHTML = this._md(ta.value); };
        ta.addEventListener('input', update);
        update();

        // Toolbar buttons
        const toolbarDefs = [
            { wrap: ['**','**'] }, { wrap: ['*','*'] }, { wrap: ['`','`'] },
            { prefix: '## ' }, { prefix: '### ' }, { line: '---' },
            { prefix: '- ' }, { prefix: '> ' },
        ];
        document.querySelectorAll('.note-tb-btn').forEach(btn => {
            btn.onclick = () => {
                const def = toolbarDefs[+btn.dataset.idx];
                const start = ta.selectionStart, end = ta.selectionEnd;
                const sel = ta.value.slice(start, end);
                let replacement, cursorOffset;
                if (def.line) {
                    replacement = (start > 0 ? '\n' : '') + def.line + '\n';
                    cursorOffset = replacement.length;
                } else if (def.wrap) {
                    replacement = def.wrap[0] + (sel || 'teks') + def.wrap[1];
                    cursorOffset = def.wrap[0].length + (sel || 'teks').length;
                } else if (def.prefix) {
                    const lineStart = ta.value.lastIndexOf('\n', start - 1) + 1;
                    ta.value = ta.value.slice(0, lineStart) + def.prefix + ta.value.slice(lineStart);
                    ta.selectionStart = ta.selectionEnd = lineStart + def.prefix.length;
                    update();
                    ta.focus();
                    return;
                }
                ta.value = ta.value.slice(0, start) + replacement + ta.value.slice(end);
                ta.selectionStart = ta.selectionEnd = start + cursorOffset;
                update();
                ta.focus();
            };
        });

        // Ctrl+B / Ctrl+I shortcuts
        ta.addEventListener('keydown', e => {
            if (e.ctrlKey && e.key === 'b') { e.preventDefault(); toolbarDefs[0] && document.querySelector('[data-idx="0"]')?.click(); }
            if (e.ctrlKey && e.key === 'i') { e.preventDefault(); toolbarDefs[1] && document.querySelector('[data-idx="1"]')?.click(); }
            // Tab → 2 spaces
            if (e.key === 'Tab') {
                e.preventDefault();
                const s = ta.selectionStart;
                ta.value = ta.value.slice(0, s) + '  ' + ta.value.slice(ta.selectionEnd);
                ta.selectionStart = ta.selectionEnd = s + 2;
            }
        });
    },

    async renderNotes() {
        this.showLoading();
        try {
            const notes = await this.api('/api/notes');
            const esc = s => (s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
            let listHtml = '';
            if (notes.length > 0) {
                listHtml = notes.map(n => `
                    <div class="card">
                        <div style="display:flex;justify-content:space-between;align-items:start;flex-wrap:wrap;gap:4px">
                            <div style="display:flex;gap:4px;flex-wrap:wrap;align-items:center">
                                <span class="badge badge-blue">${esc(n.ticker)}</span>
                                ${(n.tags||[]).map(t => `<span class="badge badge-purple">${esc(t)}</span>`).join('')}
                            </div>
                            <div style="display:flex;gap:4px;align-items:center">
                                <span style="color:var(--text-muted);font-size:0.75em">${n.updated_at.substring(0,10)}</span>
                                <button class="btn btn-sm btn-secondary" onclick="App.editNote(${n.id})">Edit</button>
                                <button class="btn btn-sm btn-danger" onclick="App.deleteNote(${n.id})">Del</button>
                            </div>
                        </div>
                        <div class="card-title" style="margin-top:8px">${esc(n.title)}</div>
                        <div class="note-body" style="margin-top:8px;font-size:0.88em;line-height:1.65">${this._md(n.content || '')}</div>
                    </div>
                `).join('');
            } else {
                listHtml = '<div class="empty-state"><p>Belum ada catatan. Buat satu di bawah.</p></div>';
            }

            this.render(`
                <div class="section-header">
                    <h2>Notes</h2>
                    <button class="btn btn-sm btn-secondary" onclick="App.screenshotToClipboard()">Screenshot</button>
                </div>
                <div class="card" id="note-form-card">
                    <div class="card-title">Catatan Baru</div>
                    ${this._noteEditorHtml()}
                    <div style="margin-top:12px;display:flex;gap:8px">
                        <button class="btn btn-primary" id="btn-save-note">Simpan Catatan</button>
                        <button class="btn btn-secondary" id="btn-reset-note" type="button">Reset</button>
                    </div>
                </div>
                <div id="notes-list" style="margin-top:16px">${listHtml}</div>
            `);

            this._initNoteEditor();

            document.getElementById('btn-save-note').onclick = async () => {
                const ticker  = document.getElementById('note-ticker').value.trim();
                const title   = document.getElementById('note-title').value.trim();
                const content = document.getElementById('note-content').value;
                const tags    = document.getElementById('note-tags').value;
                if (!ticker || !title) { this.toast('Ticker dan judul wajib diisi', 'error'); return; }
                try {
                    await this.api('/api/notes', { method: 'POST', body: { ticker, title, content, tags } });
                    this.toast('Catatan disimpan', 'success');
                    this.renderNotes();
                } catch (e) { this.toast(e.message, 'error'); }
            };
            document.getElementById('btn-reset-note').onclick = () => {
                document.getElementById('note-ticker').value = '';
                document.getElementById('note-title').value = '';
                document.getElementById('note-content').value = '';
                document.getElementById('note-tags').value = '';
                document.getElementById('note-preview').innerHTML = '';
                document.getElementById('btn-save-note').textContent = 'Simpan Catatan';
                this._initNoteEditor();
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
            if (!note) { this.toast('Catatan tidak ditemukan', 'error'); return; }

            // Re-render editor section with existing values
            const formCard = document.getElementById('note-form-card');
            if (formCard) {
                formCard.innerHTML = `<div class="card-title">Edit Catatan</div>
                    ${this._noteEditorHtml(note.ticker, note.title, note.content || '', (note.tags||[]).join(', '))}
                    <div style="margin-top:12px;display:flex;gap:8px">
                        <button class="btn btn-primary" id="btn-save-note">Update Catatan</button>
                        <button class="btn btn-secondary" id="btn-cancel-edit" type="button">Batal</button>
                    </div>`;
                this._initNoteEditor();
                document.getElementById('btn-save-note').onclick = async () => {
                    const title   = document.getElementById('note-title').value.trim();
                    const content = document.getElementById('note-content').value;
                    const tags    = document.getElementById('note-tags').value;
                    try {
                        await this.api(`/api/notes/${id}`, { method: 'PUT', body: { title, content, tags } });
                        this.toast('Catatan diperbarui', 'success');
                        this.renderNotes();
                    } catch (e) { this.toast(e.message, 'error'); }
                };
                document.getElementById('btn-cancel-edit').onclick = () => this.renderNotes();
            }
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
                <div class="section-header">
                    <h2>Watchlists</h2>
                    <button class="btn btn-sm btn-secondary" onclick="App.screenshotToClipboard()">Screenshot</button>
                </div>
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
        if (typeof html2canvas === 'undefined') {
            this.toast('Screenshot library failed to load. Refresh the page and try again.', 'error');
            return;
        }
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
