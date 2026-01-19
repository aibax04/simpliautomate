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
            created_at: new Date().toISOString().replace('Z', '+00:00')
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
        if (this.pollingInterval) clearTimeout(this.pollingInterval);

        const poll = async () => {
            await this.fetchJobs();

            // Adjust frequency: 2s if jobs are active, 10s if idle
            const hasActiveJobs = this.jobs.some(j => !['ready', 'failed'].includes(j.status)) || this.optimisticJobs.length > 0;
            const nextDelay = hasActiveJobs ? 2000 : 10000;

            this.pollingInterval = setTimeout(poll, nextDelay);
        };

        poll();
    }

    async fetchJobs() {
        try {
            const serverJobs = await Api.getQueueStatus();

            // Update internal state
            this.jobs = serverJobs;

            // Remove optimistic jobs that are now confirmed by server (matched by headline or ID)
            this.optimisticJobs = this.optimisticJobs.filter(opt => {
                const found = serverJobs.find(s =>
                    s.job_id === opt.id ||
                    s.id === opt.id ||
                    (s.payload?.headline === opt.payload?.headline && opt.status === 'processing')
                );
                return !found;
            });

            this.refreshUI();
        } catch (e) {
            console.error("Queue fetch error", e);
        }
    }

    refreshUI() {
        // Merge lists: Optimistic first
        const displayList = [...this.optimisticJobs, ...this.jobs];

        // Check for auto-open (if app is watching a job)
        if (typeof window.app !== 'undefined' && window.app.checkWatch) {
            displayList.forEach(job => window.app.checkWatch(job));
        } else {
            // Optional: Log once if app is missing to avoid spam, or just ignore
            // console.warn("QueuePanel: window.app not ready yet for auto-open check");
        }

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
        if (!this.list) return;

        // --- CHANGE DETECTION ---
        // Create a signature of the current state to avoid unnecessary DOM churn
        const jobsSignature = JSON.stringify(jobs.map(j => ({
            id: j.id || j.job_id,
            status: j.status,
            progress: j.progress
        })));

        if (this.lastJobsSignature === jobsSignature) {
            return; // Nothing meaningful changed, skip rendering
        }
        this.lastJobsSignature = jobsSignature;
        // ------------------------

        // Efficient Incremental Update
        const existingItems = new Map();
        const currentIdList = [];
        Array.from(this.list.children).forEach(child => {
            const id = child.getAttribute('data-job-id');
            if (id) {
                existingItems.set(id, child);
                currentIdList.push(id);
            }
        });

        const newIdList = jobs.map(job => (job.id || job.job_id).toString());
        const orderChanged = JSON.stringify(currentIdList) !== JSON.stringify(newIdList);

        // Clear if absolutely empty
        if (jobs.length === 0) {
            this.list.innerHTML = '<div class="empty-state">No activity yet.</div>';
            return;
        } else if (this.list.querySelector('.empty-state')) {
            this.list.innerHTML = '';
        }

        const fragment = orderChanged ? document.createDocumentFragment() : null;

        jobs.forEach((job, index) => {
            const jobId = (job.id || job.job_id).toString();
            const existingElement = existingItems.get(jobId);

            if (existingElement) {
                // Update if status or progress changed
                const oldStatus = existingElement.getAttribute('data-status');
                const oldProgress = existingElement.getAttribute('data-progress');
                const newStatus = job.status || 'queued';
                const newProgress = (job.progress || 0).toString();

                if (oldStatus !== newStatus || oldProgress !== newProgress) {
                    this.updateJobElement(existingElement, job);
                }

                if (orderChanged) {
                    fragment.appendChild(existingElement);
                }
                existingItems.delete(jobId);
            } else {
                // Create new
                const newElement = this.createJobElement(job);
                newElement.style.opacity = '0';
                newElement.style.transform = 'translateY(10px)';

                if (orderChanged) {
                    fragment.appendChild(newElement);
                } else {
                    this.list.insertBefore(newElement, this.list.children[index]);
                }

                // Animate entrance
                setTimeout(() => {
                    newElement.style.opacity = '1';
                    newElement.style.transform = 'translateY(0)';
                }, 10);
            }
        });

        if (orderChanged) {
            // Remove elements that are no longer in the list
            existingItems.forEach(el => {
                el.style.opacity = '0';
                el.style.transform = 'scale(0.95)';
                setTimeout(() => el.remove(), 300);
            });
            this.list.appendChild(fragment);
        } else {
            // Surgical removal of deleted items
            existingItems.forEach(el => el.remove());
        }
    }

    updateJobElement(element, job) {
        const status = job.status || 'queued';
        const isGenerating = (status.includes('generating') || status === 'processing' || status === 'fetching_sources');
        const statusClass = isGenerating ? 'generating active' : status;

        element.setAttribute('data-status', status);
        element.setAttribute('data-progress', job.progress || 0);
        element.className = `queue-item ${statusClass}`;

        // Refresh the inner content for status/progress
        this.setJobInnerHtml(element, job);
    }

    createJobElement(job) {
        const item = document.createElement('div');
        const jobId = job.id || job.job_id;
        item.setAttribute('data-job-id', jobId);

        const status = job.status || 'queued';
        const isGenerating = (status.includes('generating') || status === 'processing' || status === 'fetching_sources');
        const statusClass = isGenerating ? 'generating active' : status;

        item.className = `queue-item ${statusClass}`;
        item.setAttribute('data-status', status);
        item.setAttribute('data-progress', job.progress || 0);

        // Pass event to handle click carefully
        item.onclick = (e) => this.handleJobClick(job, e);

        this.setJobInnerHtml(item, job);
        return item;
    }

    setJobInnerHtml(item, job) {
        const status = job.status || 'queued';
        const isGenerating = (status.includes('generating') || status === 'processing' || status === 'fetching_sources');
        const jobId = job.id || job.job_id;

        // Professional Status Mapping
        const statusMap = {
            'queued': 'Queued',
            'processing': 'Initializing',
            'generating_caption': 'Drafting',
            'generating_visual_plan': 'Designing',
            'generating_image': 'Rendering',
            'fetching_sources': 'Sourcing',
            'generating_content': 'Writing',
            'quality_check_caption': 'Proofreading',
            'quality_check_visual': 'Polishing',
            'ready': 'Ready',
            'failed': 'Failed'
        };

        const statusLabel = statusMap[status] || status.replace(/_/g, ' ');

        // Type Detection & Keyword Extraction
        let typeLabel = "News Post";
        if (job.is_historical) {
            // Try to fetch a relevant keyword/domain
            if (job.payload?.category) typeLabel = job.payload.category;
            else if (job.result?.domain) typeLabel = job.result.domain;
            else if (job.result?.news_item?.domain) typeLabel = job.result.news_item.domain;
            else if (job.result?.category) typeLabel = job.result.category;
            else if (job.payload?.news_item?.domain) typeLabel = job.payload.news_item.domain;
            else typeLabel = "Past Post";
        }

        if (job.type === 'blog_generation') {
            typeLabel = "LinkedIn Blog";
        } else if (job.payload?.news_item?.custom_prompt || job.type === 'custom_post') {
            typeLabel = "Custom Post";
        }

        // Headline Cleanup
        let headline = job.payload?.headline || job.headline || 'Untitled Post';
        if (headline === "undefined" || !headline || headline === "Historical Post") {
            if (job.result?.headline) headline = job.result.headline;
            else if (job.result?.text) headline = job.result.text.substring(0, 30) + "...";
            else headline = "LinkedIn Content";
        }

        const dateObj = job.created_at ? new Date(job.created_at) : new Date();
        const timeStr = dateObj.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit', hour12: false });
        const dateStr = dateObj.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });

        item.innerHTML = `
            <div class="job-row-main">
                <div class="job-col-info">
                    <span class="job-title-primary">${headline}</span>
                    <div class="job-sub-row">
                        <span class="job-type-tag">${typeLabel}</span>
                        <span class="job-time-muted">${dateStr}, ${timeStr}</span>
                    </div>
                </div>
                <div class="job-col-status">
                    <div class="status-badge-container">
                        ${isGenerating ? '<div class="mini-spinner" style="width:10px; height:10px; border-width:2px; margin-right:6px;"></div>' : ''}
                        <span class="status-badge">${statusLabel}</span>
                    </div>
                </div>
                <div class="job-col-actions" style="margin-left: 8px;">
                    <button class="btn-icon delete-job-btn" onclick="window.queuePanel.handleDelete('${jobId}', event)" title="Delete" style="opacity: 0.6; padding: 4px;">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="3 6 5 6 21 6"></polyline><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2"></path></svg>
                    </button>
                </div>
            </div>
            ${isGenerating && job.progress > 0 ? `
            <div class="progress-container-mini">
                <div class="progress-bar-mini" style="width: ${job.progress}%"></div>
            </div>` : ''}
        `;
    }

    handleDelete(jobId, e) {
        if (e) e.stopPropagation();
        if (!confirm("Are you sure you want to remove this item?")) return;

        // Optimistic Remove
        const strId = String(jobId);
        this.jobs = this.jobs.filter(j => String(j.id || j.job_id) !== strId);
        this.optimisticJobs = this.optimisticJobs.filter(j => String(j.id) !== strId);
        this.refreshUI();

        // API
        Api.deleteJob(jobId).then(() => {
            console.log("Job deleted:", jobId);
        });
    }

    async handleJobClick(job, e) {
        // Prevent click if clicking delete button (redundant check if stopPropagation works, but good for safety)
        if (e && e.target.closest('.delete-job-btn')) return;

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
