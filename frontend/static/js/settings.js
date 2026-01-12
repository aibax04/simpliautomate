const Settings = {
    init() {
        this.setupEventListeners();
    },

    setupEventListeners() {
        const generateBtn = document.getElementById('generate-token-btn');
        const copyBtn = document.getElementById('copy-token-btn');

        if (generateBtn) {
            generateBtn.addEventListener('click', () => this.generateToken());
        }

        if (copyBtn) {
            copyBtn.addEventListener('click', () => this.copyToken());
        }
    },

    async generateToken() {
        const generateBtn = document.getElementById('generate-token-btn');
        const tokenInput = document.getElementById('api-token-display');

        generateBtn.disabled = true;
        generateBtn.textContent = 'Generating...';

        try {
            const response = await fetch('/api/auth/api-token', {
                method: 'GET',
                headers: Api.getHeaders()
            });

            const data = await Api.handleResponse(response);
            tokenInput.value = data.token;
            Toast.show('Token generated successfully!', 'success');
        } catch (error) {
            Toast.show('Failed to generate token', 'error');
            console.error('Token generation error:', error);
        } finally {
            generateBtn.disabled = false;
            generateBtn.textContent = 'Generate';
        }
    },

    copyToken() {
        const tokenInput = document.getElementById('api-token-display');
        const token = tokenInput.value;

        if (!token) {
            Toast.show('No token to copy', 'error');
            return;
        }

        navigator.clipboard.writeText(token).then(() => {
            Toast.show('Token copied to clipboard!', 'success');
        }).catch(() => {
            // Fallback for older browsers
            tokenInput.select();
            document.execCommand('copy');
            Toast.show('Token copied to clipboard!', 'success');
        });
    }
};

// Initialize when DOM loads
document.addEventListener('DOMContentLoaded', () => Settings.init());