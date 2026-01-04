document.addEventListener('DOMContentLoaded', () => {
    const blogBtn = document.getElementById('blog-generator-btn');
    const blogCatModal = document.getElementById('blog-category-modal');
    const blogSettingsModal = document.getElementById('blog-settings-modal');
    const closeBlogCatModal = document.getElementById('close-blog-cat-modal');
    const backToCatsBtn = document.getElementById('back-to-cats-btn');
    const generateBlogBtn = document.getElementById('generate-blog-btn');
    
    const blogTopicInput = document.getElementById('blog-topic-input');
    const blogToneSelect = document.getElementById('blog-tone-select');
    const blogLengthSelect = document.getElementById('blog-length-select');
    const blogStatus = document.getElementById('blog-status');
    const blogStatusText = document.getElementById('blog-status-text');
    const catBoxes = document.querySelectorAll('.blog-cat-box');

    let selectedCategory = "";

    const blogResultModal = document.getElementById('blog-result-modal');
    const blogResultTitle = document.getElementById('blog-result-title');
    const blogResultContent = document.getElementById('blog-result-content');
    const closeBlogResult = document.getElementById('close-blog-result');
    const copyBlogBtn = document.getElementById('copy-blog-btn');
    const publishBlogBtn = document.getElementById('publish-blog-btn');

    if (!blogSettingsModal) return;

    // Open Category Modal
    // Note: blogBtn now uses an inline onclick in index.html for better reliability

    // Specific close listeners for buttons that aren't .close-modal-btn
    if (closeBlogCatModal) {
        closeBlogCatModal.addEventListener('click', () => {
            if (blogCatModal) blogCatModal.classList.add('hidden');
        });
    }

    if (closeBlogResult) {
        closeBlogResult.addEventListener('click', () => {
            if (blogResultModal) blogResultModal.classList.add('hidden');
        });
    }

    // Close buttons logic for blog modals (the X buttons)
    document.querySelectorAll('#blog-category-modal, #blog-settings-modal, #blog-result-modal').forEach(modal => {
        const closeBtn = modal.querySelector('.close-modal-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                modal.classList.add('hidden');
                if (modal === blogSettingsModal) resetBlogWorkflow();
            });
        }
    });

    // Category Selection -> Go to Settings Modal
    if (catBoxes) {
        catBoxes.forEach(box => {
            box.addEventListener('click', () => {
                selectedCategory = box.getAttribute('data-cat');
                if (blogTopicInput) {
                    blogTopicInput.placeholder = `e.g. Impact of AI on ${selectedCategory} in 2026`;
                }
                
                if (blogCatModal) blogCatModal.classList.add('hidden');
                if (blogSettingsModal) blogSettingsModal.classList.remove('hidden');
            });
        });
    }

    // Back to Category Modal from Settings Modal
    if (backToCatsBtn) {
        backToCatsBtn.addEventListener('click', () => {
            if (blogSettingsModal) blogSettingsModal.classList.add('hidden');
            if (blogCatModal) blogCatModal.classList.remove('hidden');
        });
    }

    function resetBlogWorkflow() {
        selectedCategory = "";
        if (blogTopicInput) blogTopicInput.value = '';
        if (blogStatus) blogStatus.classList.add('hidden');
        if (generateBlogBtn) generateBlogBtn.disabled = false;
        if (blogSettingsModal) blogSettingsModal.classList.add('hidden');
        if (blogCatModal) blogCatModal.classList.add('hidden');
    }

    // Generate blog
    if (generateBlogBtn) {
        generateBlogBtn.addEventListener('click', async () => {
            const topicInput = blogTopicInput ? blogTopicInput.value.trim() : "";
            const finalTopic = topicInput ? `${selectedCategory}: ${topicInput}` : selectedCategory;
            const tone = blogToneSelect ? blogToneSelect.value : "Professional";
            const length = blogLengthSelect ? blogLengthSelect.value : "Medium";
            const productId = document.getElementById('blog-product-select').value;

            if (!selectedCategory) {
                Toast.show("Please select a category first", "error");
                return;
            }

            generateBlogBtn.disabled = true;
            if (blogStatus) blogStatus.classList.remove('hidden');
            if (blogStatusText) blogStatusText.innerText = "Sourcing facts & sending to queue...";

            try {
                const result = await Api.enqueueBlog(finalTopic, tone, length, productId ? parseInt(productId) : null);
                
                if (result && result.job_id) {
                    resetBlogWorkflow();
                    Toast.show('Blog generation started! Check the Activity Queue.');
                    if (window.queuePanel && window.queuePanel.fetchJobs) {
                        window.queuePanel.fetchJobs();
                    }
                } else {
                    Toast.show((result && result.error) || 'Failed to start blog generation', 'error');
                    generateBlogBtn.disabled = false;
                    if (blogStatus) blogStatus.classList.add('hidden');
                }
            } catch (e) {
                console.error("Blog Generation Click Error:", e);
                Toast.show('An error occurred during blog generation', 'error');
                generateBlogBtn.disabled = false;
                if (blogStatus) blogStatus.classList.add('hidden');
            }
        });
    }

    window.showBlogResult = function(blog) {
        blogResultTitle.innerText = blog.title;
        blogResultContent.innerText = blog.content;
        blogResultModal.classList.remove('hidden');
    };

    // Close blog result modal
    if (closeBlogResult) {
        closeBlogResult.addEventListener('click', () => {
            blogResultModal.classList.add('hidden');
        });
    }

    // Copy to clipboard
    if (copyBlogBtn) {
        copyBlogBtn.addEventListener('click', () => {
            const text = blogResultContent.innerText;
            navigator.clipboard.writeText(text).then(() => {
                Toast.show('Blog copied to clipboard');
            }).catch(err => {
                console.error('Could not copy text: ', err);
                Toast.show('Failed to copy text', 'error');
            });
        });
    }

    // Post to LinkedIn
    if (publishBlogBtn) {
        publishBlogBtn.addEventListener('click', async () => {
            const text = blogResultContent.innerText;
            const title = blogResultTitle.innerText;
            const fullContent = `${title}\n\n${text}`;

            publishBlogBtn.disabled = true;
            publishBlogBtn.innerText = 'Publishing...';

            const accountId = LinkedInAccounts.getSelectedAccountId('blog-account-selector');

            try {
                const result = await Api.publishPost(fullContent, null, accountId);
                if (result.status === 'success') {
                    Toast.show('Blog published successfully to LinkedIn!');
                    blogResultModal.classList.add('hidden');
                } else {
                    Toast.show(result.error || 'Failed to publish blog', 'error');
                }
            } catch (e) {
                console.error(e);
                Toast.show('An error occurred while publishing', 'error');
            } finally {
                publishBlogBtn.disabled = false;
                publishBlogBtn.innerText = 'Post to LinkedIn';
            }
        });
    }
});
