class SwipeApp {
    constructor() {
        this.stack = document.getElementById('card-stack');
        this.prefModal = document.getElementById('pref-modal');
        this.resultModal = document.getElementById('result-modal');
        this.customModal = document.getElementById('custom-post-modal');
        this.customReviewModal = document.getElementById('custom-review-modal');
        this.activeCustomTab = 'custom-prompt';
        this.cards = [];
        this.currentNews = null;
        this.currentPrefs = null;
        this.generatedPost = null;
        this.isCustomPost = false;
        this.customPrompt = "";

        // Image comparison state
        this.previousImageUrl = null;
        this.currentImageUrl = null;
        this.hasComparisonImage = false;

        // Recent posts navigation
        this.recentPosts = [];
        this.currentPostIndex = -1;

        this.allNews = [];
        this.allNews = [];
        this.currentFilter = 'All';
        this.viewMode = 'swipe'; // 'swipe' or 'list'
        this.viewSelect = document.getElementById('view-mode-selector');
        this.listView = document.getElementById('list-view-container');
        this.controls = document.getElementById('controls');
        this.swipeContainer = document.getElementById('swipe-container');

        this.imageOptionsModal = new ImageOptionsModal((imgPrefs) => {
            this.finalizeGeneration(imgPrefs);
        });

        this.init();
        this.bindGlobalEvents();
        this.bindCustomEvents();
        this.bindModalCloseEvents();
    }

    setWatchingJob(jobId) {
        this.watchingJobId = jobId;
    }

    checkWatch(job) {
        // Safe string comparison for IDs
        const watchId = String(this.watchingJobId);
        const jobId = String(job.id || job.job_id);

        if (this.watchingJobId && jobId === watchId) {
            console.log(`[SwipeApp] Watch hit for job ${watchId}. Status: ${job.status}`);
            if (job.status === 'ready') {
                this.watchingJobId = null; // Stop watching
                console.log("[SwipeApp] Job ready, auto-opening...");
                this.openResult(job);
                if (window.Toast) window.Toast.show("Your post is ready!", "success");
            }
        }
    }

    bindModalCloseEvents() {
        // Find all modals and their close buttons
        document.querySelectorAll('.modal').forEach(modal => {
            const closeBtn = modal.querySelector('.close-modal-btn');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    modal.classList.add('hidden');
                    if (modal === this.customModal || modal === this.customReviewModal) {
                        this.isCustomPost = false;
                        this.resetCustomStages();
                    }
                });
            }
        });
    }

    bindCustomEvents() {
        console.log("Binding Custom Post events...");
        const closeCustomBtn = document.getElementById('close-custom-modal');
        const nextToPrefsBtn = document.getElementById('next-to-prefs-custom-btn');
        const generateDetailedBtn = document.getElementById('generate-detailed-prompt-btn');
        const backToInputBtn = document.getElementById('back-to-input-btn');
        const regenerateBtn = document.getElementById('regenerate-prompt-btn');

        // Tab switching for custom input
        const customTabs = document.querySelectorAll('.custom-tab-btn');
        const customContents = document.querySelectorAll('.custom-tab-content');

        if (customTabs.length > 0) {
            customTabs.forEach(btn => {
                btn.addEventListener('click', () => {
                    customTabs.forEach(b => b.classList.remove('active'));
                    customContents.forEach(c => c.classList.add('hidden'));
                    btn.classList.add('active');
                    this.activeCustomTab = btn.dataset.tab;
                    const stage = document.getElementById(`stage-${this.activeCustomTab}`);
                    if (stage) stage.classList.remove('hidden');
                });
            });
        }

        if (closeCustomBtn) {
            closeCustomBtn.addEventListener('click', () => {
                if (this.customModal) {
                    this.customModal.classList.add('hidden');
                    this.isCustomPost = false;
                    this.resetCustomStages();
                }
            });
        }

        if (generateDetailedBtn) {
            generateDetailedBtn.addEventListener('click', async () => {
                console.log("[DEBUG] Generate Prompt Button Clicked");
                const rawPromptEl = document.getElementById('custom-raw-prompt');
                const urlInputEl = document.getElementById('custom-url-input');
                const fileInputEl = document.getElementById('custom-file-input');

                const rawPrompt = rawPromptEl ? rawPromptEl.value.trim() : "";
                const url = urlInputEl ? urlInputEl.value.trim() : "";

                const formData = new FormData();
                let hasInput = false;

                if (this.activeCustomTab === 'custom-prompt' && rawPrompt) {
                    formData.append('raw_prompt', rawPrompt);
                    hasInput = true;
                } else if (this.activeCustomTab === 'custom-url' && url) {
                    formData.append('url_data', url);
                    hasInput = true;
                } else if (this.activeCustomTab === 'custom-pdf' && fileInputEl && fileInputEl.files[0]) {
                    formData.append('file', fileInputEl.files[0]);
                    hasInput = true;
                }

                if (!hasInput) {
                    alert("Please provide a prompt, URL, or file first.");
                    return;
                }

                // Transition modals immediately
                if (this.customModal) this.customModal.classList.add('hidden');
                if (this.customReviewModal) this.customReviewModal.classList.remove('hidden');

                if (typeof Toast !== 'undefined') {
                    Toast.show("Strategic prompt is being crafted by AI...", "info");
                }

                const reviewContent = document.getElementById('custom-review-content');
                const customGenStatus = document.getElementById('custom-gen-status');

                if (customGenStatus) customGenStatus.classList.remove('hidden');
                if (reviewContent) reviewContent.classList.add('hidden');

                try {
                    console.log("[DEBUG] Fetching expanded prompt...");
                    const response = await fetch('/api/generate-detailed-prompt', {
                        method: 'POST',
                        headers: Api.getAuthHeaders(),
                        body: formData
                    });

                    if (!response.ok) {
                        const errorData = await response.json().catch(() => ({ detail: "Unknown error" }));
                        throw new Error(errorData.detail || "Failed to generate detailed prompt");
                    }

                    const data = await response.json();
                    console.log("[DEBUG] Expanded prompt received successfully.");
                    const promptArea = document.getElementById('custom-detailed-prompt');
                    if (promptArea) {
                        promptArea.value = data.detailed_prompt;
                    }

                } catch (e) {
                    console.error("Prompt expansion error:", e);
                    if (typeof Toast !== 'undefined') {
                        Toast.show("AI Architect error: " + e.message, "error");
                    }
                    // Return to step 1
                    if (this.customReviewModal) this.customReviewModal.classList.add('hidden');
                    if (this.customModal) this.customModal.classList.remove('hidden');
                } finally {
                    if (customGenStatus) customGenStatus.classList.add('hidden');
                    if (reviewContent) reviewContent.classList.remove('hidden');
                }
            });
        }

        if (backToInputBtn) {
            backToInputBtn.addEventListener('click', () => {
                if (this.customReviewModal) this.customReviewModal.classList.add('hidden');
                if (this.customModal) this.customModal.classList.remove('hidden');
            });
        }

        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', () => {
                console.log("Regenerate clicked.");
                generateDetailedBtn.click();
            });
        }

        if (nextToPrefsBtn) {
            nextToPrefsBtn.addEventListener('click', () => {
                const detailedPrompt = document.getElementById('custom-detailed-prompt').value.trim();
                if (!detailedPrompt) {
                    alert("Prompt cannot be empty.");
                    return;
                }
                this.customPrompt = detailedPrompt;
                if (this.customReviewModal) this.customReviewModal.classList.add('hidden');
                this.showPrefs();
            });
        }
    }

    resetCustomStages() {
        this.activeCustomTab = 'custom-prompt';
        const rawPromptEl = document.getElementById('custom-raw-prompt');
        const urlInputEl = document.getElementById('custom-url-input');
        const fileInputEl = document.getElementById('custom-file-input');
        const promptArea = document.getElementById('custom-detailed-prompt');

        if (rawPromptEl) rawPromptEl.value = '';
        if (urlInputEl) urlInputEl.value = '';
        if (fileInputEl) fileInputEl.value = '';
        if (promptArea) promptArea.value = '';

        // Reset tab UI
        const customTabs = document.querySelectorAll('.custom-tab-btn');
        const customContents = document.querySelectorAll('.custom-tab-content');
        if (customTabs.length > 0) {
            customTabs.forEach(btn => btn.classList.remove('active'));
            customTabs[0].classList.add('active');
        }
        if (customContents.length > 0) {
            customContents.forEach(c => c.classList.add('hidden'));
            const defaultStage = document.getElementById('stage-custom-prompt');
            if (defaultStage) defaultStage.classList.remove('hidden');
        }

        if (this.customModal) this.customModal.classList.add('hidden');
        if (this.customReviewModal) this.customReviewModal.classList.add('hidden');

        // CRITICAL: Reset the custom flag so news card swipes work correctly
        this.isCustomPost = false;
    }

    showCustomPostModal() {
        if (this.customModal) {
            this.resetCustomStages();
            this.customModal.classList.remove('hidden');
            this.isCustomPost = true;
        }
    }

    async init() {
        // Show loading state immediately
        const loadingHtml = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Fetching latest news...</p>
            </div>
        `;

        if (this.viewMode === 'list') {
            this.listView.innerHTML = loadingHtml;
        } else {
            this.stack.innerHTML = loadingHtml;
        }

        this.fetchUser();

        try {
            const news = await Api.fetchNews();
            this.allNews = news;
            this.filterNews(this.currentFilter);
        } catch (e) {
            const errorHtml = `<div class="empty-state-message"><p>Failed to fetch news. Please try again.</p><button onclick="window.app.init()" class="btn-secondary">Retry</button></div>`;
            if (this.viewMode === 'list') {
                this.listView.innerHTML = errorHtml;
            } else {
                this.stack.innerHTML = errorHtml;
            }
            console.error(e);
        }
    }

    async fetchUser() {
        try {
            const user = await Api.fetchUserMe();
            if (user) {
                const nameLabel = document.getElementById('user-display-name');
                if (nameLabel) nameLabel.innerText = user.username;
            }
        } catch (e) {
            console.error("Failed to fetch user:", e);
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

        // CRITICAL FIX: Ensure stack is rendered effectively in Swipe Mode
        if (this.viewMode === 'list') {
            this.renderListView();
        } else {
            this.renderStack();
        }
    }

    createCard(data, index) {
        // Safe default palette if missing from backend
        const palette = data.palette || {
            bg: '#FFFFFF',
            text: '#1A1F23',
            accent: '#2563EB' // Blue accent
        };

        const card = document.createElement('div');
        card.className = 'card';
        card.style.backgroundColor = palette.bg;
        card.style.borderTop = `6px solid ${palette.accent}`;

        card.innerHTML = `
            <div class="category" style="color: ${palette.accent}">${data.domain}</div>
            <h2 style="color: ${palette.text}">${data.headline}</h2>
            <div class="content" style="color: ${palette.text}">${data.summary}</div>
            <div class="footer">
                <div class="source-info">
                    <strong style="color: ${palette.text}">${data.source_name}</strong>
                    <a href="${data.source_url}" target="_blank" class="source-link" style="color: ${palette.accent}">View Source</a>
                </div>
                <span style="color: ${palette.text}">${new Date().toLocaleDateString()}</span>
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

        // Ensure we are in News Post mode
        this.isCustomPost = false;
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
        if (this.viewSelect) {
            this.viewSelect.addEventListener('change', (e) => {
                this.switchView(e.target.value);
            });
        }

        const closeModal = document.getElementById('close-modal');
        if (closeModal) {
            closeModal.addEventListener('click', () => {
                if (this.prefModal) this.prefModal.classList.add('hidden');
            });
        }

        const filterSelect = document.getElementById('category-filter');
        if (filterSelect) {
            filterSelect.addEventListener('change', (e) => {
                this.filterNews(e.target.value);
            });
        }

        const searchInput = document.getElementById('news-search-input');
        if (searchInput) {
            searchInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    this.performSearch(searchInput.value.trim());
                }
            });
        }

        const nextToImageBtn = document.getElementById('next-to-image-btn');
        if (nextToImageBtn) {
            nextToImageBtn.addEventListener('click', () => {
                const toneSelect = document.getElementById('tone-select');
                const audienceSelect = document.getElementById('audience-select');
                const lengthSelect = document.getElementById('length-select');

                if (!toneSelect || !audienceSelect || !lengthSelect) return;

                const tone = toneSelect.value;
                const audience = audienceSelect.value;
                const length = lengthSelect.value;

                this.currentPrefs = { tone, audience, length };

                if (this.prefModal) this.prefModal.classList.add('hidden');
                if (this.imageOptionsModal) this.imageOptionsModal.show();
            });
        }

        // REMOVED OLD REGENERATE BUTTON LOGIC (Full post regeneration)
        // This is replaced by the new Image-Only Regeneration below.

        const downloadBtn = document.getElementById('download-img-btn');
        if (downloadBtn) {
            downloadBtn.addEventListener('click', () => {
                if (!this.generatedPost || !this.generatedPost.image_url) {
                    if (window.Toast) window.Toast.show("No image available to download.", "error");
                    return;
                }

                const imageUrl = this.generatedPost.image_url;
                const link = document.createElement('a');
                link.href = imageUrl;
                const filename = imageUrl.split('/').pop() || 'simplii-post.png';
                link.download = filename;
                document.body.appendChild(link);
                link.click();
                document.body.removeChild(link);

                if (window.Toast) window.Toast.show("Starting image download...");
            });
        }

        const copyCaptionBtn = document.getElementById('copy-caption-btn');
        if (copyCaptionBtn) {
            copyCaptionBtn.addEventListener('click', () => {
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
            });
        }

        const copyImageBtn = document.getElementById('copy-image-btn');
        if (copyImageBtn) {
            copyImageBtn.addEventListener('click', async () => {
                if (!this.generatedPost || !this.generatedPost.image_url) {
                    if (window.Toast) window.Toast.show("No image to copy.", "error");
                    return;
                }

                if (window.Toast) window.Toast.show("Preparing image for clipboard...", "info");

                try {
                    const response = await fetch(this.generatedPost.image_url);
                    const blob = await response.blob();

                    const item = new ClipboardItem({ [blob.type]: blob });
                    await navigator.clipboard.write([item]);

                    if (window.Toast) window.Toast.show("Image copied to clipboard!");
                } catch (err) {
                    console.error('Image copy error:', err);
                    navigator.clipboard.writeText(window.location.origin + this.generatedPost.image_url).then(() => {
                        if (window.Toast) window.Toast.show("Direct copy failed. Image URL copied instead.", "info");
                    });
                }
            });
        }

        const publishBtn = document.getElementById('publish-btn');
        if (publishBtn) {
            publishBtn.addEventListener('click', async () => {
                if (!this.generatedPost) return;

                let finalPayload = "";
                if (this.generatedPost.caption_data && this.generatedPost.caption_data.full_caption) {
                    finalPayload = this.generatedPost.caption_data.full_caption;
                } else {
                    finalPayload = this.generatedPost.text;
                }

                publishBtn.disabled = true;
                const originalText = publishBtn.innerText;
                publishBtn.innerText = "Posting...";

                if (window.Toast) window.Toast.show("Publishing to LinkedIn...", "info");
                if (this.resultModal) this.resultModal.classList.add('hidden');

                const accountId = LinkedInAccounts.getSelectedAccountId('post-account-selector');

                try {
                    const res = await Api.publishPost(finalPayload, this.generatedPost.image_url, accountId);
                    if (res.status === 'success') {
                        if (window.Toast) window.Toast.show(res.message || "Published successfully!", "success");
                    } else {
                        if (window.Toast) window.Toast.show("Publishing error: " + (res.error || res.message), "error");
                    }
                } catch (e) {
                    if (window.Toast) window.Toast.show("Publishing failed: " + e.message, "error");
                } finally {
                    publishBtn.disabled = false;
                    publishBtn.innerText = originalText;
                }
            });
        }

        const editBtn = document.getElementById('edit-btn');
        if (editBtn) {
            editBtn.addEventListener('click', () => {
                if (this.resultModal) this.resultModal.classList.add('hidden');
                if (this.prefModal) this.prefModal.classList.remove('hidden');
            });
        }

        const skipBtn = document.getElementById('skip-btn');
        if (skipBtn) {
            skipBtn.addEventListener('click', () => {
                if (this.cards.length) this.handleLeftSwipe(this.cards[0]);
            });
        }

        const approveBtn = document.getElementById('approve-btn');
        if (approveBtn) {
            approveBtn.addEventListener('click', () => {
                if (this.cards.length) {
                    const card = this.cards[0];
                    this.handleRightSwipe(card, card.__newsData);
                }
            });
        }

        // Keep global listener for dynamically injected AND static buttons (fallback)
        // This is the source of truth for all image action buttons
        // Keep global listener for dynamically injected AND static buttons (fallback)
        // This is the source of truth for all image action buttons
        document.body.addEventListener('click', async (e) => {
            const target = e.target;

            // 1. Image Regeneration
            const isRegen = target.id === 'regen-image-btn' || target.closest('#regen-image-btn');
            if (isRegen) {
                e.preventDefault();
                console.log("[DEBUG] Regen button clicked (global)");
                await this.handleImageRegeneration();
                return;
            }

            // 1.5. Caption Regeneration
            const isCaptionRegen = target.id === 'regen-caption-btn' || target.closest('#regen-caption-btn');
            if (isCaptionRegen) {
                e.preventDefault();
                console.log("[DEBUG] Caption regen button clicked (global handler)");
                await this.handleCaptionRegeneration();
                return;
            }

            // 2. Show Image Edit UI
            const isEditTrigger = target.id === 'edit-image-btn' ||
                target.id === 'edit-image-btn-main' ||
                target.closest('#edit-image-btn') ||
                target.closest('#edit-image-btn-main');
            if (isEditTrigger) {
                e.preventDefault();
                console.log("[DEBUG] Edit trigger clicked (global)");
                this.handleImageEditShow();
                return;
            }

            // 3. Submit Image Edits
            const isSubmitEdit = target.id === 'submit-edit-btn' || target.closest('#submit-edit-btn');
            if (isSubmitEdit) {
                e.preventDefault();
                console.log("[DEBUG] Submit Edit clicked (global)");
                await this.handleImageEditSubmit();
                return;
            }

            // 4. Cancel Image Edits
            const isCancelEdit = target.id === 'cancel-edit-btn' || target.closest('#cancel-edit-btn');
            if (isCancelEdit) {
                e.preventDefault();
                console.log("[DEBUG] Cancel Edit clicked (global)");
                this.handleImageEditCancel();
                return;
            }
        });

        // Add direct listeners for static buttons as a robust backup
        const staticSubmitBtn = document.getElementById('submit-edit-btn');
        if (staticSubmitBtn) {
            staticSubmitBtn.addEventListener('click', async (e) => {
                e.preventDefault();
                e.stopPropagation(); // Prevent bubbling to body listener
                console.log("[DEBUG] Direct Apply Edits clicked");
                await this.handleImageEditSubmit();
            });
        }
    }

    handleImageEditShow() {
        const container = document.getElementById('image-edit-container');
        if (container) {
            container.classList.remove('hidden');
            container.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }

        // Hide trigger buttons to focus on edit UI
        const mainEditBtn = document.getElementById('edit-image-btn-main');
        if (mainEditBtn) mainEditBtn.classList.add('hidden');

        const footerEditBtn = document.getElementById('edit-image-btn');
        if (footerEditBtn) footerEditBtn.classList.add('hidden');

        const regenBtn = document.getElementById('regen-image-btn');
        if (regenBtn) regenBtn.classList.add('hidden');
    }

    handleImageEditCancel() {
        const container = document.getElementById('image-edit-container');
        if (container) container.classList.add('hidden');

        const mainEditBtn = document.getElementById('edit-image-btn-main');
        if (mainEditBtn) mainEditBtn.classList.remove('hidden');

        const footerEditBtn = document.getElementById('edit-image-btn');
        if (footerEditBtn) footerEditBtn.classList.remove('hidden');

        const regenBtn = document.getElementById('regen-image-btn');
        if (regenBtn) regenBtn.classList.remove('hidden');

        const promptArea = document.getElementById('image-edit-prompt');
        if (promptArea) promptArea.value = '';
    }

    async handleImageEditSubmit() {
        console.log("[CRITICAL DEBUG] handleImageEditSubmit entered");

        const promptArea = document.getElementById('image-edit-prompt');
        const submitBtn = document.getElementById('submit-edit-btn');
        const loader = document.getElementById('regen-loader');
        const overlay = document.getElementById('image-overlay');

        // Prevent double-submission
        if (submitBtn && submitBtn.disabled) return;

        if (!promptArea) {
            console.error("[CRITICAL] promptArea not found");
            return;
        }

        const editPrompt = promptArea.value.trim();
        if (!editPrompt) {
            const msg = "Please describe the changes you want.";
            if (typeof Toast !== 'undefined') Toast.show(msg, "error");
            else if (window.Toast) window.Toast.show(msg, "error");
            else alert(msg);
            return;
        }

        // Store the previous image URL for comparison
        this.previousImageUrl = this.generatedPost?.image_url || this.originalImageUrl;

        // --- CONTEXT VALIDATION ---
        const finalPostId = this.currentPostId ||
            (this.generatedPost ? (this.generatedPost.post_id || this.generatedPost.id) : null);

        console.log("[DEBUG] handleImageEditSubmit context:", {
            jobId: this.currentJobId,
            postId: finalPostId,
            hasPost: !!this.generatedPost
        });

        if (!finalPostId && !this.currentJobId) {
            const errorMsg = "Technical Error: Post context lost. Please re-open from queue.";
            if (typeof Toast !== 'undefined') Toast.show(errorMsg, "error");
            else if (window.Toast) window.Toast.show(errorMsg, "error");
            else alert(errorMsg);
            return;
        }

        try {
            // Show loading state
            if (loader) loader.classList.remove('hidden');
            if (overlay) overlay.classList.remove('hidden');
            if (submitBtn) {
                // Only capture original text if it's not already "Applying..."
                if (submitBtn.innerText !== "Applying...") {
                    this.originalSubmitText = submitBtn.innerText;
                }
                submitBtn.disabled = true;
                submitBtn.innerText = "Applying...";
            }

            const infoMsg = "AI Architect is applying your manual edits...";
            if (typeof Toast !== 'undefined') Toast.show(infoMsg, "info");
            else if (window.Toast) window.Toast.show(infoMsg, "info");

            console.log("[DEBUG] Calling window.Api.editImageByPrompt...");
            const data = await window.Api.editImageByPrompt(this.currentJobId, finalPostId, editPrompt);
            console.log("[DEBUG] window.Api.editImageByPrompt response received");

            const newImageUrl = data.image_url;
            if (!newImageUrl) {
                throw new Error("AI successfully processed but returned no image URL.");
            }

            // Automatically update DB
            console.log("[DEBUG] Persisting edited image to DB...");
            await window.Api.updatePostImage(newImageUrl, finalPostId, editPrompt);

            // Update local state and UI
            if (this.generatedPost && typeof this.generatedPost === 'object') {
                this.generatedPost.image_url = newImageUrl;
            }
            this.originalImageUrl = newImageUrl;
            this.currentImageUrl = newImageUrl;
            this.hasComparisonImage = true;

            const imgEl = document.querySelector('.generated-post-image');
            if (imgEl) {
                const timestamp = new Date().getTime();
                imgEl.src = `${newImageUrl}?t=${timestamp}`;
                console.log("[DEBUG] UI Image updated:", imgEl.src);
            }

            // Add comparison slider UI
            this.addImageComparisonUI();

            // Hide edit container and restore main buttons
            this.handleImageEditCancel();

            const successMsg = "Image updated! Use the slider to compare with previous version.";
            if (typeof Toast !== 'undefined') Toast.show(successMsg, "success");
            else if (window.Toast) window.Toast.show(successMsg, "success");

        } catch (e) {
            console.error("[CRITICAL ERROR] Image Edit Failed:", e);
            const msg = e.message || "Something went wrong. Please try again.";
            if (typeof Toast !== 'undefined') Toast.show("Failed: " + msg, "error");
            else if (window.Toast) window.Toast.show("Failed: " + msg, "error");
            else alert("Failed: " + msg);
        } finally {
            if (loader) loader.classList.add('hidden');
            if (overlay) overlay.classList.add('hidden');
            if (submitBtn) {
                submitBtn.disabled = false;
                submitBtn.innerText = this.originalSubmitText || "Apply Edits";
            }
        }
    }

    async handleImageRegeneration() {
        const finalPostId = this.currentPostId || (this.generatedPost ? this.generatedPost.post_id || this.generatedPost.id : null);
        console.log("[DEBUG] Starting image regeneration. Job ID:", this.currentJobId, "Post ID:", finalPostId);

        // Store the previous image URL for comparison
        this.previousImageUrl = this.generatedPost?.image_url || this.originalImageUrl;

        const loader = document.getElementById('regen-loader');
        const overlay = document.getElementById('image-overlay');
        const regenBtn = document.getElementById('regen-image-btn');

        if (loader) loader.classList.remove('hidden');
        if (overlay) overlay.classList.remove('hidden');
        if (regenBtn) regenBtn.disabled = true;

        if (window.Toast) window.Toast.show("Redesigning image based on original plan...", "info");

        try {
            console.log("[DEBUG] Calling window.Api.regenerateImage...");
            const data = await window.Api.regenerateImage(this.currentJobId, finalPostId);
            const newImageUrl = data.image_url;

            if (!newImageUrl) throw new Error("AI failed to redesign image. Please try again.");

            // Automatically update DB
            console.log("[DEBUG] Calling window.Api.updatePostImage...");
            const updateResp = await window.Api.updatePostImage(newImageUrl, finalPostId);

            if (!updateResp) throw new Error("Failed to sync new image to database");

            // Store the new image and show comparison option
            this.generatedPost.image_url = newImageUrl;
            this.originalImageUrl = newImageUrl;
            this.currentImageUrl = newImageUrl;
            this.hasComparisonImage = true;

            const imgEl = document.querySelector('.generated-post-image');
            if (imgEl) {
                imgEl.src = newImageUrl + '?t=' + new Date().getTime();
            }

            // Add comparison slider UI
            this.addImageComparisonUI();

            if (window.Toast) window.Toast.show("Image redesigned! Use the slider to compare with previous version.", "success");

        } catch (e) {
            console.error("Regeneration Error:", e);
            if (window.Toast) window.Toast.show("Failed to regenerate image: " + e.message, "error");
        } finally {
            if (loader) loader.classList.add('hidden');
            if (overlay) overlay.classList.add('hidden');
            if (regenBtn) regenBtn.disabled = false;
        }
    }

    async handleCaptionRegeneration() {
        const finalPostId = this.currentPostId || (this.generatedPost ? this.generatedPost.post_id || this.generatedPost.id : null);
        console.log("[DEBUG] Starting caption regeneration. Job ID:", this.currentJobId, "Post ID:", finalPostId);

        const captionBtn = document.getElementById('regen-caption-btn');

        if (captionBtn) {
            captionBtn.disabled = true;
            captionBtn.innerHTML = '<div class="mini-spinner" style="width: 12px; height: 12px; border-width: 1px;"></div>';
        }

        if (window.Toast) window.Toast.show("Regenerating caption...", "info");

        try {
            console.log("[DEBUG] Calling window.Api.regenerateCaption...");
            const data = await window.Api.regenerateCaption(this.currentJobId, finalPostId);

            if (!data) throw new Error("Caption regeneration returned empty response");

            // Update the caption in the UI
            const captionEl = document.querySelector('.preview-caption');
            if (captionEl) {
                captionEl.textContent = data.caption || data.preview_text || "Caption generated...";
            }

            // Update hashtags if present
            if (data.hashtags) {
                let hashtagsEl = document.querySelector('.preview-hashtags');
                if (!hashtagsEl) {
                    // Create hashtags element if it doesn't exist
                    const previewContent = document.querySelector('.preview-content');
                    if (previewContent) {
                        hashtagsEl = document.createElement('div');
                        hashtagsEl.className = 'preview-hashtags';
                        previewContent.appendChild(hashtagsEl);
                    }
                }
                if (hashtagsEl) {
                    hashtagsEl.innerHTML = data.hashtags;
                }
            }

            // Update the generated post data
            if (this.generatedPost) {
                this.generatedPost.text = data.caption;
                this.generatedPost.preview_text = data.preview_text;
                this.generatedPost.hashtags = data.hashtags;
                this.generatedPost.caption_data = data.caption_data;
            }

            if (window.Toast) window.Toast.show("Caption regenerated successfully!", "success");

            // NEW: Automatically update DB with the new caption
            console.log("[DEBUG] Persisting regenerated caption to DB...");
            await window.Api.updatePostCaption(data.caption, finalPostId, data.hashtags, data.caption_data);
            console.log("[DEBUG] Caption persisted successfully");

        } catch (e) {
            console.error("Caption Regeneration Error:", e);
            if (window.Toast) window.Toast.show("Failed to regenerate caption: " + e.message, "error");
        } finally {
            if (captionBtn) {
                captionBtn.disabled = false;
                captionBtn.innerHTML = `
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                        <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                    </svg>
                `;
            }
        }
    }

    async finalizeGeneration(imgPrefs) {
        const gBtn = document.getElementById('finalize-generate-btn');
        if (!gBtn) return;

        gBtn.disabled = true;
        gBtn.innerText = "Queueing...";

        const productSelect = document.getElementById('product-select');
        const productId = productSelect ? productSelect.value : null;

        const fullPrefs = {
            ...this.currentPrefs,
            image_style: imgPrefs.style,
            image_palette: imgPrefs.palette
        };
        this.currentPrefs = fullPrefs;

        const tempId = 'temp_' + Date.now();
        // Safe headline access
        const headline = this.isCustomPost ? "Custom Post" : (this.currentNews?.headline || "Untitled Post");

        if (window.queuePanel) {
            window.queuePanel.addOptimisticJob(tempId, headline);
        }

        if (window.Toast) window.Toast.show("Agent started working on your post...", "info");

        try {
            let resp;
            if (this.isCustomPost) {
                resp = await Api.enqueueCustomPost(this.customPrompt, fullPrefs, productId ? parseInt(productId) : null);
                // Reset custom state
                this.resetCustomStages();
            } else {
                resp = await Api.enqueuePost(this.currentNews, fullPrefs, productId ? parseInt(productId) : null);
            }

            if (window.queuePanel) {
                window.queuePanel.updateOptimisticId(tempId, resp.job_id);
                // Force immediate sync
                window.queuePanel.fetchJobs();

                // Auto-open logic
                if (this.setWatchingJob) {
                    this.setWatchingJob(resp.job_id);
                }
            }
            if (window.Toast) window.Toast.show("Job confirmed by agent core.", "success");

            // Close modal and reset button to allow next post
            document.getElementById('image-options-modal').classList.add('hidden');
            gBtn.disabled = false;
            gBtn.innerText = "Queue Job";
        } catch (e) {
            console.error("Queueing error (likely transient):", e);
            // removing error toast as per user request to avoid false alarms
            // if (window.Toast) window.Toast.show("Failed to start agent process.", "error");

            gBtn.disabled = false;
            gBtn.innerText = "Queue Job";
            if (window.queuePanel) window.queuePanel.removeJob(tempId);
        }
    }

    async performSearch(query) {
        if (!query) {
            this.init();
            return;
        }

        this.stack.innerHTML = `
            <div class="loading-state">
                <div class="spinner"></div>
                <p>Searching for "${query}"...</p>
            </div>
        `;

        try {
            const news = await Api.fetchNews(query);
            this.allNews = news;
            this.filterNews('All');
        } catch (e) {
            this.stack.innerHTML = `<div class="empty-state-message"><p>Search failed. Please try again.</p><button onclick="window.app.performSearch('${query}')" class="btn-secondary">Retry</button></div>`;
            console.error(e);
        }
    }

    injectCards(newCards) {
        if (!newCards || newCards.length === 0) return;
        this.allNews = [...newCards, ...this.allNews];
        if (this.stack.innerHTML.includes('No news')) {
            this.stack.innerHTML = '';
        }
        newCards.forEach((item, index) => {
            // Safe default palette
            const palette = item.palette || {
                bg: '#FFFFFF',
                text: '#1A1F23',
                accent: '#2563EB'
            };

            const card = document.createElement('div');
            card.className = 'card';
            card.style.backgroundColor = palette.bg;
            card.style.borderTop = `6px solid ${palette.accent}`;
            card.innerHTML = `
                <div class="category" style="color: ${palette.accent}">${item.domain}</div>
                <h2 style="color: ${palette.text}">${item.headline}</h2>
                <div class="content" style="color: ${palette.text}">${item.summary}</div>
                <div class="footer">
                    <div class="source-info">
                        <strong style="color: ${palette.text}">${item.source_name}</strong>
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
        console.log("[DEBUG] openResult called with job:", job);
        const result = job.result || job;
        console.log("[DEBUG] Result object:", result);
        console.log("[DEBUG] Image URL:", result.image_url);
        this.generatedPost = result;
        this.currentJobId = job.id || job.job_id || null;
        this.currentPostId = result.post_id || result.id || null;
        this.originalImageUrl = result.image_url;

        console.log("[DEBUG] Opening result. Job ID:", this.currentJobId, "Post ID:", this.currentPostId);

        // Add this post to recent posts for navigation
        this.addToRecentPosts(result);

        if (job.payload) {
            if (job.payload.news_item) this.currentNews = job.payload.news_item;
            if (job.payload.user_prefs) this.currentPrefs = job.payload.user_prefs;
        }

        // --- FEATURE 1: SAFE POST TITLE GENERATION ---
        let displayTitle = "Your Curated Post";
        if (this.currentNews && this.currentNews.headline && this.currentNews.headline !== "undefined") {
            displayTitle = this.currentNews.headline;
        } else if (result.caption_data && result.caption_data.hook) {
            // Fallback to hook/first sentence
            displayTitle = result.caption_data.hook.split('.')[0].substring(0, 60);
        } else if (result.text) {
            // Fallback to first line of text
            displayTitle = result.text.split('\n')[0].substring(0, 60);
        }

        const modalTitle = document.getElementById('result-modal-title');
        if (modalTitle) {
            modalTitle.innerText = displayTitle;
        }
        // ----------------------------------------------

        const rawCaption = result.caption_data ? result.caption_data.body : result.text;
        const hashtags = result.caption_data ? result.caption_data.hashtags : "";
        const hook = result.caption_data ? result.caption_data.hook : "";

        // Include the original news headline in the content display for context
        const headlinePrefix = (this.currentNews && !this.generatedPost.is_custom) ? `NEWS UPDATE: ${this.currentNews.headline}\n\n` : "";
        const displayBody = hook ? `${headlinePrefix}<strong>${hook}</strong>\n\n${rawCaption}` : `${headlinePrefix}${rawCaption}`;

        const container = document.getElementById('post-preview');
        const timestamp = new Date().getTime();
        const imageUrl = result.image_url ? `${result.image_url}?t=${timestamp}` : null;

        // Handle button visibility
        const copyImgBtn = document.getElementById('copy-image-btn');
        const downImgBtn = document.getElementById('download-img-btn');
        const editImgBtnMain = document.getElementById('edit-image-btn-main');

        if (copyImgBtn) copyImgBtn.style.display = result.image_url ? 'inline-block' : 'none';
        if (downImgBtn) downImgBtn.style.display = result.image_url ? 'inline-block' : 'none';
        if (editImgBtnMain) editImgBtnMain.style.display = result.image_url ? 'inline-block' : 'none';

        // Reset edit containers to hidden when opening a new result
        const editContainer = document.getElementById('image-edit-container');
        if (editContainer) editContainer.classList.add('hidden');
        if (editImgBtnMain) editImgBtnMain.classList.remove('hidden');

        console.log("[DEBUG] Rendering post result with imageUrl:", imageUrl);

        container.innerHTML = `
            <div class="post-preview-container">
                <div class="preview-image">
                    <div id="image-overlay" class="image-loading-overlay hidden">
                        <div class="mini-spinner"></div>
                        <span>AI Architect is redesigning...</span>
                    </div>
                    ${imageUrl ? `
                        <div class="image-container">
                            <img src="${imageUrl}" alt="Generated Infographic" class="generated-post-image">
                        </div>
                    ` : '<div class="preview-image-fallback">Visualization generated...<br>(check network/path)</div>'}
                </div>
                <div class="preview-content">
                    <div class="preview-caption" contenteditable="true" spellcheck="false" style="outline:none; border:1px dashed transparent; padding:4px;">${displayBody}</div>
                </div>



        ${hashtags ? `<div class="preview-hashtags">${hashtags}</div>` : ''}

        <div class="preview-footer" style="display: flex; flex-direction: column; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
                <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                    <button id="regen-caption-btn" class="btn-secondary" style="font-size: 0.75rem; padding: 6px 12px; background: #007bff; color: white; border: 1px solid #007bff;">
                        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin-right: 4px;">
                            <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                            <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                        </svg>
                        Caption
                    </button>
                    <button id="regen-image-btn" class="btn-secondary" style="font-size: 0.75rem; padding: 6px 12px; background: #f0f0f0; color: #666; border: 1px solid #ddd;">
                        Regenerate Image
                    </button>
                    <button id="edit-image-btn" class="btn-secondary" style="font-size: 0.75rem; padding: 6px 12px; background: #f0f0f0; color: #666; border: 1px solid #ddd;">
                        Edit
                    </button>
                    <div id="regen-loader" class="mini-spinner hidden" style="width: 16px; height: 16px; border-width: 2px;"></div>
                </div>
            </div>

            <div style="font-size:0.75rem; color:#999; text-align: right;">(Click text to edit)</div>
        </div>
    </div>
    `;

        // CRITICAL: Attach event listener immediately after HTML is set
        setTimeout(() => {
            const captionBtn = document.getElementById('regen-caption-btn');
            console.log("[DEBUG] Looking for caption button:", captionBtn);

            if (captionBtn) {
                console.log("[DEBUG] Found caption button, attaching listener");
                captionBtn.addEventListener('click', async (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    console.log("[DEBUG] Caption button clicked!");
                    await this.handleCaptionRegeneration();
                });

                // Make sure button is visible
                captionBtn.style.display = 'flex';
                captionBtn.style.visibility = 'visible';
                captionBtn.style.opacity = '1';

                console.log("[DEBUG] Caption button styles applied");
            } else {
                console.log("[DEBUG] Caption button NOT found in DOM");
            }
        }, 100);

        // Bind navigation events for recent posts
        this.bindNavigationEvents();
        this.updateNavigationButtons();

        this.resultModal.classList.remove('hidden');
    }
    switchView(mode) {
        this.viewMode = mode;
        const swipeActions = document.getElementById('swipe-view-actions');

        if (mode === 'list') {
            document.getElementById('card-stack').classList.add('hidden');
            document.getElementById('controls').classList.add('hidden');
            if (swipeActions) swipeActions.classList.add('hidden');

            this.listView.classList.remove('hidden');
            this.swipeContainer.classList.add('list-mode');
            this.renderListView();
        } else {
            document.getElementById('card-stack').classList.remove('hidden');
            document.getElementById('controls').classList.remove('hidden');
            if (swipeActions) swipeActions.classList.remove('hidden');

            this.listView.classList.add('hidden');
            this.swipeContainer.classList.remove('list-mode');
            // Ensure stack is rendered correctly
            this.renderStack();
        }
    }

    renderListView() {
        if (!this.allNews || this.allNews.length === 0) {
            this.listView.innerHTML = '<div class="empty-state-message" style="text-align:center; padding:40px; color:#64748B;">No news available.</div>';
            return;
        }

        const filtered = this.currentFilter === 'All'
            ? this.allNews
            : this.allNews.filter(n => n.domain && n.domain.toLowerCase().includes(this.currentFilter.toLowerCase()));

        if (filtered.length === 0) {
            let emptyHtml = `<div class="empty-state-message" style="text-align:center; padding:40px; color:#64748B;">No ${this.currentFilter} news found.`;
            if (this.currentFilter !== 'All') {
                emptyHtml += `<br><br><button onclick="window.app.filterNews('All')" class="btn-secondary" style="padding: 8px 16px; margin-top: 12px; cursor: pointer;">Show All</button>`;
            }
            emptyHtml += `</div>`;
            this.listView.innerHTML = emptyHtml;
            return;
        }

        let cardsHtml = '';

        filtered.forEach((item, index) => {
            // Create temporary ID for selection
            const tempId = `news_item_${index}`;
            window.app.newsCache = window.app.newsCache || {};
            window.app.newsCache[tempId] = item;

            // Extract keyword from domain (focused mapping for top 5 ventures)
            const keywordMap = {
                'HealthTech': 'Healthcare',
                'Legal': 'Legal',
                'Judiciary AI': 'Judiciary',
                'LLM Models': 'AI',
                'Media AI': 'Media'
            };

            const topic = item.domain || 'General';
            let keyword = keywordMap[topic] || topic;

            // Fallback mappings for partial matches
            if (!keywordMap[topic]) {
                if (topic.includes('Health')) keyword = 'Healthcare';
                else if (topic.includes('Fin')) keyword = 'Finance';
                else if (topic.includes('Legal')) keyword = 'Legal';
                else if (topic.includes('HR')) keyword = 'HR';
                else if (topic.includes('AI') || topic.includes('LLM') || topic.includes('NLP')) keyword = 'AI';
                else if (topic.includes('Tech')) keyword = 'Technology';
                else if (topic.includes('IoT')) keyword = 'IoT';
                else if (topic.includes('Marketing')) keyword = 'Marketing';
                else if (topic.includes('Secure')) keyword = 'Security';
                else if (topic.includes('Consumer')) keyword = 'Consumer';
                else if (topic.includes('Industrial')) keyword = 'Industry';
                else if (topic.includes('Urban')) keyword = 'Urban';
                else if (topic.includes('Civic')) keyword = 'Civic';
                else if (topic.includes('Ed')) keyword = 'Education';
                else keyword = 'Technology'; // Default fallback
            }

            // Clean description (remove undefined, limit length)
            let description = item.summary || '';
            if (description === 'undefined' || !description) {
                description = item.source_name ? `From ${item.source_name}` : 'Latest industry update';
            }
            description = description.length > 120 ? description.substring(0, 120) + '...' : description;

            cardsHtml += `
                <div class="news-card" onclick="window.app.selectNewsFromList('${tempId}')">
                    <div class="news-card-top">
                        <div class="news-card-headline">${item.headline}</div>
                        <div class="news-card-description">${description}</div>
                    </div>
                    <div class="news-card-bottom">
                        <span class="news-card-keyword">${keyword}</span>
                        <span class="news-card-read-link" onclick="event.stopPropagation(); window.open('${item.source_url}', '_blank')">Read full article</span>
                    </div>
                </div>
            `;
        });

        // Create clean two-column grid
        let html = `
            <div class="news-grid-container">
                ${cardsHtml}
            </div>

            <div style="text-align: center; padding: 30px; margin-top: 20px; border-top: 1px solid var(--border);">
                <button id="load-more-list-btn" onclick="window.app.loadMoreNews()" class="btn-primary" style="display: inline-flex; align-items: center; gap: 8px; padding: 12px 24px;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12a9 9 0 0 0-9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"></path><path d="M3 3v5h5"></path><path d="M3 12a9 9 0 0 0 9 9 9.75 9.75 0 0 0 6.74-2.74L21 16"></path><path d="M16 21h5v-5"></path></svg>
                    Reload More News
                </button>
            </div>
        `;

        this.listView.innerHTML = html;
    }

    async loadMoreNews() {
        // Show loading on button(s)
        const listBtn = document.getElementById('load-more-list-btn');
        const swipeBtn = document.getElementById('load-more-swipe-btn');

        const originalListText = listBtn ? listBtn.innerHTML : '';
        const originalSwipeText = swipeBtn ? swipeBtn.innerHTML : '';

        if (listBtn) {
            listBtn.disabled = true;
            listBtn.innerHTML = '<div class="mini-spinner" style="border-color: white; border-right-color: transparent;"></div> Loading...';
        }
        if (swipeBtn) {
            swipeBtn.disabled = true;
            swipeBtn.innerHTML = '<div class="mini-spinner" style="border-color: white; border-right-color: transparent;"></div> Loading...';
        }

        try {
            if (window.Toast) window.Toast.show("Fetching fresh news...", "info");

            // Force fetch
            const newNews = await Api.fetchNews(null, true);

            if (newNews && newNews.length > 0) {
                // Deduplicate based on source_url (simple check)
                const existingUrls = new Set(this.allNews.map(n => n.source_url));
                const uniqueNew = newNews.filter(n => !existingUrls.has(n.source_url));

                if (uniqueNew.length > 0) {
                    this.injectCards(uniqueNew);
                    if (window.Toast) window.Toast.show(`Added ${uniqueNew.length} new stories!`, "success");
                } else {
                    // Even if duplicates, we might want to refresh 'allNews' or just say nothing new found
                    if (window.Toast) window.Toast.show("No new unique stories found right now.", "info");
                }
            } else {
                if (window.Toast) window.Toast.show("No more news available at the moment.", "info");
            }

        } catch (e) {
            console.error("Load more error:", e);
            if (window.Toast) window.Toast.show("Failed to load more news.", "error");
        } finally {
            if (listBtn) {
                listBtn.disabled = false;
                listBtn.innerHTML = originalListText;
            }
            if (swipeBtn) {
                swipeBtn.disabled = false;
                swipeBtn.innerHTML = originalSwipeText;
            }
        }
    }

    selectNewsFromList(cacheId) {
        const item = this.newsCache[cacheId];
        if (!item) return;

        // Open Preference Modal directly, treating it like a Right Swipe
        this.currentNews = item;
        this.isCustomPost = false;
        this.showPrefs();
    }

    addImageComparisonUI() {
        if (!this.hasComparisonImage || !this.previousImageUrl) return;

        // Find the image container
        const imageContainer = document.querySelector('.image-container');
        if (!imageContainer) return;

        // Remove existing comparison UI if present
        const existingComparison = document.querySelector('.image-comparison-container');
        if (existingComparison) {
            existingComparison.remove();
        }

        // Add comparison UI
        const comparisonHTML = `
            <div class="image-comparison-container">
                <div class="image-comparison-slider">
                    <div class="comparison-labels">
                        <span class="previous-label">Previous</span>
                        <span class="current-label">New</span>
                    </div>
                    <input type="range" min="0" max="100" value="100" class="comparison-slider"
                           id="image-comparison-range">
                    <div class="slider-track"></div>
                </div>
                <div class="comparison-instruction">
                    Slide to compare images
                </div>
            </div>
        `;

        imageContainer.insertAdjacentHTML('afterend', comparisonHTML);

        // Add event listener for the slider
        const slider = document.getElementById('image-comparison-range');
        if (slider) {
            slider.addEventListener('input', (e) => {
                this.updateImageComparison(e.target.value);
            });
        }

        // Initialize comparison
        this.updateImageComparison(100);
    }

    updateImageComparison(sliderValue) {
        const mainImage = document.querySelector('.generated-post-image');
        const sliderTrack = document.querySelector('.slider-track');

        if (!mainImage) return;

        const percentage = sliderValue / 100;

        // Update the main image source based on slider position
        if (sliderValue < 50) {
            // Show previous image
            mainImage.src = this.previousImageUrl + '?t=' + new Date().getTime();
            if (sliderTrack) sliderTrack.style.width = '0%';
        } else {
            // Show current image
            mainImage.src = this.currentImageUrl + '?t=' + new Date().getTime();
            if (sliderTrack) sliderTrack.style.width = sliderValue + '%';
        }

        // Update slider track visual
        if (sliderTrack) {
            sliderTrack.style.width = sliderValue + '%';
        }
    }

    async loadRecentPosts() {
        console.log("[DEBUG] Loading recent posts from database...");

        try {
            // First try to load from database API
            const response = await window.Api.getRecentPosts(20);

            if (response && response.posts && response.posts.length > 0) {
                // Transform database posts to match our expected format
                this.recentPosts = response.posts.map(post => ({
                    id: post.id,
                    image_url: post.image_url,
                    text: post.caption,
                    caption_data: {
                        body: post.caption,
                        hashtags: "",
                        hook: post.caption ? post.caption.split('.')[0] : ""
                    },
                    created_at: post.created_at,
                    style: post.style,
                    palette: post.palette,
                    news_headline: post.news_headline,
                    posted_to_linkedin: post.posted_to_linkedin,
                    last_image_edit_prompt: post.last_image_edit_prompt,
                    from_database: true
                }));

                console.log(`[DEBUG] Loaded ${this.recentPosts.length} posts from database`);
            } else {
                // Fallback to localStorage if no database posts
                console.log("[DEBUG] No posts from database, checking localStorage...");
                await this.loadRecentPostsFromLocalStorage();
            }
        } catch (error) {
            console.warn("[DEBUG] Failed to load from database, falling back to localStorage:", error);
            await this.loadRecentPostsFromLocalStorage();
        }

        // Update current index for navigation
        this.currentPostIndex = this.recentPosts.length > 0 ? 0 : -1;
    }

    async loadRecentPostsFromLocalStorage() {
        try {
            const stored = localStorage.getItem('recentPosts');
            if (stored) {
                const parsed = JSON.parse(stored);
                this.recentPosts = parsed.slice(0, 20); // Keep only last 20
                console.log(`[DEBUG] Loaded ${this.recentPosts.length} posts from localStorage`);
            } else {
                this.recentPosts = [];
                console.log("[DEBUG] No posts in localStorage");
            }
        } catch (error) {
            console.warn("[DEBUG] Could not load stored recent posts:", error);
            this.recentPosts = [];
        }
    }

    saveRecentPosts() {
        try {
            localStorage.setItem('recentPosts', JSON.stringify(this.recentPosts));
        } catch (error) {
            console.warn("[DEBUG] Could not save recent posts:", error);
        }
    }

    showPostInModal(postData, index = -1) {
        // Update current index if provided
        if (index >= 0) {
            this.currentPostIndex = index;
        }

        // Update navigation buttons
        this.updateNavigationButtons();

        // Add navigation event listeners
        this.bindNavigationEvents();

        // Show the post in the modal (existing functionality)
        this.openResult({ result: postData, id: null });
    }

    updateNavigationButtons() {
        const prevBtn = document.getElementById('prev-post-btn');
        const nextBtn = document.getElementById('next-post-btn');

        console.log('[DEBUG] Updating navigation buttons. Index:', this.currentPostIndex, 'Total posts:', this.recentPosts.length);

        if (prevBtn) {
            const shouldDisable = this.currentPostIndex <= 0;
            prevBtn.disabled = shouldDisable;
            console.log('[DEBUG] Previous button disabled:', shouldDisable);
        }

        if (nextBtn) {
            const shouldDisable = this.currentPostIndex >= this.recentPosts.length - 1;
            nextBtn.disabled = shouldDisable;
            console.log('[DEBUG] Next button disabled:', shouldDisable);
        }

        // Update modal title to show position
        const titleEl = document.getElementById('result-modal-title');
        if (titleEl && this.recentPosts.length > 0) {
            const total = this.recentPosts.length;
            const current = this.currentPostIndex + 1;
            titleEl.textContent = `Your Curated Post (${current}/${total})`;
            console.log('[DEBUG] Updated modal title:', titleEl.textContent);
        }
    }

    navigateToPreviousPost() {
        if (this.currentPostIndex > 0) {
            this.currentPostIndex--;
            const postData = this.recentPosts[this.currentPostIndex];
            this.showPostInModal(postData, this.currentPostIndex);
        }
    }

    navigateToNextPost() {
        if (this.currentPostIndex < this.recentPosts.length - 1) {
            this.currentPostIndex++;
            const postData = this.recentPosts[this.currentPostIndex];
            this.showPostInModal(postData, this.currentPostIndex);
        }
    }

    bindNavigationEvents() {
        const prevBtn = document.getElementById('prev-post-btn');
        const nextBtn = document.getElementById('next-post-btn');

        console.log('[DEBUG] Binding navigation events. Prev btn:', !!prevBtn, 'Next btn:', !!nextBtn);

        if (prevBtn) {
            prevBtn.onclick = () => {
                console.log('[DEBUG] Previous button clicked');
                this.navigateToPreviousPost();
            };
        }

        if (nextBtn) {
            nextBtn.onclick = () => {
                console.log('[DEBUG] Next button clicked');
                this.navigateToNextPost();
            };
        }
    }

    addToRecentPosts(postData) {
        if (!postData) return;

        // Remove if already exists
        this.recentPosts = this.recentPosts.filter(post => post.id !== postData.id);

        // Create a standardized post object
        const standardizedPost = {
            id: postData.id || postData.post_id,
            image_url: postData.image_url || postData.image_path,
            text: postData.text || postData.caption,
            caption_data: postData.caption_data || {
                body: postData.caption || postData.text,
                hashtags: "",
                hook: (postData.caption || postData.text || "").split('.')[0]
            },
            created_at: postData.created_at || new Date().toISOString(),
            style: postData.style,
            palette: postData.palette,
            news_headline: postData.news_headline,
            posted_to_linkedin: postData.posted_to_linkedin,
            last_image_edit_prompt: postData.last_image_edit_prompt,
            from_database: postData.from_database || false
        };

        // Add to beginning of array
        this.recentPosts.unshift(standardizedPost);

        // Keep only last 20 posts
        if (this.recentPosts.length > 20) {
            this.recentPosts = this.recentPosts.slice(0, 20);
        }

        // Save to localStorage as backup
        this.saveRecentPosts();

        console.log(`[DEBUG] Added post to recent posts. Total: ${this.recentPosts.length}, From DB: ${standardizedPost.from_database}`);
    }
}

window.addEventListener('DOMContentLoaded', () => {
    try {
        window.app = new SwipeApp();
    } catch (e) {
        console.error("Critical: SwipeApp failed to initialize", e);
    }
});
