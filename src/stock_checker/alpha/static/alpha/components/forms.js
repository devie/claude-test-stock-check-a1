/**
 * Form helpers for modelling and input
 */
const Forms = {
    /**
     * Create a form group HTML
     */
    group(label, name, type = 'text', value = '', attrs = {}) {
        const attrStr = Object.entries(attrs)
            .map(([k, v]) => `${k}="${v}"`)
            .join(' ');
        if (type === 'textarea') {
            return `<div class="form-group">
                <label for="${name}">${label}</label>
                <textarea id="${name}" name="${name}" ${attrStr}>${value}</textarea>
            </div>`;
        }
        if (type === 'select') {
            const options = (attrs.options || [])
                .map(o => `<option value="${o.value}" ${o.value == value ? 'selected' : ''}>${o.label}</option>`)
                .join('');
            return `<div class="form-group">
                <label for="${name}">${label}</label>
                <select id="${name}" name="${name}">${options}</select>
            </div>`;
        }
        return `<div class="form-group">
            <label for="${name}">${label}</label>
            <input type="${type}" id="${name}" name="${name}" value="${value}" ${attrStr} />
        </div>`;
    },

    /**
     * Read all form values from a container
     */
    readValues(containerId) {
        const container = document.getElementById(containerId);
        if (!container) return {};
        const values = {};
        container.querySelectorAll('input, select, textarea').forEach(el => {
            if (el.name) {
                if (el.type === 'number') {
                    values[el.name] = parseFloat(el.value) || 0;
                } else {
                    values[el.name] = el.value;
                }
            }
        });
        return values;
    },

    /**
     * DCF assumptions form
     */
    dcfForm(defaults = {}) {
        const d = {
            growth_rate: 10,
            terminal_growth: 3,
            wacc: 10,
            projection_years: 5,
            ...defaults,
        };
        return `
            <div class="form-row">
                ${Forms.group('FCF Growth Rate (%)', 'growth_rate', 'number', d.growth_rate, { step: '0.5', min: '-50', max: '100' })}
                ${Forms.group('Terminal Growth (%)', 'terminal_growth', 'number', d.terminal_growth, { step: '0.5', min: '0', max: '10' })}
            </div>
            <div class="form-row">
                ${Forms.group('WACC (%)', 'wacc', 'number', d.wacc, { step: '0.5', min: '1', max: '30' })}
                ${Forms.group('Projection Years', 'projection_years', 'number', d.projection_years, { step: '1', min: '1', max: '20' })}
            </div>
        `;
    },

    /**
     * Scenario form
     */
    scenarioForm(defaults = {}) {
        const d = { bull: 15, base: 10, bear: 5, ...defaults };
        return `
            <div class="form-row">
                ${Forms.group('Bull Growth (%)', 'bull', 'number', d.bull, { step: '0.5' })}
                ${Forms.group('Base Growth (%)', 'base', 'number', d.base, { step: '0.5' })}
                ${Forms.group('Bear Growth (%)', 'bear', 'number', d.bear, { step: '0.5' })}
            </div>
        `;
    },
};
