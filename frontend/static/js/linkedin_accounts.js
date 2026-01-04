const LinkedInAccounts = {
    accounts: [],
    selectedAccountId: null,

    init() {
        this.loadAccounts();
        this.setupEventListeners();
        this.checkCallback();
    },

    async loadAccounts() {
        try {
            this.accounts = await Api.getLinkedInAccounts();
            this.renderAccounts();
            this.updateSelectors();
        } catch (e) {
            console.error("Failed to load LinkedIn accounts:", e);
        }
    },

    setupEventListeners() {
        const connectBtn = document.getElementById('connect-linkedin-btn');
        if (connectBtn) {
            connectBtn.onclick = () => this.initiateOAuth();
        }

        // Add account management button to sidebar
        const linkedinContainer = document.getElementById('sidebar-linkedin-container');
        if (linkedinContainer) {
            const mgmtBtn = document.createElement('button');
            mgmtBtn.className = 'sidebar-btn';
            mgmtBtn.innerHTML = '<span class="icon">🔗</span> <span>LinkedIn</span>';
            mgmtBtn.onclick = () => this.showManagementModal();
            linkedinContainer.appendChild(mgmtBtn);
        }
    },

    async initiateOAuth() {
        try {
            const { url } = await Api.getLinkedInAuthUrl();
            window.location.href = url;
        } catch (e) {
            Toast.show("Failed to start LinkedIn connection", "error");
        }
    },

    async checkCallback() {
        const urlParams = new URLSearchParams(window.location.search);
        const code = urlParams.get('code');
        if (code) {
            // Remove code from URL
            window.history.replaceState({}, document.title, window.location.pathname);
            
            Toast.show("Connecting LinkedIn account...", "info");
            try {
                await Api.connectLinkedIn(code);
                Toast.show("LinkedIn account connected successfully!");
                await this.loadAccounts();
                this.showManagementModal();
            } catch (e) {
                Toast.show("Failed to connect LinkedIn account", "error");
            }
        }
    },

    showManagementModal() {
        const modal = document.getElementById('linkedin-mgmt-modal');
        if (modal) {
            modal.classList.remove('hidden');
            this.renderAccounts();
        }
    },

    renderAccounts() {
        const list = document.getElementById('linkedin-accounts-list');
        if (!list) return;

        if (this.accounts.length === 0) {
            list.innerHTML = '<p style="text-align:center; padding: 20px; color: var(--text-secondary);">No accounts connected.</p>';
            return;
        }

        list.innerHTML = this.accounts.map(acc => `
            <div class="account-item">
                <div class="account-info">
                    <strong>${acc.display_name || 'LinkedIn User'}</strong>
                    <span>${acc.linkedin_email || ''}</span>
                    <span class="status-badge ${acc.status}">${acc.status}</span>
                </div>
                <button class="btn-icon delete" onclick="LinkedInAccounts.disconnectAccount(${acc.id})">✕</button>
            </div>
        `).join('');
    },

    async disconnectAccount(id) {
        if (!confirm("Disconnect this LinkedIn account?")) return;
        try {
            await Api.disconnectLinkedInAccount(id);
            Toast.show("Account disconnected");
            await this.loadAccounts();
        } catch (e) {
            Toast.show("Failed to disconnect", "error");
        }
    },

    updateSelectors() {
        const selectors = document.querySelectorAll('.linkedin-account-selector');
        selectors.forEach(select => {
            const currentValue = select.value;
            select.innerHTML = this.accounts.map(acc => `
                <option value="${acc.id}" ${acc.id == currentValue ? 'selected' : ''}>
                    ${acc.display_name} (${acc.status})
                </option>
            `).join('');
            
            if (this.accounts.length > 0 && !select.value) {
                select.value = this.accounts[0].id;
            }
        });
    },

    getSelectedAccountId(selectorId) {
        const selector = document.getElementById(selectorId);
        return selector ? selector.value : null;
    }
};

document.addEventListener('DOMContentLoaded', () => LinkedInAccounts.init());
