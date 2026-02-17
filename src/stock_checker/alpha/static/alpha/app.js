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
        // Check if response is file download
        const ct = resp.headers.get('content-type') || '';
        if (ct.includes('text/csv') || ct.includes('application/pdf')) {
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
        document.getElementById('page-content').innerHTML = html;
    },

    // ====== PAGE RENDERERS ======

    // --- Dashboard ---
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
            // DB might not have data yet
            watchlistsHtml = '<div class="empty-state"><p>No watchlists yet.</p></div>';
            notesHtml = '<div class="empty-state"><p>No notes yet.</p></div>';
        }

        this.render(`
            <div class="section-header">
                <h2>Dashboard</h2>
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
                        .map(t => `<span class="ticker-chip" onclick="Router.navigate('#detail/${t}')">${t}</span>`).join('')}
                </div>
            </div>
        `);
    },

    // --- Detail ---
    async renderDetail(ticker) {
        if (!ticker) {
            this.render('<div class="empty-state"><h3>Enter a ticker to analyze</h3></div>');
            return;
        }
        this.showLoading();
        try {
            const [fin, trends] = await Promise.all([
                this.api('/api/financials', { method: 'POST', body: { ticker } }),
                this.api('/api/trends', { method: 'POST', body: { ticker } }),
            ]);

            const fv = Tables.formatValue;
            const ps = fin.price_summary || {};
            const hl = fin.highlights || {};

            // Price summary card
            const priceSummaryHtml = `
                <div class="card">
                    <div style="display:flex;justify-content:space-between;align-items:baseline;flex-wrap:wrap;gap:8px">
                        <div>
                            <span style="font-size:2em;font-weight:700">${fv(ps.current_price)}</span>
                            <span style="color:var(--text-muted);margin-left:4px">${ps.currency || ''}</span>
                        </div>
                        <div style="display:flex;gap:16px;flex-wrap:wrap">
                            <div><span style="color:var(--text-muted);font-size:0.8em">Mkt Cap</span><br>${fv(ps.market_cap, true)}</div>
                            <div><span style="color:var(--text-muted);font-size:0.8em">52W High</span><br>${fv(ps['52w_high'])}</div>
                            <div><span style="color:var(--text-muted);font-size:0.8em">52W Low</span><br>${fv(ps['52w_low'])}</div>
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
                            <div style="font-size:1.1em;font-weight:600">${fv(v, true)}</div>
                        </div>
                    `).join('') + '</div></div>';
            }

            // Ratios - split into categories
            const ratioCategories = {
                'Valuation': ['PER', 'PBV', 'EV/EBITDA', 'PEG'],
                'Profitability': ['ROE', 'ROA', 'NPM', 'GPM'],
                'Risk & Leverage': ['Beta', 'DER', 'Current Ratio', 'Dividend Yield'],
            };
            let ratiosHtml = '<div class="grid grid-3">';
            for (const [cat, keys] of Object.entries(ratioCategories)) {
                const filtered = {};
                keys.forEach(k => { if (fin.ratios[k] !== undefined) filtered[k] = fin.ratios[k]; });
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
                    <div id="stmt-income">${Tables.financialStatement(fin.income_statement, 'Income Statement (Annual)')}</div>
                    <div id="stmt-balance" class="hidden">${Tables.financialStatement(fin.balance_sheet, 'Balance Sheet')}</div>
                    <div id="stmt-cashflow" class="hidden">${Tables.financialStatement(fin.cash_flow, 'Cash Flow')}</div>
                    <div id="stmt-quarterly" class="hidden">${Tables.financialStatement(fin.quarterly_income, 'Income Statement (Quarterly)')}</div>
                </div>`;

            this.render(`
                <div class="section-header">
                    <h2>${fin.name || ticker} <span style="color:var(--text-muted);font-weight:400">(${fin.ticker})</span></h2>
                    <div style="display:flex;gap:8px;align-items:center">
                        <span class="badge badge-blue">${fin.sector}</span>
                        <span class="badge badge-purple">${fin.industry}</span>
                        <button class="btn btn-sm btn-primary" onclick="Router.navigate('#model/${ticker}')">DCF Model</button>
                        <button class="btn btn-sm btn-secondary" onclick="App.saveSnapshot('${ticker}', ${JSON.stringify(fin.ratios).replace(/"/g, '&quot;')})">Save Snapshot</button>
                    </div>
                </div>
                ${priceSummaryHtml}
                ${highlightsHtml}
                ${ratiosHtml}
                ${anomalyHtml}
                ${trendChartsHtml}
                ${stmtTabs}
            `);

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
            this.render(`<div class="card"><p class="val-negative">Error: ${e.message}</p></div>`);
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
    async renderCompare() {
        this.render(`
            <div class="section-header"><h2>Compare Tickers</h2></div>
            <div class="card">
                <div class="form-group">
                    <label>Tickers (comma-separated, max 8)</label>
                    <input type="text" id="compare-tickers" placeholder="BBCA.JK, BBRI.JK, BMRI.JK" />
                </div>
                <button class="btn btn-primary" id="btn-compare">Compare</button>
            </div>
            <div id="compare-results"></div>
        `);

        document.getElementById('btn-compare').onclick = async () => {
            const input = document.getElementById('compare-tickers').value;
            const tickers = input.split(',').map(t => t.trim().toUpperCase()).filter(Boolean);
            if (tickers.length < 2) { this.toast('Enter at least 2 tickers', 'error'); return; }

            this.showLoading();
            try {
                const result = await this.api('/api/compare', {
                    method: 'POST',
                    body: { tickers },
                });

                let html = '<div class="card">' +
                    Tables.comparison(result.metrics, result.tickers, result.data) +
                    '</div>';

                // Bar charts for key metrics
                const chartMetrics = ['PER', 'ROE', 'NPM', 'DER'];
                html += '<div class="grid grid-2">';
                chartMetrics.forEach((m, i) => {
                    html += `<div class="card"><div id="cmp-chart-${i}"></div></div>`;
                });
                html += '</div>';

                // Radar chart
                html += '<div class="card"><div id="radar-chart"></div></div>';

                // Export buttons
                html += `<div style="margin-top:12px;display:flex;gap:8px">
                    <button class="btn btn-secondary btn-sm" onclick="App.exportData('csv', ${JSON.stringify(result.data).replace(/"/g, '&quot;')})">Export CSV</button>
                    <button class="btn btn-secondary btn-sm" onclick="App.exportData('json', ${JSON.stringify(result.data).replace(/"/g, '&quot;')})">Export JSON</button>
                </div>`;

                document.getElementById('compare-results').innerHTML = html;

                // Render charts
                chartMetrics.forEach((m, i) => {
                    const vals = result.tickers.map(t => result.data[t]?.metrics?.[m] ?? null);
                    Charts.comparisonBar(`cmp-chart-${i}`, result.tickers, m, vals);
                });

                // Radar
                const radarMetrics = ['PER', 'PBV', 'ROE', 'ROA', 'NPM', 'DER'];
                const radarData = {};
                result.tickers.forEach(t => {
                    radarData[t] = {};
                    radarMetrics.forEach(m => {
                        radarData[t][m] = result.data[t]?.metrics?.[m] ?? 0;
                    });
                });
                Charts.radarChart('radar-chart', result.tickers, radarMetrics, radarData);
            } catch (e) {
                document.getElementById('compare-results').innerHTML =
                    `<div class="card"><p class="val-negative">Error: ${e.message}</p></div>`;
            }
            this.hideLoading();
        };
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
                <button class="btn btn-sm btn-secondary" onclick="Router.navigate('#detail/${ticker}')">Back to Detail</button>
            </div>

            <div class="card">
                <div class="card-title">DCF Valuation</div>
                <div id="dcf-form">${Forms.dcfForm()}</div>
                <button class="btn btn-primary" id="btn-dcf">Run DCF</button>
                <div id="dcf-results" style="margin-top:16px"></div>
            </div>

            <div class="card">
                <div class="card-title">Scenario Analysis</div>
                <div id="scenario-form">${Forms.scenarioForm()}</div>
                <button class="btn btn-primary" id="btn-scenario">Run Scenarios</button>
                <div id="scenario-results" style="margin-top:16px"></div>
            </div>

            <div class="card">
                <div class="card-title">Sensitivity Matrix</div>
                <button class="btn btn-primary" id="btn-sensitivity">Generate Heatmap</button>
                <div id="sensitivity-results" style="margin-top:16px"></div>
            </div>

            <div class="card">
                <div class="card-title">Linear Projection</div>
                <div class="form-group">
                    <label>Metric</label>
                    <select id="proj-metric">
                        <option value="Total Revenue">Total Revenue</option>
                        <option value="Net Income">Net Income</option>
                        <option value="Operating Cash Flow">Operating Cash Flow</option>
                        <option value="Free Cash Flow">Free Cash Flow</option>
                        <option value="Gross Profit">Gross Profit</option>
                    </select>
                </div>
                <button class="btn btn-primary" id="btn-projection">Project</button>
                <div id="projection-results" style="margin-top:16px"></div>
            </div>
        `);

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
                if (result.error) {
                    document.getElementById('dcf-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    const upside = result.upside_pct != null
                        ? `<span class="${result.upside_pct >= 0 ? 'val-positive' : 'val-negative'}">${result.upside_pct > 0 ? '+' : ''}${result.upside_pct}%</span>`
                        : '';
                    document.getElementById('dcf-results').innerHTML = Tables.keyValue({
                        'FCF Base': Tables.formatValue(result.fcf_base, true),
                        'Sum PV of FCFs': Tables.formatValue(result.sum_pv_fcf, true),
                        'PV Terminal Value': Tables.formatValue(result.pv_terminal, true),
                        'Enterprise Value': Tables.formatValue(result.enterprise_value, true),
                        'Equity Value': Tables.formatValue(result.equity_value, true),
                        'Intrinsic/Share': result.intrinsic_per_share != null ? result.intrinsic_per_share.toFixed(2) : 'N/A',
                        'Current Price': result.current_price != null ? result.current_price.toFixed(2) : 'N/A',
                        'Upside/Downside': upside || 'N/A',
                    });
                }
            } catch (e) {
                document.getElementById('dcf-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // Scenario
        document.getElementById('btn-scenario').onclick = async () => {
            const vals = Forms.readValues('scenario-form');
            this.showLoading();
            try {
                const result = await this.api('/api/model/scenario', {
                    method: 'POST',
                    body: {
                        ticker,
                        scenarios: { bull: vals.bull / 100, base: vals.base / 100, bear: vals.bear / 100 },
                    },
                });
                if (result.error) {
                    document.getElementById('scenario-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    let html = '<table class="data-table"><thead><tr><th>Scenario</th><th>Intrinsic/Share</th><th>Equity Value</th></tr></thead><tbody>';
                    for (const [name, data] of Object.entries(result.scenarios)) {
                        html += `<tr><td>${name.charAt(0).toUpperCase() + name.slice(1)}</td>
                            <td>${data.intrinsic_per_share != null ? data.intrinsic_per_share.toFixed(2) : 'N/A'}</td>
                            <td>${Tables.formatValue(data.equity_value, true)}</td></tr>`;
                    }
                    html += '</tbody></table>';
                    if (result.current_price) html += `<p style="margin-top:8px;color:var(--text-secondary)">Current price: ${result.current_price.toFixed(2)}</p>`;
                    document.getElementById('scenario-results').innerHTML = html;
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
                if (result.error) {
                    document.getElementById('sensitivity-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    document.getElementById('sensitivity-results').innerHTML = '<div id="sens-heatmap"></div>';
                    Charts.heatmap('sens-heatmap', 'Intrinsic Value per Share',
                        result.growth_labels, result.wacc_labels, result.matrix);
                }
            } catch (e) {
                document.getElementById('sensitivity-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };

        // Projection
        document.getElementById('btn-projection').onclick = async () => {
            const metric = document.getElementById('proj-metric').value;
            this.showLoading();
            try {
                const result = await this.api('/api/model/projection', {
                    method: 'POST',
                    body: { ticker, metric },
                });
                if (result.error) {
                    document.getElementById('projection-results').innerHTML = `<p class="val-negative">${result.error}</p>`;
                } else {
                    document.getElementById('projection-results').innerHTML =
                        `<div id="proj-chart"></div>
                         <p style="margin-top:8px;color:var(--text-secondary)">R² = ${result.r_squared}</p>`;
                    Charts.projectionChart('proj-chart', `${metric} Projection`,
                        result.historical_labels.map(l => l.substring(0, 4)),
                        result.fitted.map((_, i) => result.historical_labels[i] ? null : null),
                        result.fitted,
                        result.projections
                    );
                }
            } catch (e) {
                document.getElementById('projection-results').innerHTML = `<p class="val-negative">${e.message}</p>`;
            }
            this.hideLoading();
        };
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
        // Simple: scroll to form and populate (for MVP)
        this.toast('Edit by creating a new note with same ticker/title', 'info');
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

    Router.init();
});
