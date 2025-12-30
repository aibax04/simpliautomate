const Api = {
    async fetchNews() {
        try {
            const response = await fetch('/api/fetch-news');
            return await response.json();
        } catch (e) {
            console.error("API Error:", e);
            return [];
        }
    },

    async generatePost(newsItem, prefs) {
        // Keeps existing logic valid but we prefer enqueue now
        try {
            const response = await fetch('/api/generate-post', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ news: newsItem, prefs })
            });
            return await response.json();
        } catch (e) {
            console.error("API Error:", e);
            throw e;
        }
    },

    async enqueuePost(newsItem, prefs) {
        try {
            const response = await fetch('/api/enqueue-post', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ news_item: newsItem, user_prefs: prefs })
            });
            const data = await response.json();
            return data;
        } catch (e) {
            console.error("Queue Error:", e);
            throw e;
        }
    },

    async getQueueStatus() {
        try {
            const response = await fetch('/api/queue-status');
            return await response.json();
        } catch (e) {
            console.error("Queue Status Error:", e);
            return [];
        }
    },

    async getJobResult(jobId) {
        try {
            const response = await fetch(`/api/job-result/${jobId}`);
            return await response.json();
        } catch (e) {
            console.error("Job Result Error:", e);
            return null;
        }
    },

    async publishPost(content, imageUrl) {
        try {
            const response = await fetch('/api/post-linkedin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content, image_url: imageUrl })
            });
            return await response.json();
        } catch (e) {
            console.error("API Error:", e);
            return { error: "Failed to publish." };
        }
    }
};
