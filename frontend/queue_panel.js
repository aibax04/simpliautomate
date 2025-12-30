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
        const activeCount = jobs.filter(j => ['queued', 'generating_caption', 'generating_visual_plan', 'generating_image'].includes(j.status)).length;
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
            const item = document.createElement('div');
            item.className = `queue-item ${job.status}`;
            item.onclick = () => this.handleJobClick(job);

            let statusLabel = job.status.replace('_', ' ');
            let icon = '⏳';
            if (job.status === 'ready') icon = '✅';
            if (job.status === 'failed') icon = '❌';
            if (job.status.includes('generating')) icon = '⚙️';

            item.innerHTML = `
                <div class="job-header">
                    <span class="job-title">${job.payload.headline || 'Untitled'}</span>
                    <span class="job-icon">${icon}</span>
                </div>
                <div class="job-status">
                    ${statusLabel} 
                    ${job.progress ? `<span class="progress-text">${job.progress}%</span>` : ''}
                </div>
                ${job.progress && job.progress < 100 ? `
                <div class="progress-bar-bg">
                    <div class="progress-bar-fill" style="width: ${job.progress}%"></div>
                </div>` : ''}
            `;
            this.list.appendChild(item);
        });
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
