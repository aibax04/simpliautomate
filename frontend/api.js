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
        try {
            const response = await fetch('/api/generate-post', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ news: newsItem, prefs })
            });
            return await response.json();
        } catch (e) {
            console.error("API Error:", e);
            return { content: "Error generating content." };
        }
    },

    async publishPost(content) {
        try {
            const response = await fetch('/api/post-linkedin', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ content })
            });
            return await response.json();
        } catch (e) {
            console.error("API Error:", e);
            return { error: "Failed to publish." };
        }
    }
};
