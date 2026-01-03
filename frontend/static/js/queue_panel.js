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
        // Simple ID-based matching to prevent flickering
        const currentIds = Array.from(this.list.children).map(child => child.getAttribute('data-job-id'));
        const newIds = jobs.map(job => (job.id || job.job_id).toString());

        // Check if the order or content is actually different
        const isSameOrder = currentIds.length === newIds.length && currentIds.every((id, idx) => id === newIds[idx]);
        
        // If same order, check if any status or progress changed
        if (isSameOrder) {
            let hasChanges = false;
            jobs.forEach((job, idx) => {
                const item = this.list.children[idx];
                const oldStatus = item.getAttribute('data-status');
                const oldProgress = item.getAttribute('data-progress');
                if (oldStatus !== job.status || oldProgress !== (job.progress || 0).toString()) {
                    hasChanges = true;
                }
            });
            if (!hasChanges) return;
        }

        // Apply smooth transition if changing content
        this.list.style.opacity = '0.7';

        setTimeout(() => {
            this.list.innerHTML = '';
            if (jobs.length === 0) {
                this.list.innerHTML = '<div class="empty-state">No activity yet.</div>';
            } else {
                jobs.forEach(job => {
                    const item = this.createJobElement(job);
                    this.list.appendChild(item);
                });
            }
            this.list.style.opacity = '1';
        }, 50);
    }

    createJobElement(job) {
        const item = document.createElement('div');
        const jobId = job.id || job.job_id;
        item.setAttribute('data-job-id', jobId);
        item.setAttribute('data-status', job.status);
        item.setAttribute('data-progress', job.progress || 0);
        
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
            'fetching_sources': 'Sourcing Facts...',
            'generating_content': 'Writing Blog...',
            'ready': 'Ready for Review',
            'failed': 'Process Failed'
        };

        let statusLabel = statusMap[status] || status.replace(/_/g, ' ');

        // Icons
        let icon = '';
        if (status === 'ready') icon = '<span style="color:var(--success); font-weight:bold;">✓</span>';
        else if (status === 'failed') icon = '<span style="color:var(--error); font-weight:bold;">!</span>';
        else if (isGenerating) icon = '<div class="mini-spinner"></div>';

        let progress = job.progress || 0;
        // Mock progress for optimistic
        if (status === 'processing' && !job.progress) progress = 5;

        // Handle headline from payload or direct properties (depends on backend)
        const headline = job.payload?.headline || job.headline || 'Untitled Source';
        const category = job.payload?.news_item?.domain || job.payload?.topic || '';

        item.innerHTML = `
            <div class="job-header">
                <span class="job-title">${headline}</span>
                <span class="job-icon">${icon}</span>
            </div>
            
            <div class="job-meta">
                <div style="display:flex; gap:6px; align-items:center;">
                    <span class="status-badge">${statusLabel}</span>
                    ${category ? `<span style="font-size:0.6rem; color:var(--primary); font-weight:600; text-transform:uppercase; opacity:0.7;">• ${category}</span>` : ''}
                </div>
                ${progress > 0 && progress < 100 ? `<span style="font-size:0.7rem; color:var(--text-secondary); opacity:0.8;">${progress}%</span>` : ''}
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
            if (job.type === 'blog_generation') {
                if (window.showBlogResult) {
                    window.showBlogResult(job.result);
                }
            } else {
                if (window.app) {
                    window.app.openResult(job);
                }
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
