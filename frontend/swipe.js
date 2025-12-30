class SwipeApp {
    constructor() {
        this.stack = document.getElementById('card-stack');
        this.prefModal = document.getElementById('pref-modal');
        this.resultModal = document.getElementById('result-modal');
        this.cards = [];
        this.currentNews = null;
        this.generatedPost = null;

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
            this.stack.innerHTML = '';

            if (!news || news.length === 0) {
                this.stack.innerHTML = '<div class="empty-state-message"><p>No news found for today.</p><button onclick="window.app.init()" class="btn-secondary">Try Again</button></div>';
                return;
            }

            this.cards = [];
            news.forEach((item, index) => {
                this.createCard(item, index);
            });
            this.renderStack();
        } catch (e) {
            this.stack.innerHTML = `<div class="empty-state-message"><p>Failed to fetch news. Please try again.</p><button onclick="window.app.init()" class="btn-secondary">Retry</button></div>`;
            console.error(e);
        }
    }

    createCard(data, index) {
        const card = document.createElement('div');
        card.className = 'card';
        card.style.backgroundColor = data.palette.bg;
        card.style.borderTop = `6px solid ${data.palette.accent}`;

        card.innerHTML = `
            <div class="category" style="color: ${data.palette.accent}">${data.domain}</div>
            <h2 style="color: ${data.palette.text}">${data.headline}</h2>
            <div class="content">${data.summary}</div>
            <div class="footer">
                <div class="source-info">
                    <strong>${data.source_name}</strong>
                    <a href="${data.source_url}" target="_blank" class="source-link" style="color: ${data.palette.accent}">View Source</a>
                </div>
                <span>${new Date().toLocaleDateString()}</span>
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

        document.getElementById('generate-btn').onclick = async () => {
            const status = document.getElementById('generation-status');
            const gBtn = document.getElementById('generate-btn');

            // Optimistic UI: Don't disable button for long, just preventing double clicks
            gBtn.disabled = true;
            gBtn.innerText = "Queueing...";

            const prefs = {
                tone: document.getElementById('tone-select').value,
                audience: document.getElementById('audience-select').value,
                length: document.getElementById('length-select').value
            };

            // IMMEDIATE FEEDBACK: Close modal right away
            this.prefModal.classList.add('hidden');

            // Generate temp ID for immediate queue feedback
            const tempId = 'temp_' + Date.now();
            if (window.queuePanel) {
                window.queuePanel.addOptimisticJob(tempId, this.currentNews.headline);
            }

            if (window.Toast) window.Toast.show("Agent started working on your post...", "info");

            // Reset button state (since modal is closed, this prepares for next time)
            setTimeout(() => {
                gBtn.disabled = false;
                gBtn.innerText = "Generate Content";
                status.classList.add('hidden');
            }, 500);

            try {
                // Background API Call
                const resp = await Api.enqueuePost(this.currentNews, prefs);

                // Update the Optimistic Job ID with real one
                if (window.queuePanel) {
                    window.queuePanel.updateOptimisticId(tempId, resp.job_id);
                }

                // Confirm
                if (window.Toast) window.Toast.show("Job confirmed by agent core.", "success");

            } catch (e) {
                console.error(e);
                if (window.Toast) window.Toast.show("Failed to start agent found.", "error");

                // Remove the optimistic job since it failed
                if (window.queuePanel) {
                    window.queuePanel.removeJob(tempId);
                }
            }
        };




        document.getElementById('publish-btn').onclick = async () => {
            if (!this.generatedPost) return;

            // Prefer full_caption from metadata
            let finalPayload = "";
            if (this.generatedPost.caption_data && this.generatedPost.caption_data.full_caption) {
                finalPayload = this.generatedPost.caption_data.full_caption;
            } else {
                finalPayload = this.generatedPost.text;
            }

            const pBtn = document.getElementById('publish-btn');
            pBtn.disabled = true;
            pBtn.innerText = "Posting...";

            // IMMEDIATE FEEDBACK: Close modal, assume intent is captured
            if (window.Toast) window.Toast.show("Publishing to LinkedIn...", "info");

            // Keep modal open briefly to show state change, then close? 
            // Better UX: Close modal and continue in background.
            this.resultModal.classList.add('hidden');

            try {
                // Pass image_url from saved result
                const res = await Api.publishPost(finalPayload, this.generatedPost.image_url);

                if (res.status === 'success') {
                    if (window.Toast) window.Toast.show(res.message || "Published successfully!", "success");
                } else {
                    if (window.Toast) window.Toast.show("Publishing error: " + (res.error || res.message), "error");
                    // Re-open modal if failed? Maybe too jarring. Toast is enough.
                }
            } catch (e) {
                if (window.Toast) window.Toast.show("Publishing failed: " + e.message, "error");
            } finally {
                // Reset button for next time
                pBtn.disabled = false;
                pBtn.innerText = "Post to LinkedIn";
            }
        };

        document.getElementById('edit-btn').onclick = () => {
            this.resultModal.classList.add('hidden');
            this.prefModal.classList.remove('hidden');
        };

        // Manual controls
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

    injectCards(newCards) {
        // ... (existing implementation)
        if (!newCards || newCards.length === 0) return;

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
                <div class="content">${item.summary}</div>
                <div class="footer">
                    <div class="source-info">
                        <strong>${item.source_name}</strong>
                        <a href="${item.source_url}" target="_blank" class="source-link" style="color: ${item.palette.accent}">View Source</a>
                    </div>
                    <span>${new Date().toLocaleDateString()}</span>
                </div>
            `;

            this.bindSwipe(card, item);
            this.cards.unshift(card);
            this.stack.insertBefore(card, this.stack.firstChild);
        });

        this.renderStack();
    }

    openResult(result) {
        this.generatedPost = result;

        const rawCaption = result.caption_data ? result.caption_data.body : result.text;
        const hashtags = result.caption_data ? result.caption_data.hashtags : "";
        const hook = result.caption_data ? result.caption_data.hook : "";

        const displayBody = hook ? `<strong>${hook}</strong>\n\n${rawCaption}` : rawCaption;

        const container = document.getElementById('post-preview');
        // Add timestamp to prevent caching issues
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
