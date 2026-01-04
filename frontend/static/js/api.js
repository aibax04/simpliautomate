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

    async enqueuePost(newsItem, prefs, productId = null) {
        try {
            const body = { news_item: newsItem, user_prefs: prefs };
            if (productId) body.product_id = productId;
            
            const response = await fetch('/api/enqueue-post', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body)
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Queue Error:", e);
            throw e;
        }
    },

    async enqueueCustomPost(customPrompt, prefs, productId = null) {
        try {
            const body = { custom_prompt: customPrompt, user_prefs: prefs };
            if (productId) body.product_id = productId;

            const response = await fetch('/api/enqueue-post', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body)
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

    async publishPost(content, imageUrl, accountId) {
        try {
            const response = await fetch('/api/post-linkedin', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ 
                    content, 
                    image_url: imageUrl,
                    linkedin_account_id: accountId
                })
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("API Error:", e);
            return { error: "Failed to publish." };
        }
    },

    async getLinkedInAuthUrl() {
        const response = await fetch('/api/linkedin/auth-url', { headers: this.getHeaders() });
        return await this.handleResponse(response);
    },

    async connectLinkedIn(code) {
        const response = await fetch('/api/linkedin/connect', {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ code })
        });
        return await this.handleResponse(response);
    },

    async getLinkedInAccounts() {
        const response = await fetch('/api/linkedin/accounts', { headers: this.getHeaders() });
        return await this.handleResponse(response);
    },

    async disconnectLinkedInAccount(accountId) {
        const response = await fetch(`/api/linkedin/accounts/${accountId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        return await this.handleResponse(response);
    },

    // --- Scheduling & Email API ---
    async schedulePost(payload) {
        const response = await fetch('/api/scheduler/schedule', {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify(payload)
        });
        return await this.handleResponse(response);
    },

    async getScheduledPosts() {
        const response = await fetch('/api/scheduler/scheduled-posts', {
            headers: this.getHeaders()
        });
        return await this.handleResponse(response);
    },

    async cancelScheduledPost(postId) {
        const response = await fetch(`/api/scheduler/scheduled-posts/${postId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        return await this.handleResponse(response);
    },

    async sendTestEmail(email) {
        const response = await fetch('/api/scheduler/test-email', {
            method: 'POST',
            headers: this.getHeaders(),
            body: JSON.stringify({ email })
        });
        return await this.handleResponse(response);
    },

    async getProducts() {
        const response = await fetch('/api/products', { headers: this.getHeaders() });
        return await this.handleResponse(response);
    },

    async createProduct(formData) {
        const token = localStorage.getItem('simplii_token');
        const headers = {}; // Fetch will handle multipart/form-data
        if (token) {
            headers['Authorization'] = `Bearer ${token}`;
        }
        const response = await fetch('/api/products', {
            method: 'POST',
            headers: headers,
            body: formData
        });
        return await this.handleResponse(response);
    },

    async deleteProduct(productId) {
        const response = await fetch(`/api/products/${productId}`, {
            method: 'DELETE',
            headers: this.getHeaders()
        });
        return await this.handleResponse(response);
    },

    async generateBlog(topic, tone, length) {
        try {
            const response = await fetch('/api/generate-blog', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify({ topic, tone, length })
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Blog Generation Error:", e);
            throw e;
        }
    },

    async enqueueBlog(topic, tone, length, productId = null) {
        try {
            const body = { topic, tone, length };
            if (productId) body.product_id = productId;

            const response = await fetch('/api/enqueue-blog', {
                method: 'POST',
                headers: this.getHeaders(),
                body: JSON.stringify(body)
            });
            return await this.handleResponse(response);
        } catch (e) {
            console.error("Blog Enqueue Error:", e);
            throw e;
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
