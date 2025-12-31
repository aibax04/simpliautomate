class QueuePanel {
    constructor() {
        this.list = document.getElementById('queue-list');
        this.badge = document.getElementById('queue-count');
        this.jobs = [];
        this.optimisticJobs = [];
        this.startPolling();
    }

    addOptimisticJob(jobId, headline) {
        const job = {
            id: jobId,
            status: 'processing',
            payload: { headline: headline },
            progress: 0,
            isOptimistic: true,
            created_at: new Date().toISOString()
        };

        // Add to optimistic list
        this.optimisticJobs.unshift(job);

        // Force immediate refresh
        this.refreshUI();
    }

    updateOptimisticId(tempId, realId) {
        const job = this.optimisticJobs.find(j => j.id === tempId);
        if (job) {
            job.id = realId;
            // No need to refresh, just update internal ref. 
            // The next poll will find it by realId and merge it correctly.
        }
    }

    removeJob(jobId) {
        this.optimisticJobs = this.optimisticJobs.filter(j => j.id !== jobId);
        this.refreshUI();
    }

    startPolling() {
        setInterval(() => {
            this.fetchJobs();
        }, 3000);
    }

    async fetchJobs() {
        try {
            const serverJobs = await Api.getQueueStatus();
            this.jobs = serverJobs;

            // Remove optimistic jobs that are now present in server response
            this.optimisticJobs = this.optimisticJobs.filter(opt =>
                !this.jobs.find(server => server.job_id === opt.id || server.id === opt.id)
            );

            this.refreshUI();
        } catch (e) {
            console.error("Polling error", e);
        }
    }

    refreshUI() {
        // Merge lists: Optimistic first
        const displayList = [...this.optimisticJobs, ...this.jobs];

        this.render(displayList);

        // Update System Status
        const activeJobs = displayList.filter(j => ['queued', 'generating_caption', 'generating_visual_plan', 'generating_image', 'processing'].includes(j.status));
        this.updateBadgeCount(activeJobs.length);
        this.updateSystemStatus(activeJobs.length > 0);
    }

    updateBadgeCount(count) {
        if (!this.badge) return;

        if (count > 0) {
            this.badge.innerText = count;
            this.badge.classList.remove('hidden');
        } else {
            this.badge.classList.add('hidden');
        }
    }

    updateSystemStatus(isWorking) {
        const indicator = document.getElementById('system-status');
        const text = document.getElementById('system-status-text');
        if (!indicator || !text) return;

        if (isWorking) {
            indicator.className = 'status-pill working';
            text.innerText = 'System Active';
        } else {
            indicator.className = 'status-pill idle';
            text.innerText = 'System Ready';
        }
    }

    render(jobs) {
        this.list.innerHTML = '';
        if (jobs.length === 0) {
            this.list.innerHTML = '<div class="empty-state">No activity yet.</div>';
            return;
        }

        jobs.forEach(job => {
            const item = this.createJobElement(job);
            this.list.appendChild(item);
        });
    }

    createJobElement(job) {
        const item = document.createElement('div');
        // Add specific class for animation/status styling
        const status = job.status || 'queued';
        const isGenerating = (status.includes('generating') || status === 'processing');
        const statusClass = isGenerating ? 'generating active' : status;

        item.className = `queue-item ${statusClass}`;
        item.onclick = () => this.handleJobClick(job);

        // Friendly Status Mapping
        const statusMap = {
            'queued': 'Queued',
            'processing': 'Initializing...',
            'generating_caption': 'Drafting Caption...',
            'generating_visual_plan': 'Designing Visuals...',
            'generating_image': 'Rendering Image...',
            'ready': 'Ready for Review',
            'failed': 'Process Failed'
        };

        let statusLabel = statusMap[status] || status.replace(/_/g, ' ');

        // Icons
        let icon = '';
        if (status === 'ready') icon = '<span style="color:var(--success);">✓</span>';
        else if (status === 'failed') icon = '<span style="color:var(--error);">!</span>';
        else if (isGenerating) icon = '⟳';

        let progress = job.progress || 0;
        // Mock progress for optimistic
        if (status === 'processing' && !job.progress) progress = 5;

        // Handle headline from payload or direct properties (depends on backend)
        const headline = job.payload?.headline || job.headline || 'Untitled Source';

        item.innerHTML = `
            <div class="job-header">
                <span class="job-title">${headline}</span>
                <span class="job-icon">${icon}</span>
            </div>
            
            <div class="job-meta">
                <span class="status-badge">${statusLabel}</span>
                ${progress > 0 && progress < 100 ? `<span style="font-size:0.7rem; color:var(--text-secondary);">${progress}%</span>` : ''}
            </div>

            ${progress < 100 && status !== 'ready' && status !== 'failed' ? `
            <div class="progress-rail">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>` : ''}
        `;
        return item;
    }

    async handleJobClick(job) {
        if (job.status === 'ready' && job.result) {
            if (window.app) {
                window.app.openResult(job);
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
