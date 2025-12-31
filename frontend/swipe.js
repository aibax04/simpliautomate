class SwipeApp {
    constructor() {
        this.stack = document.getElementById('card-stack');
        this.prefModal = document.getElementById('pref-modal');
        this.resultModal = document.getElementById('result-modal');
        this.cards = [];
        this.currentNews = null;
        this.currentPrefs = null;
        this.generatedPost = null;

        this.allNews = [];
        this.currentFilter = 'All';

        this.imageOptionsModal = new ImageOptionsModal((imgPrefs) => {
            this.finalizeGeneration(imgPrefs);
        });

        this.init();
        this.bindGlobalEvents();
    }

    async init() {
        // Show loading state immediately
        this.stack.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Fetching latest news...</p>
            </div>
        `;

        try {
            const news = await Api.fetchNews();
            this.allNews = news;
            this.filterNews(this.currentFilter);
        } catch (e) {
            this.stack.innerHTML = `<div class="empty-state-message"><p>Failed to fetch news. Please try again.</p><button onclick="window.app.init()" class="btn-secondary">Retry</button></div>`;
            console.error(e);
        }
    }

    filterNews(category) {
        this.currentFilter = category;
        this.stack.innerHTML = '';
        this.cards = [];

        // Visual feedback
        this.stack.classList.remove('card-stack-filter-flash');
        void this.stack.offsetWidth; // trigger reflow
        this.stack.classList.add('card-stack-filter-flash');

        const filtered = this.allNews.filter(item => {
            if (category === 'All') return true;
            return item.domain.toLowerCase().includes(category.toLowerCase());
        });

        if (filtered.length === 0) {
            this.stack.innerHTML = `<div class="empty-state-message"><p>No ${category} news found for today.</p><button onclick="window.app.filterNews('All')" class="btn-secondary">Show All</button></div>`;
            return;
        }

        filtered.forEach((item, index) => {
            this.createCard(item, index);
        });
        this.renderStack();
    }

    createCard(data, index) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.backgroundColor = data.palette.bg;
        card.style.borderTop = `6px solid ${data.palette.accent} `;

        card.innerHTML = `
            <div class="category" style="color: ${data.palette.accent}">${data.domain}</div>
            <h2 style="color: ${data.palette.text}">${data.headline}</h2>
            <div class="content" style="color: ${data.palette.text}">${data.summary}</div>
            <div class="footer">
                <div class="source-info">
                    <strong style="color: ${data.palette.text}">${data.source_name}</strong>
                    <a href="${data.source_url}" target="_blank" class="source-link" style="color: ${data.palette.accent}">View Source</a>
                </div>
                <span style="color: ${data.palette.text}">${new Date().toLocaleDateString()}</span>
            </div>
        `;

        this.bindSwipe(card, data);
        card.__newsData = data; // Attach data for button access
        this.stack.appendChild(card);
        this.cards.push(card);
    }

    bindSwipe(card, data) {
        let startX, startY, moveX, moveY;
        let isDragging = false;

        const onStart = (e) => {
            isDragging = true;
            startX = e.type.includes('touch') ? e.touches[0].clientX : e.clientX;
            startY = e.type.includes('touch') ? e.touches[0].clientY : e.clientY;
            card.style.transition = 'none';
        };

        const onMove = (e) => {
            if (!isDragging) return;
            moveX = (e.type.includes('touch') ? e.touches[0].clientX : e.clientX) - startX;
            moveY = (e.type.includes('touch') ? e.touches[0].clientY : e.clientY) - startY;

            const rotation = moveX / 10;
            card.style.transform = `translate(${moveX}px, ${moveY}px) rotate(${rotation}deg)`;
        };

        const onEnd = () => {
            if (!isDragging) return;
            isDragging = false;
            card.style.transition = 'transform 0.5s cubic-bezier(0.175, 0.885, 0.32, 1.275)';

            if (Math.abs(moveX) > 120) {
                if (moveX > 0) this.handleRightSwipe(card, data);
                else this.handleLeftSwipe(card);
            } else {
                card.style.transform = '';
                this.renderStack();
            }
            moveX = moveY = 0;
        };

        card.addEventListener('mousedown', onStart);
        window.addEventListener('mousemove', onMove);
        window.addEventListener('mouseup', onEnd);

        card.addEventListener('touchstart', onStart);
        card.addEventListener('touchmove', onMove);
        card.addEventListener('touchend', onEnd);
    }

    handleLeftSwipe(card) {
        card.style.transform = 'translateX(-1000px) rotate(-30deg)';
        card.style.opacity = '0';
        this.popCard();
    }

    handleRightSwipe(card, data) {
        card.style.transform = 'translateX(1000px) rotate(30deg)';
        card.style.opacity = '0';
        this.currentNews = data;
        this.showPrefs();
        this.popCard();
    }

    popCard() {
        const card = this.cards.shift();
        setTimeout(() => {
            card.remove();
            if (this.cards.length === 0) this.init(); // Refetch if empty
            else this.renderStack();
        }, 300);
    }

    renderStack() {
        this.cards.forEach((card, i) => {
            card.style.zIndex = this.cards.length - i;
            card.style.transform = `scale(${1 - i * 0.05}) translateY(${i * 15}px)`;
            card.style.opacity = i > 2 ? 0 : 1;
        });
    }

    showPrefs() {
        this.prefModal.classList.remove('hidden');
    }

    bindGlobalEvents() {
        document.getElementById('close-modal').onclick = () => {
            this.prefModal.classList.add('hidden');
        };

        const filterSelect = document.getElementById('category-filter');
        if (filterSelect) {
            filterSelect.onchange = (e) => {
                this.filterNews(e.target.value);
            };
        }

        document.getElementById('next-to-image-btn').onclick = () => {
            const tone = document.getElementById('tone-select').value;
            const audience = document.getElementById('audience-select').value;
            const length = document.getElementById('length-select').value;

            this.currentPrefs = { tone, audience, length };

            this.prefModal.classList.add('hidden');
            this.imageOptionsModal.show();
        };

        document.getElementById('regenerate-img-btn').onclick = async () => {
            if (!this.currentNews || !this.currentPrefs) {
                if (window.Toast) window.Toast.show("Original context lost. Please try swiping again.", "error");
                return;
            }

            // Close result modal and re-trigger generation
            this.resultModal.classList.add('hidden');

            const tempId = 'temp_' + Date.now();
            if (window.queuePanel) {
                window.queuePanel.addOptimisticJob(tempId, this.currentNews.headline);
            }

            if (window.Toast) window.Toast.show("Regenerating post with same settings...", "info");

            try {
                const resp = await Api.enqueuePost(this.currentNews, this.currentPrefs);
                if (window.queuePanel) {
                    window.queuePanel.updateOptimisticId(tempId, resp.job_id);
                }
            } catch (e) {
                console.error(e);
                if (window.Toast) window.Toast.show("Failed to regenerate.", "error");
                if (window.queuePanel) window.queuePanel.removeJob(tempId);
            }
        };

        document.getElementById('publish-btn').onclick = async () => {
            if (!this.generatedPost) return;

            let finalPayload = "";
            if (this.generatedPost.caption_data && this.generatedPost.caption_data.full_caption) {
                finalPayload = this.generatedPost.caption_data.full_caption;
            } else {
                finalPayload = this.generatedPost.text;
            }

            const pBtn = document.getElementById('publish-btn');
            pBtn.disabled = true;
            pBtn.innerText = "Posting...";

            if (window.Toast) window.Toast.show("Publishing to LinkedIn...", "info");
            this.resultModal.classList.add('hidden');

            try {
                const res = await Api.publishPost(finalPayload, this.generatedPost.image_url);
                if (res.status === 'success') {
                    if (window.Toast) window.Toast.show(res.message || "Published successfully!", "success");
                } else {
                    if (window.Toast) window.Toast.show("Publishing error: " + (res.error || res.message), "error");
                }
            } catch (e) {
                if (window.Toast) window.Toast.show("Publishing failed: " + e.message, "error");
            } finally {
                pBtn.disabled = false;
                pBtn.innerText = "Post to LinkedIn";
            }
        };

        document.getElementById('edit-btn').onclick = () => {
            this.resultModal.classList.add('hidden');
            this.prefModal.classList.remove('hidden');
        };

        document.getElementById('skip-btn').onclick = () => {
            if (this.cards.length) this.handleLeftSwipe(this.cards[0]);
        };
        document.getElementById('approve-btn').onclick = () => {
            if (this.cards.length) {
                const card = this.cards[0];
                this.handleRightSwipe(card, card.__newsData);
            }
        };
    }

    async finalizeGeneration(imgPrefs) {
        const gBtn = document.getElementById('finalize-generate-btn');
        gBtn.disabled = true;
        gBtn.innerText = "Queueing...";

        const fullPrefs = {
            ...this.currentPrefs,
            image_style: imgPrefs.style,
            image_palette: imgPrefs.palette
        };
        this.currentPrefs = fullPrefs;

        const tempId = 'temp_' + Date.now();
        if (window.queuePanel) {
            window.queuePanel.addOptimisticJob(tempId, this.currentNews.headline);
        }

        if (window.Toast) window.Toast.show("Agent started working on your post...", "info");

        setTimeout(() => {
            gBtn.disabled = false;
            gBtn.innerText = "Generate Content";
        }, 500);

        try {
            const resp = await Api.enqueuePost(this.currentNews, fullPrefs);
            if (window.queuePanel) {
                window.queuePanel.updateOptimisticId(tempId, resp.job_id);
            }
            if (window.Toast) window.Toast.show("Job confirmed by agent core.", "success");
        } catch (e) {
            console.error(e);
            if (window.Toast) window.Toast.show("Failed to start agent found.", "error");
            if (window.queuePanel) window.queuePanel.removeJob(tempId);
        }
    }

    injectCards(newCards) {
        if (!newCards || newCards.length === 0) return;
        this.allNews = [...newCards, ...this.allNews];
        if (this.stack.innerHTML.includes('No news')) {
            this.stack.innerHTML = '';
        }
        newCards.forEach((item, index) => {
            const card = document.createElement('div');
            card.className = 'card';
            card.style.backgroundColor = item.palette.bg;
            card.style.borderTop = `6px solid ${item.palette.accent}`;
            card.innerHTML = `
                <div class="category" style="color: ${item.palette.accent}">${item.domain}</div>
                <h2 style="color: ${item.palette.text}">${item.headline}</h2>
                <div class="content" style="color: ${item.palette.text}">${item.summary}</div>
                <div class="footer">
                    <div class="source-info">
                        <strong style="color: ${item.palette.text}">${item.source_name}</strong>
                        <a href="${item.source_url}" target="_blank" class="source-link" style="color: ${item.palette.accent}">View Source</a>
                    </div>
                    <span style="color: ${item.palette.text}">${new Date().toLocaleDateString()}</span>
                </div>
            `;
            this.bindSwipe(card, item);
            this.cards.unshift(card);
            this.stack.insertBefore(card, this.stack.firstChild);
        });
        this.renderStack();
    }

    openResult(job) {
        const result = job.result || job;
        this.generatedPost = result;
        if (job.payload) {
            if (job.payload.news_item) this.currentNews = job.payload.news_item;
            if (job.payload.user_prefs) this.currentPrefs = job.payload.user_prefs;
        }
        const rawCaption = result.caption_data ? result.caption_data.body : result.text;
        const hashtags = result.caption_data ? result.caption_data.hashtags : "";
        const hook = result.caption_data ? result.caption_data.hook : "";
        const displayBody = hook ? `<strong>${hook}</strong>\n\n${rawCaption}` : rawCaption;
        const container = document.getElementById('post-preview');
        const timestamp = new Date().getTime();
        const imageUrl = result.image_url ? `${result.image_url}?t=${timestamp}` : null;
        container.innerHTML = `
            <div class="post-preview-container">
                <div class="preview-image">
                    ${imageUrl ? `<img src="${imageUrl}" alt="Generated Infographic" class="generated-post-image">` : '<div class="preview-image-fallback">Visualization generated...<br>(check network/path)</div>'}
                </div>
                <div class="preview-content">
                    <div class="preview-caption" contenteditable="true" spellcheck="false" style="outline:none; border:1px dashed transparent; padding:4px;">${displayBody}</div>
                    ${hashtags ? `<div class="preview-hashtags">${hashtags}</div>` : ''}
                    <div style="font-size:0.75rem; color:#999; margin-top:5px; text-align:right;">(Click text to edit)</div>
                </div>
            </div>
        `;
        this.resultModal.classList.remove('hidden');
    }
}

window.onload = () => {
    window.app = new SwipeApp();
};
