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

        this.allNews = [];
        this.currentFilter = 'All';

        this.imageOptionsModal = new ImageOptionsModal((imgPrefs) => {
            this.finalizeGeneration(imgPrefs);
        });

        this.init();
        this.bindGlobalEvents();
        this.bindCustomEvents();
        this.bindModalCloseEvents();
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

        // Reset modals if needed
        if (this.customModal) this.customModal.classList.add('hidden');
        if (this.customReviewModal) this.customReviewModal.classList.add('hidden');
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
            
            const imgEl = document.querySelector('.generated-post-image');
            if (imgEl) {
                const timestamp = new Date().getTime();
                imgEl.src = `${newImageUrl}?t=${timestamp}`;
                console.log("[DEBUG] UI Image updated:", imgEl.src);
            }

            // Hide edit container and restore main buttons
            this.handleImageEditCancel();

            const successMsg = "Image updated successfully!";
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

            // Update UI
            this.generatedPost.image_url = newImageUrl;
            this.originalImageUrl = newImageUrl;
            
            const imgEl = document.querySelector('.generated-post-image');
            if (imgEl) {
                imgEl.src = newImageUrl + '?t=' + new Date().getTime();
            }

            if (window.Toast) window.Toast.show("Image redesigned and updated successfully!", "success");

        } catch (e) {
            console.error("Regeneration Error:", e);
            if (window.Toast) window.Toast.show("Failed to regenerate image: " + e.message, "error");
        } finally {
            if (loader) loader.classList.add('hidden');
            if (overlay) overlay.classList.add('hidden');
            if (regenBtn) regenBtn.disabled = false;
        }
    }

    async finalizeGeneration(imgPrefs) {
        const gBtn = document.getElementById('finalize-generate-btn');
        gBtn.disabled = true;
        gBtn.innerText = "Queueing...";

        const productId = document.getElementById('product-select').value;

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
                resp = await Api.enqueueCustomPost(this.customPrompt, fullPrefs, productId ? parseInt(productId) : null);
                // Reset custom state
                this.resetCustomStages();
            } else {
                resp = await Api.enqueuePost(this.currentNews, fullPrefs, productId ? parseInt(productId) : null);
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
        this.currentJobId = job.id || job.job_id || null;
        this.currentPostId = result.post_id || null;
        this.originalImageUrl = result.image_url;

        console.log("[DEBUG] Opening result. Job ID:", this.currentJobId, "Post ID:", this.currentPostId);

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

        container.innerHTML = `
            <div class="post-preview-container">
                <div class="preview-image">
                    <div id="image-overlay" class="image-loading-overlay hidden">
                        <div class="mini-spinner"></div>
                        <span>AI Architect is redesigning...</span>
                    </div>
                    ${imageUrl ? `<img src="${imageUrl}" alt="Generated Infographic" class="generated-post-image">` : '<div class="preview-image-fallback">Visualization generated...<br>(check network/path)</div>'}
                </div>
                <div class="preview-content">
                    <div class="preview-caption" contenteditable="true" spellcheck="false" style="outline:none; border:1px dashed transparent; padding:4px;">${displayBody}</div>
                    ${hashtags ? `<div class="preview-hashtags">${hashtags}</div>` : ''}
                    
                    <div class="preview-footer" style="display: flex; flex-direction: column; gap: 12px; margin-top: 16px; padding-top: 16px; border-top: 1px solid var(--border);">
                        <div style="display: flex; justify-content: space-between; align-items: center; width: 100%;">
                            <div style="display: flex; gap: 8px; align-items: center; flex-wrap: wrap;">
                                <button id="regen-image-btn" class="btn-secondary" style="font-size: 0.75rem; padding: 6px 12px; background: #f0f0f0; color: #666; border: 1px solid #ddd;">
                                    <span class="icon" style="margin-right: 4px;">🔄</span> Regenerate
                                </button>
                                <button id="edit-image-btn" class="btn-secondary" style="font-size: 0.75rem; padding: 6px 12px; background: #f0f0f0; color: #666; border: 1px solid #ddd;">
                                    <span class="icon" style="margin-right: 4px;">🎨</span> Edit Image
                                </button>
                                <div id="regen-loader" class="mini-spinner hidden" style="width: 16px; height: 16px; border-width: 2px;"></div>
                            </div>
                            ${result.is_custom ? '' : `
                            <div class="source-attribution">
                                <span style="font-size: 0.75rem; color: var(--text-secondary); font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px;">Source:</span>
                                <a href="${this.currentNews ? this.currentNews.source_url : '#'}" target="_blank" style="font-size: 0.85rem; color: var(--primary); text-decoration: none; font-weight: 500; margin-left: 4px;">
                                    ${this.currentNews ? this.currentNews.source_name : 'Original Article'}
                                </a>
                            </div>
                            `}
                        </div>

                        <div style="font-size:0.75rem; color:#999; text-align: right;">(Click text to edit)</div>
                    </div>
                </div>
            </div>
        `;
        this.resultModal.classList.remove('hidden');
    }
}

window.addEventListener('DOMContentLoaded', () => {
    try {
        window.app = new SwipeApp();
    } catch (e) {
        console.error("Critical: SwipeApp failed to initialize", e);
    }
});
