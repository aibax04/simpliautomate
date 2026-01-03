document.addEventListener('DOMContentLoaded', () => {
    const blogBtn = document.getElementById('blog-generator-btn');
    const blogModal = document.getElementById('blog-modal');
    const closeBlogModal = document.getElementById('close-blog-modal');
    const generateBlogBtn = document.getElementById('generate-blog-btn');
    const blogTopicInput = document.getElementById('blog-topic-input');
    const blogToneSelect = document.getElementById('blog-tone-select');
    const blogLengthSelect = document.getElementById('blog-length-select');
    const blogStatus = document.getElementById('blog-status');
    const blogStatusText = document.getElementById('blog-status-text');

    const blogResultModal = document.getElementById('blog-result-modal');
    const blogResultTitle = document.getElementById('blog-result-title');
    const blogResultContent = document.getElementById('blog-result-content');
    const closeBlogResult = document.getElementById('close-blog-result');
    const copyBlogBtn = document.getElementById('copy-blog-btn');
    const publishBlogBtn = document.getElementById('publish-blog-btn');

    if (!blogBtn) return;

    // Open blog modal
    blogBtn.addEventListener('click', () => {
        blogModal.classList.remove('hidden');
    });

    // Close blog modal
    closeBlogModal.addEventListener('click', () => {
        blogModal.classList.add('hidden');
        resetBlogModal();
    });

    function resetBlogModal() {
        blogTopicInput.value = '';
        blogStatus.classList.add('hidden');
        generateBlogBtn.disabled = false;
    }

    // Generate blog
    generateBlogBtn.addEventListener('click', async () => {
        const topic = blogTopicInput.value.trim();
        const tone = blogToneSelect.value;
        const length = blogLengthSelect.value;

        if (!topic) {
            Toast.show('Please enter a blog topic', 'error');
            return;
        }

        generateBlogBtn.disabled = true;
        blogStatus.classList.remove('hidden');
        blogStatusText.innerText = "Sourcing facts & sending to queue...";

        try {
            const result = await Api.enqueueBlog(topic, tone, length);
            
            if (result.job_id) {
                blogModal.classList.add('hidden');
                Toast.show('Blog generation started! Check the Activity Queue.');
                if (window.queuePanel && window.queuePanel.fetchJobs) {
                    window.queuePanel.fetchJobs();
                }
            } else {
                Toast.show(result.error || 'Failed to start blog generation', 'error');
            }
        } catch (e) {
            console.error(e);
            Toast.show('An error occurred during blog generation', 'error');
        } finally {
            generateBlogBtn.disabled = false;
            blogStatus.classList.add('hidden');
            resetBlogModal();
        }
    });

    window.showBlogResult = function(blog) {
        blogResultTitle.innerText = blog.title;
        blogResultContent.innerText = blog.content;
        blogResultModal.classList.remove('hidden');
    };

    // Close blog result modal
    closeBlogResult.addEventListener('click', () => {
        blogResultModal.classList.add('hidden');
    });

    // Copy to clipboard
    copyBlogBtn.addEventListener('click', () => {
        const text = blogResultContent.innerText;
        navigator.clipboard.writeText(text).then(() => {
            Toast.show('Blog copied to clipboard');
        }).catch(err => {
            console.error('Could not copy text: ', err);
            Toast.show('Failed to copy text', 'error');
        });
    });

    // Post to LinkedIn
    publishBlogBtn.addEventListener('click', async () => {
        const text = blogResultContent.innerText;
        const title = blogResultTitle.innerText;
        const fullContent = `${title}\n\n${text}`;

        publishBlogBtn.disabled = true;
        publishBlogBtn.innerText = 'Publishing...';

        try {
            const result = await Api.publishPost(fullContent, null);
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
});
