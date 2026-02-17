/**
 * Plotly chart builders for Alpha module
 */
const Charts = {
    darkLayout: {
        plot_bgcolor: '#1e1e2f',
        paper_bgcolor: '#16161e',
        font: { color: '#e0e0e0', size: 12 },
        margin: { l: 50, r: 30, t: 40, b: 40 },
        xaxis: { gridcolor: '#2a2a3e' },
        yaxis: { gridcolor: '#2a2a3e' },
    },

    config: {
        responsive: true,
        displayModeBar: true,
        modeBarButtonsToRemove: ['lasso2d', 'select2d'],
    },

    /**
     * Render a bar chart for comparison metrics
     */
    comparisonBar(containerId, tickers, metricName, values) {
        const colors = ['#2196F3', '#26a69a', '#FF9800', '#9C27B0', '#ef5350', '#00BCD4', '#E91E63', '#8BC34A'];
        const trace = {
            x: tickers,
            y: values,
            type: 'bar',
            marker: { color: colors.slice(0, tickers.length) },
            text: values.map(v => v != null ? v.toFixed(2) : 'N/A'),
            textposition: 'auto',
        };
        const layout = {
            ...this.darkLayout,
            title: { text: metricName, font: { size: 14 } },
            height: 300,
        };
        Plotly.newPlot(containerId, [trace], layout, this.config);
    },

    /**
     * Render a radar chart with normalized values (0-100 scale)
     */
    radarChart(containerId, tickers, metrics, dataByTicker) {
        const colors = ['#2196F3', '#26a69a', '#FF9800', '#9C27B0', '#ef5350', '#00BCD4', '#E91E63', '#8BC34A'];

        // Normalize each metric to 0-100 range across tickers
        const normalized = {};
        tickers.forEach(t => { normalized[t] = {}; });

        metrics.forEach(m => {
            const vals = tickers.map(t => dataByTicker[t]?.[m]).filter(v => v != null && isFinite(v));
            const min = Math.min(...vals, 0);
            const max = Math.max(...vals, 1);
            const range = max - min || 1;
            tickers.forEach(t => {
                const v = dataByTicker[t]?.[m];
                normalized[t][m] = (v != null && isFinite(v)) ? ((v - min) / range) * 100 : 0;
            });
        });

        const traces = tickers.map((ticker, i) => ({
            type: 'scatterpolar',
            r: metrics.map(m => normalized[ticker][m]),
            theta: metrics,
            fill: 'toself',
            name: ticker,
            line: { color: colors[i % colors.length] },
            opacity: 0.6,
            hovertemplate: metrics.map(m =>
                `${m}: ${dataByTicker[ticker]?.[m] != null ? dataByTicker[ticker][m].toFixed(2) : 'N/A'}`
            ).join('<br>') + '<extra>%{fullData.name}</extra>',
        }));

        const layout = {
            ...this.darkLayout,
            polar: {
                bgcolor: '#1e1e2f',
                radialaxis: { gridcolor: '#2a2a3e', color: '#a0a0b0', range: [0, 100], showticklabels: false },
                angularaxis: { gridcolor: '#2a2a3e', color: '#a0a0b0' },
            },
            title: { text: 'Normalized Comparison (0-100)', font: { size: 14 } },
            height: 450,
            legend: { font: { size: 11 } },
        };
        Plotly.newPlot(containerId, traces, layout, this.config);
    },

    /**
     * Render a trend line chart
     */
    trendLine(containerId, title, labels, values, growthPcts) {
        const traces = [{
            x: labels,
            y: values,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Value',
            line: { color: '#2196F3', width: 2 },
            marker: { size: 6 },
        }];

        if (growthPcts) {
            traces.push({
                x: labels,
                y: growthPcts,
                type: 'bar',
                name: 'Growth %',
                yaxis: 'y2',
                marker: {
                    color: growthPcts.map(g => g != null ? (g >= 0 ? '#26a69a' : '#ef5350') : '#666'),
                },
                opacity: 0.5,
            });
        }

        const layout = {
            ...this.darkLayout,
            title: { text: title, font: { size: 14 } },
            height: 350,
            yaxis2: growthPcts ? {
                overlaying: 'y',
                side: 'right',
                title: 'Growth %',
                gridcolor: '#2a2a3e',
            } : undefined,
            legend: { orientation: 'h', y: -0.15 },
        };
        Plotly.newPlot(containerId, traces, layout, this.config);
    },

    /**
     * Render a sensitivity heatmap
     */
    heatmap(containerId, title, xLabels, yLabels, matrix, currentPrice) {
        const colorscale = currentPrice
            ? matrix.map(row => row.map(v => v != null && v > currentPrice ? 1 : 0)).flat()
            : null;

        const trace = {
            x: xLabels,
            y: yLabels,
            z: matrix,
            type: 'heatmap',
            colorscale: 'RdYlGn',
            text: matrix.map(row => row.map(v => v != null ? v.toFixed(2) : 'N/A')),
            texttemplate: '%{text}',
            hovertemplate: 'WACC: %{y}<br>Growth: %{x}<br>Value: %{z:.2f}<extra></extra>',
        };

        const layout = {
            ...this.darkLayout,
            title: { text: title, font: { size: 14 } },
            height: 400,
            xaxis: { ...this.darkLayout.xaxis, title: 'Growth Rate' },
            yaxis: { ...this.darkLayout.yaxis, title: 'WACC' },
        };
        Plotly.newPlot(containerId, [trace], layout, this.config);
    },

    /**
     * Render projection chart with confidence bands
     */
    projectionChart(containerId, title, histLabels, histValues, fitted, projections) {
        const traces = [];

        // Historical data points (if provided)
        if (histValues && histValues.some(v => v != null)) {
            traces.push({
                x: histLabels,
                y: histValues,
                type: 'scatter',
                mode: 'markers',
                name: 'Historical',
                marker: { color: '#2196F3', size: 8 },
            });
        }

        // Fitted line
        traces.push({
            x: histLabels,
            y: fitted,
            type: 'scatter',
            mode: 'lines+markers',
            name: 'Trend Line',
            line: { color: '#FF9800', dash: 'dash', width: 1.5 },
            marker: { color: '#FF9800', size: 6 },
        });

        if (projections && projections.length > 0) {
            const projLabels = projections.map((_, i) => `P+${i + 1}`);
            const projVals = projections.map(p => p.value);
            const upper = projections.map(p => p.upper);
            const lower = projections.map(p => p.lower);

            traces.push({
                x: projLabels,
                y: projVals,
                type: 'scatter',
                mode: 'lines+markers',
                name: 'Projection',
                line: { color: '#26a69a', width: 2 },
            });
            traces.push({
                x: [...projLabels, ...projLabels.slice().reverse()],
                y: [...upper, ...lower.slice().reverse()],
                fill: 'toself',
                fillcolor: 'rgba(38,166,154,0.15)',
                line: { color: 'transparent' },
                name: '95% CI',
                showlegend: true,
            });
        }

        const layout = {
            ...this.darkLayout,
            title: { text: title, font: { size: 14 } },
            height: 400,
            legend: { orientation: 'h', y: -0.15 },
        };
        Plotly.newPlot(containerId, traces, layout, this.config);
    },
};
