/**
 * Hash-based SPA router
 */
const Router = {
    routes: {},
    currentPage: null,

    register(hash, handler) {
        this.routes[hash] = handler;
    },

    navigate(hash) {
        window.location.hash = hash;
    },

    init() {
        window.addEventListener('hashchange', () => this._resolve());
        // Initial route
        if (!window.location.hash) {
            window.location.hash = '#dashboard';
        } else {
            this._resolve();
        }
    },

    _resolve() {
        const hash = window.location.hash.slice(1) || 'dashboard';
        const parts = hash.split('/');
        const page = parts[0];
        const param = parts.slice(1).join('/');

        // Update nav active state
        document.querySelectorAll('.nav-link').forEach(el => {
            el.classList.toggle('active', el.dataset.page === page);
        });

        this.currentPage = page;

        // Find matching route
        const handler = this.routes[page];
        if (handler) {
            handler(param);
        } else {
            document.getElementById('page-content').innerHTML =
                '<div class="empty-state"><h3>Page not found</h3></div>';
        }
    },

    getParam() {
        const hash = window.location.hash.slice(1) || '';
        const parts = hash.split('/');
        return parts.slice(1).join('/');
    }
};
