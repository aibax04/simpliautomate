const PostScheduler = {
    scheduledPosts: [],

    init() {
        this.setupEventListeners();
        this.loadSavedEmail();
    },

    loadSavedEmail() {
        const savedEmail = localStorage.getItem('simplii_notification_email');
        if (savedEmail) {
            const mgmtInput = document.getElementById('test-email-input');
            if (mgmtInput) mgmtInput.value = savedEmail;
            
            const postEmailInput = document.getElementById('post-notification-email');
            if (postEmailInput) postEmailInput.value = savedEmail;
            
            const blogEmailInput = document.getElementById('blog-notification-email');
            if (blogEmailInput) blogEmailInput.value = savedEmail;
        }
    },

    setupEventListeners() {
        const manageBtn = document.getElementById('manage-scheduled-btn');
        if (manageBtn) {
            manageBtn.onclick = () => this.showManagementModal();
        }

        const scheduleBtn = document.getElementById('schedule-btn');
        if (scheduleBtn) {
            scheduleBtn.onclick = () => this.handleSchedulePost('post-account-selector', 'post-schedule-time', 'post-preview', 'post-notification-email');
        }

        const scheduleBlogBtn = document.getElementById('schedule-blog-btn');
        if (scheduleBlogBtn) {
            scheduleBlogBtn.onclick = () => this.handleSchedulePost('blog-account-selector', 'blog-schedule-time', 'blog-result-content', 'blog-notification-email');
        }

        const testEmailBtn = document.getElementById('send-test-email-btn');
        if (testEmailBtn) {
            testEmailBtn.onclick = () => this.handleTestEmail();
        }

        const emailInput = document.getElementById('test-email-input');
        if (emailInput) {
            emailInput.addEventListener('change', (e) => {
                localStorage.setItem('simplii_notification_email', e.target.value.trim());
            });
        }
    },

    async showManagementModal() {
        document.getElementById('scheduled-posts-modal').classList.remove('hidden');
        await this.loadScheduledPosts();
    },

    async loadScheduledPosts() {
        try {
            this.scheduledPosts = await Api.getScheduledPosts();
            this.renderScheduledPosts();
        } catch (e) {
            console.error("Failed to load scheduled posts:", e);
        }
    },

    renderScheduledPosts() {
        const list = document.getElementById('scheduled-posts-list');
        if (!list) return;

        if (this.scheduledPosts.length === 0) {
            list.innerHTML = '<p style="text-align:center; padding: 20px; color: var(--text-secondary);">No scheduled posts yet.</p>';
            return;
        }

        list.innerHTML = this.scheduledPosts.map(post => `
            <div class="account-item">
                <div class="account-info">
                    <strong>${post.account_name}</strong>
                    <span>Scheduled for: ${new Date(post.scheduled_at).toLocaleString()}</span>
                    <span class="status-badge ${post.status}">${post.status}</span>
                    ${post.error_message ? `<span style="color: var(--error); font-size: 10px;">${post.error_message}</span>` : ''}
                </div>
                ${post.status === 'pending' ? `
                    <button class="btn-icon delete" onclick="PostScheduler.cancelPost(${post.id})">✕</button>
                ` : ''}
            </div>
        `).join('');
    },

    async cancelPost(id) {
        if (!confirm("Cancel this scheduled post?")) return;
        try {
            await Api.cancelScheduledPost(id);
            Toast.show("Scheduled post cancelled");
            await this.loadScheduledPosts();
        } catch (e) {
            Toast.show("Failed to cancel", "error");
        }
    },

    async handleSchedulePost(accountSelectorId, timeInputId, contentId, emailInputId) {
        const accountId = LinkedInAccounts.getSelectedAccountId(accountSelectorId);
        const scheduledAt = document.getElementById(timeInputId).value;
        const emailEl = document.getElementById(emailInputId);
        const notificationEmail = emailEl ? emailEl.value.trim() : localStorage.getItem('simplii_notification_email');
        
        const contentEl = document.getElementById(contentId);
        const content = contentEl.innerText || contentEl.textContent;
        
        // Find image if exists (for regular posts)
        let imageUrl = null;
        const imgEl = document.querySelector(`#${contentId} img`);
        if (imgEl) imageUrl = imgEl.src;

        if (!accountId) {
            Toast.show("Please select a LinkedIn account", "error");
            return;
        }

        if (!scheduledAt) {
            Toast.show("Please select a date and time", "error");
            return;
        }

        if (!notificationEmail) {
            Toast.show("Please enter a notification email", "error");
            return;
        }

        const scheduledDate = new Date(scheduledAt);
        if (scheduledDate <= new Date()) {
            Toast.show("Scheduled time must be in the future", "error");
            return;
        }

        try {
            await Api.schedulePost({
                linkedin_account_id: parseInt(accountId),
                content: content,
                image_url: imageUrl,
                scheduled_at: scheduledDate.toISOString(),
                notification_email: notificationEmail
            });
            Toast.show("Post scheduled successfully!", "success");
            
            // Save email for next time
            localStorage.setItem('simplii_notification_email', notificationEmail);
            
            // Close the modal
            const resultModal = document.getElementById('result-modal');
            const blogResultModal = document.getElementById('blog-result-modal');
            if (resultModal) resultModal.classList.add('hidden');
            if (blogResultModal) blogResultModal.classList.add('hidden');
            
            // Reset fields
            document.getElementById(timeInputId).value = "";
            if (emailEl) emailEl.value = notificationEmail;
        } catch (e) {
            Toast.show("Failed to schedule post: " + e.message, "error");
        }
    },

    async handleTestEmail() {
        const email = document.getElementById('test-email-input').value.trim();
        if (!email) {
            Toast.show("Please enter an email address", "error");
            return;
        }

        const btn = document.getElementById('send-test-email-btn');
        btn.disabled = true;
        btn.innerText = "Sending...";

        try {
            await Api.sendTestEmail(email);
            Toast.show("Test email sent! Check your inbox.");
        } catch (e) {
            Toast.show("Failed to send test email: " + e.message, "error");
        } finally {
            btn.disabled = false;
            btn.innerText = "Send Test";
        }
    }
};

document.addEventListener('DOMContentLoaded', () => PostScheduler.init());
