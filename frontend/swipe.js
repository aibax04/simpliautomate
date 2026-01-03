class SwipeApp {
    constructor() {
        this.stack = document.getElementById('card-stack');
        this.prefModal = document.getElementById('pref-modal');
        this.resultModal = document.getElementById('result-modal');
        this.customModal = document.getElementById('custom-post-modal');
        this.cards = [];
        this.currentNews = null;
        this.currentPrefs = null;
        this.generatedPost = null;
        this.isCustomPost = false;
        this.customPrompt = "";

        this.allNews = [];
        this.currentFilter = 'All';

        this.imageOptionsModal = new ImageOptionsModal((imgPrefs) => {
            this.finalizeGeneration(imgPrefs);
        });

        this.init();
        this.bindGlobalEvents();
        this.bindCustomEvents();
    }

    bindCustomEvents() {
        const customBtn = document.getElementById('custom-post-btn');
        const closeCustomBtn = document.getElementById('close-custom-modal');
        const nextCustomBtn = document.getElementById('next-to-prefs-custom-btn');

        if (customBtn) {
            customBtn.onclick = () => {
                this.customModal.classList.remove('hidden');
                this.isCustomPost = true;
            };
        }

        if (closeCustomBtn) {
            closeCustomBtn.onclick = () => {
                this.customModal.classList.add('hidden');
                this.isCustomPost = false;
            };
        }

        if (nextCustomBtn) {
            nextCustomBtn.onclick = () => {
                const prompt = document.getElementById('custom-prompt-input').value.trim();
                if (!prompt) {
                    alert("Please enter a prompt.");
                    return;
                }
                this.customPrompt = prompt;
                this.customModal.classList.add('hidden');
                this.showPrefs();
            };
        }
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

        document.getElementById('download-img-btn').onclick = () => {
            if (!this.generatedPost || !this.generatedPost.image_url) {
                if (window.Toast) window.Toast.show("No image available to download.", "error");
                return;
            }

            const imageUrl = this.generatedPost.image_url;
            const link = document.createElement('a');
            link.href = imageUrl;
            // Extract filename from URL or use a default
            const filename = imageUrl.split('/').pop() || 'simplii-post.png';
            link.download = filename;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            
            if (window.Toast) window.Toast.show("Starting image download...");
        };

        document.getElementById('copy-caption-btn').onclick = () => {
            const captionEl = document.querySelector('.preview-caption');
            const hashtagsEl = document.querySelector('.preview-hashtags');
            
            if (!captionEl) {
                if (window.Toast) window.Toast.show("No caption found to copy.", "error");
                return;
            }

            let textToCopy = captionEl.innerText;
            if (hashtagsEl) {
                textToCopy += "\n\n" + hashtagsEl.innerText;
            }

            navigator.clipboard.writeText(textToCopy).then(() => {
                if (window.Toast) window.Toast.show("Caption copied to clipboard!");
            }).catch(err => {
                console.error('Copy error:', err);
                if (window.Toast) window.Toast.show("Failed to copy caption.", "error");
            });
        };

        document.getElementById('copy-image-btn').onclick = async () => {
            if (!this.generatedPost || !this.generatedPost.image_url) {
                if (window.Toast) window.Toast.show("No image to copy.", "error");
                return;
            }

            if (window.Toast) window.Toast.show("Preparing image for clipboard...", "info");

            try {
                const response = await fetch(this.generatedPost.image_url);
                const blob = await response.blob();
                
                // Clipboard API requires PNG for image copying in most browsers
                const item = new ClipboardItem({ [blob.type]: blob });
                await navigator.clipboard.write([item]);
                
                if (window.Toast) window.Toast.show("Image copied to clipboard!");
            } catch (err) {
                console.error('Image copy error:', err);
                // Fallback: Copy URL if direct blob copy fails
                navigator.clipboard.writeText(window.location.origin + this.generatedPost.image_url).then(() => {
                    if (window.Toast) window.Toast.show("Direct copy failed. Image URL copied instead.", "info");
                });
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
        const headline = this.isCustomPost ? "Custom Post" : this.currentNews.headline;
        
        if (window.queuePanel) {
            window.queuePanel.addOptimisticJob(tempId, headline);
        }

        if (window.Toast) window.Toast.show("Agent started working on your post...", "info");

        setTimeout(() => {
            gBtn.disabled = false;
            gBtn.innerText = "Generate Content";
        }, 500);

        try {
            let resp;
            if (this.isCustomPost) {
                resp = await Api.enqueueCustomPost(this.customPrompt, fullPrefs);
                // Reset custom state
                this.isCustomPost = false;
                this.customPrompt = "";
                document.getElementById('custom-prompt-input').value = "";
            } else {
                resp = await Api.enqueuePost(this.currentNews, fullPrefs);
            }

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
                    
                    <div class="preview-footer" style="display: flex; justify-content: space-between; align-items: center; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
                        ${result.is_custom ? '' : `
                        <div class="source-attribution">
                            <span style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Source:</span>
                            <a href="${this.currentNews ? this.currentNews.source_url : '#'}" target="_blank" style="font-size: 0.85rem; color: var(--primary); text-decoration: none; font-weight: 500; margin-left: 4px;">
                                ${this.currentNews ? this.currentNews.source_name : 'Original Article'}
                            </a>
                        </div>
                        `}
                        <div style="font-size:0.75rem; color:#999; margin-left: auto;">(Click text to edit)</div>
                    </div>
                </div>
            </div>
        `;
        this.resultModal.classList.remove('hidden');
    }
}

window.onload = () => {
    window.app = new SwipeApp();
};
