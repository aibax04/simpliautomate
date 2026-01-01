const Api = {
    getHeaders() {
        const token = localStorage.getItem('simplii_token');
        const headers = { 'Content-Type': 'application/json' };
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        return headers;
    },

    async handleResponse(response) {
        if (response.status === 401) {
            localStorage.removeItem('simplii_token');
            window.location.href = '/login.html';
            throw new Error('Unauthorized');
        }
        return await response.json();
    },

    async fetchNews() {
        try {
            const response = await fetch('/api/fetch-news', {
                headers: this.getHeaders()
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("API Error:", e);
            return [];
        }
    },

    async generatePost(newsItem, prefs) {
        try {
            const response = await fetch('/api/generate-post', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ news: newsItem, prefs })
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("API Error:", e);
            throw e;
        }
    },

    async enqueuePost(newsItem, prefs) {
        try {
            const response = await fetch('/api/enqueue-post', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ news_item: newsItem, user_prefs: prefs })
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Queue Error:", e);
            throw e;
        }
    },

    async enqueueCustomPost(customPrompt, prefs) {
        try {
            const response = await fetch('/api/enqueue-post', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ custom_prompt: customPrompt, user_prefs: prefs })
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Queue Error:", e);
            throw e;
        }
    },

    async getQueueStatus() {
        try {
            const response = await fetch('/api/queue-status', {
                headers: this.getHeaders()
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Queue Status Error:", e);
            return [];
        }
    },

    async getJobResult(jobId) {
        try {
            const response = await fetch(`/api/job-result/${jobId}`, {
                headers: this.getHeaders()
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Job Result Error:", e);
            return null;
        }
    },

    async publishPost(content, imageUrl) {
        try {
            const response = await fetch('/api/post-linkedin', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ content, image_url: imageUrl })
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("API Error:", e);
            return { error: "Failed to publish." };
        }
    }
};

const Toast = {
    container: null,

    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },

    show(message, type = 'success') {
        this.init();
        const toast = document.createElement('div');
        toast.className = `toast ${type}`;

        let icon = '✓';
        if (type === 'error') icon = '✕';
        if (type === 'info') icon = 'ℹ';

        toast.innerHTML = `<span style="opacity:0.8; margin-right:5px;">${icon}</span> ${message}`;
        this.container.appendChild(toast);

        // Animate in
        requestAnimationFrame(() => {
            toast.classList.add('visible');
        });

        // Auto dismiss
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => {
                toast.remove();
            }, 300);
        }, 3000);
    }
};
