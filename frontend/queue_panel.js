class QueuePanel {
    constructor() {
        this.panel = document.getElementById('queue-panel');
        this.list = document.getElementById('queue-list');
        this.toggleBtn = document.getElementById('toggle-queue-btn');
        this.isOpen = false;

        this.bindEvents();
        this.startPolling();
    }

    bindEvents() {
        this.toggleBtn.onclick = () => this.toggle();
    }

    addOptimisticJob(jobId, headline) {
        // Create temp job object
        const tempJob = {
            id: jobId,
            status: 'processing',
            payload: { headline: headline },
            progress: 0,
            isOptimistic: true
        };

        // Ensure panel is open
        if (!this.isOpen) this.toggle();

        // Render or inject
        // We'll just prepend to list.
        // First check if empty state exists
        const empty = this.list.querySelector('.empty-state');
        if (empty) empty.remove();

        const item = this.createJobElement(tempJob);
        this.list.insertBefore(item, this.list.firstChild);

        // Show badge
        const badge = document.getElementById('queue-badge');
        badge.classList.remove('hidden');
        let count = parseInt(badge.innerText) || 0;
        badge.innerText = count + 1;
    }

    toggle() {
        this.isOpen = !this.isOpen;
        if (this.isOpen) {
            this.panel.classList.add('open');
            this.fetchJobs();
        } else {
            this.panel.classList.remove('open');
        }
    }

    startPolling() {
        // Poll every 3 seconds
        setInterval(() => {
            this.fetchJobs();
        }, 3000);
    }

    async fetchJobs() {
        const jobs = await Api.getQueueStatus();
        this.render(jobs);

        // Update badge count
        const activeCount = jobs.filter(j => ['queued', 'generating_caption', 'generating_visual_plan', 'generating_image', 'processing'].includes(j.status)).length;
        const badge = document.getElementById('queue-badge');
        if (activeCount > 0) {
            badge.innerText = activeCount;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    }

    render(jobs) {
        this.list.innerHTML = '';
        if (jobs.length === 0) {
            this.list.innerHTML = '<div class="empty-state">No active jobs</div>';
            return;
        }

        jobs.forEach(job => {
            const item = this.createJobElement(job);
            this.list.appendChild(item);
        });
    }

    createJobElement(job) {
        const item = document.createElement('div');
        item.className = `queue-item ${job.status}`;
        item.onclick = () => this.handleJobClick(job);

        let statusLabel = job.status.replace(/_/g, ' ');
        let icon = '⏳';

        if (job.status === 'ready') icon = '✅';
        else if (job.status === 'failed') icon = '❌';
        else if (job.status.includes('generating') || job.status === 'processing') icon = '⚙️';

        let progress = job.progress || 0;
        // Mock progress for optimistic
        if (job.status === 'processing' && !job.progress) progress = 5;

        item.innerHTML = `
            <div class="job-header">
                <span class="job-title">${job.payload.headline || 'Untitled'}</span>
                <span class="job-icon">${icon}</span>
            </div>
            <div class="job-status">
                ${statusLabel} 
                ${progress > 0 ? `<span class="progress-text">${progress}%</span>` : ''}
            </div>
            ${progress < 100 ? `
            <div class="progress-bar-bg">
                <div class="progress-bar-fill" style="width: ${progress}%"></div>
            </div>` : ''}
        `;
        return item;
    }

    async handleJobClick(job) {
        if (job.status === 'ready' && job.result) {
            // Open Result Modal via global app instance or event
            if (window.app) {
                window.app.openResult(job.result);
            }
        } else if (job.status === 'failed') {
            alert("Job failed: " + job.error);
        }
    }
}

// Init when DOM loads
document.addEventListener('DOMContentLoaded', () => {
    window.queuePanel = new QueuePanel();
});
