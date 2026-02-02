/**
 * Social Listening Module
 * Handles social media monitoring, tracking rules, alerts, and analytics
 */

// Get API reference - support both Api and API naming
const getAPI = () => window.API || window.Api;

const SocialListening = {
    // State
    rules: [],
    feedItems: [],
    alerts: [],
    analytics: {
        sentiment: { positive: 0, neutral: 0, negative: 0 },
        platforms: { twitter: 0, linkedin: 0, reddit: 0, news: 0 },
        keywords: []
    },
    currentPostForResponse: null,

    /**
     * Initialize the Social Listening module
     */
    async init() {
        console.log('[SocialListening] Initializing module...');
        await this.loadRules();
        await this.loadFeed();
        await this.loadAlerts();
        await this.loadAnalytics();

        // Load user's notification email (global function)
        try {
            await loadUserNotificationEmail();
        } catch (e) {
            console.warn('[SocialListening] Failed to load notification email:', e);
        }

        this.updateRuleFilters();

        // Initialize filter controls
        this.initFilterControls();
    },

    /**
     * Initialize filter controls and event listeners
     */
    initFilterControls() {
        console.log('[SocialListening] Initializing filter controls...');

        // Time range filter
        const timeRangeFilter = document.getElementById('feed-time-range-filter');
        if (timeRangeFilter) {
            timeRangeFilter.addEventListener('change', (e) => {
                this.handleTimeRangeChange(e.target.value);
                this.debouncedLoadFeed();
            });
        }

        // Custom date inputs
        const startDateInput = document.getElementById('feed-start-date');
        const endDateInput = document.getElementById('feed-end-date');

        if (startDateInput) {
            startDateInput.addEventListener('change', () => this.debouncedLoadFeed());
        }
        if (endDateInput) {
            endDateInput.addEventListener('change', () => this.debouncedLoadFeed());
        }

        // Rule filter
        const ruleFilter = document.getElementById('feed-rule-filter');
        if (ruleFilter) {
            ruleFilter.addEventListener('change', () => this.debouncedLoadFeed());
        }

        // Platform filter
        const platformFilter = document.getElementById('feed-platform-filter');
        if (platformFilter) {
            platformFilter.addEventListener('change', () => this.debouncedLoadFeed());
        }

        // Sort filter
        const sortFilter = document.getElementById('feed-sort-filter');
        if (sortFilter) {
            sortFilter.addEventListener('change', () => this.debouncedLoadFeed());
        }

        // Reset filters button
        const resetBtn = document.getElementById('reset-filters-btn');
        if (resetBtn) {
            resetBtn.addEventListener('click', () => this.resetFilters());
        }

        // Load saved filter state
        this.loadFilterState();

        console.log('[SocialListening] Filter controls initialized');
    },

    /**
     * Handle time range filter change
     */
    handleTimeRangeChange(timeRange) {
        const customDateGroup = document.getElementById('custom-date-group');
        if (customDateGroup) {
            customDateGroup.style.display = timeRange === 'custom' ? 'flex' : 'none';
        }

        // Set default dates for custom range
        if (timeRange === 'custom') {
            const startDateInput = document.getElementById('feed-start-date');
            const endDateInput = document.getElementById('feed-end-date');

            if (startDateInput && !startDateInput.value) {
                const lastWeek = new Date();
                lastWeek.setDate(lastWeek.getDate() - 7);
                startDateInput.value = lastWeek.toISOString().split('T')[0];
            }

            if (endDateInput && !endDateInput.value) {
                const today = new Date();
                endDateInput.value = today.toISOString().split('T')[0];
            }
        }
    },

    /**
     * Debounced load feed to prevent excessive API calls
     */
    debouncedLoadFeed() {
        if (this.feedDebounceTimer) {
            clearTimeout(this.feedDebounceTimer);
        }

        this.feedDebounceTimer = setTimeout(() => {
            console.log('[SocialListening] Debounced feed load triggered');
            this.saveFilterState();
            this.loadFeed();
        }, 500); // 500ms debounce
    },

    /**
     * Reset all filters to default values
     */
    resetFilters() {
        console.log('[SocialListening] Resetting filters...');

        // Reset time range
        const timeRangeFilter = document.getElementById('feed-time-range-filter');
        if (timeRangeFilter) {
            timeRangeFilter.value = '7d';
            this.handleTimeRangeChange('7d');
        }

        // Clear custom dates
        const startDateInput = document.getElementById('feed-start-date');
        const endDateInput = document.getElementById('feed-end-date');
        if (startDateInput) startDateInput.value = '';
        if (endDateInput) endDateInput.value = '';

        // Reset rule filter
        const ruleFilter = document.getElementById('feed-rule-filter');
        if (ruleFilter) ruleFilter.value = 'all';

        // Reset platform filter
        const platformFilter = document.getElementById('feed-platform-filter');
        if (platformFilter) platformFilter.value = 'all';

        // Reset sort filter
        const sortFilter = document.getElementById('feed-sort-filter');
        if (sortFilter) sortFilter.value = 'newest';

        // Clear saved state
        localStorage.removeItem('feedFilters');

        // Reload feed
        this.loadFeed();

        this.showToast('Filters reset to defaults', 'info');
    },

    /**
     * Save current filter state to localStorage
     */
    saveFilterState() {
        try {
            const filterState = {
                timeRange: document.getElementById('feed-time-range-filter')?.value || '7d',
                startDate: document.getElementById('feed-start-date')?.value || '',
                endDate: document.getElementById('feed-end-date')?.value || '',
                ruleId: document.getElementById('feed-rule-filter')?.value || 'all',
                platform: document.getElementById('feed-platform-filter')?.value || 'all',
                sortOrder: document.getElementById('feed-sort-filter')?.value || 'newest'
            };

            localStorage.setItem('feedFilters', JSON.stringify(filterState));
        } catch (error) {
            console.warn('[SocialListening] Failed to save filter state:', error);
        }
    },

    /**
     * Load saved filter state from localStorage
     */
    loadFilterState() {
        try {
            const savedState = localStorage.getItem('feedFilters');
            if (savedState) {
                const filterState = JSON.parse(savedState);

                // Apply saved values
                const timeRangeFilter = document.getElementById('feed-time-range-filter');
                const startDateInput = document.getElementById('feed-start-date');
                const endDateInput = document.getElementById('feed-end-date');
                const ruleFilter = document.getElementById('feed-rule-filter');
                const platformFilter = document.getElementById('feed-platform-filter');
                const sortFilter = document.getElementById('feed-sort-filter');

                if (timeRangeFilter && filterState.timeRange) {
                    timeRangeFilter.value = filterState.timeRange;
                    this.handleTimeRangeChange(filterState.timeRange);
                }

                if (startDateInput && filterState.startDate) {
                    startDateInput.value = filterState.startDate;
                }

                if (endDateInput && filterState.endDate) {
                    endDateInput.value = filterState.endDate;
                }

                if (ruleFilter && filterState.ruleId) {
                    ruleFilter.value = filterState.ruleId;
                }

                if (platformFilter && filterState.platform) {
                    platformFilter.value = filterState.platform;
                }

                if (sortFilter && filterState.sortOrder) {
                    sortFilter.value = filterState.sortOrder;
                }

                console.log('[SocialListening] Restored filter state from localStorage');
            }
        } catch (error) {
            console.warn('[SocialListening] Failed to load filter state:', error);
        }
    },

    /**
     * Load tracking rules from backend
     */
    async loadRules() {
        try {
            const response = await getAPI().get('/api/social-listening/rules');
            if (response.rules) {
                this.rules = response.rules;
                this.renderRules();
            }
        } catch (error) {
            console.log('[SocialListening] No rules loaded yet:', error.message);
            this.rules = [];
            this.renderRules();
        }
    },

    /**
     * Load feed items from backend with advanced filtering
     */
    async loadFeed(silent = false) {
        try {
            // Show loading state immediately to indicate fetching is in progress
            const container = document.getElementById('feed-content');
            if (container && !silent) {
                container.innerHTML = `
                    <div class="feed-loading-state" style="padding: 60px 20px; text-align: center; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center;">
                        <div class="spinner" style="border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid var(--accent); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin-bottom: 15px;"></div>
                        <p style="margin: 0; font-weight: 500;">Fetching similar posts...</p>
                        <p style="margin-top: 5px; font-size: 0.85em; opacity: 0.7;">Scanning social platforms for matches</p>
                    </div>
                    <style>
                        @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
                    </style>
                `;
            }
            // Get all filter values
            const timeRange = document.getElementById('feed-time-range-filter')?.value || '7d';
            const startDate = document.getElementById('feed-start-date')?.value || '';
            const endDate = document.getElementById('feed-end-date')?.value || '';
            const ruleFilter = document.getElementById('feed-rule-filter')?.value || 'all';
            const platformFilter = document.getElementById('feed-platform-filter')?.value || 'all';
            const sortOrder = document.getElementById('feed-sort-filter')?.value || 'newest';

            const params = new URLSearchParams();

            // Always add time_range parameter with default
            params.append('time_range', timeRange || 'all');

            // Add custom date range if applicable
            if (timeRange === 'custom') {
                if (startDate) params.append('start_date', startDate);
                if (endDate) params.append('end_date', endDate);
            }

            // Always add rule and platform filters with defaults
            params.append('rule_id', ruleFilter || 'all');
            params.append('platform', platformFilter || 'all');

            // Always add sorting with default
            params.append('sort_order', sortOrder || 'newest');

            // Always add limit with default (ensure it's within backend limits)
            const feedLimit = Math.min(parseInt(this.feedLimit) || 20, 100);
            params.append('limit', feedLimit.toString());

            console.log('[SocialListening] Loading feed with params:', Object.fromEntries(params));

            const response = await getAPI().get(`/api/social-listening/feed?${params.toString()}`);
            if (response.items) {
                this.feedItems = response.items;
                console.log(`[SocialListening] Loaded ${this.feedItems.length} feed items`);
                this.renderFeed();
            } else {
                this.feedItems = [];
                this.renderFeed();
            }
        } catch (error) {
            console.error('[SocialListening] Error loading feed:', error);
            this.feedItems = [];
            this.renderFeed();
        }
    },

    /**
     * Load alerts from backend
     */
    async loadAlerts() {
        try {
            const response = await getAPI().get('/api/social-listening/alerts');
            if (response.alerts) {
                this.alerts = response.alerts;
                this.renderAlerts();
                this.updateAlertBadge();
            }
        } catch (error) {
            console.log('[SocialListening] No alerts:', error.message);
            this.alerts = [];
            this.renderAlerts();
        }
    },

    /**
     * Load analytics data from backend
     */
    async loadAnalytics() {
        try {
            const timeframe = document.getElementById('analytics-timeframe')?.value || '7d';
            const response = await getAPI().get(`/api/social-listening/analytics?timeframe=${timeframe}`);
            if (response.analytics) {
                this.analytics = response.analytics;
                this.renderAnalytics();
            }
        } catch (error) {
            console.log('[SocialListening] No analytics:', error.message);
            this.renderAnalytics();
        }
    },

    /**
     * Refresh the feed display - reloads current feed data from database
     * Note: Does NOT trigger new content ingestion (use background scheduler for that)
     */
    async refreshFeed() {
        const refreshBtn = document.querySelector('.btn-refresh');
        if (refreshBtn) {
            refreshBtn.innerHTML = '<div class="mini-spinner"></div> Fetching new content...';
            refreshBtn.disabled = true;
        }

        try {
            console.log('[SocialListening] Refreshing feed display...');

            // Trigger backend fetch first to get latest content
            try {
                await getAPI().post('/api/social-listening/fetch');
                // Start polling instead of waiting blindly
                this.pollForNewContent();
            } catch (err) {
                console.warn('[SocialListening] Fetch trigger failed, reloading existing data', err);
            }

            console.log('[SocialListening] Reloading data...');

            // Reload the feed, alerts, and analytics data
            // We do this immediately regardless of polling to ensure UI is responsive
            await Promise.all([
                this.loadFeed(),
                this.loadAlerts(),
                this.loadAnalytics()
            ]);

            this.showToast('Feed refreshed', 'success');
        } catch (error) {
            console.error('[SocialListening] Refresh error:', error);
            this.showToast('Error refreshing feed: ' + error.message, 'error');
        } finally {
            if (refreshBtn) {
                refreshBtn.innerHTML = `<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="23 4 23 10 17 10"></polyline><polyline points="1 20 1 14 7 14"></polyline><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path></svg> Refresh`;
                refreshBtn.disabled = false;
            }
        }
    },

    /**
     * Show the rule builder modal
     */
    showRuleModal(ruleId = null) {
        const modal = document.getElementById('rule-builder-modal');

        // Reset form
        document.getElementById('rule-name').value = '';
        document.getElementById('rule-keywords').value = '';
        document.getElementById('rule-handle-input').value = '';
        document.getElementById('rule-platform-select').value = 'all';
        document.getElementById('rule-sentiment').value = 'all';
        const filterContactEl = document.getElementById('rule-filter-contact-email');
        if (filterContactEl) filterContactEl.checked = false;

        // Reset hidden fields
        document.getElementById('rule-logic').value = 'keywords_or_handles';
        document.getElementById('rule-frequency').value = 'hourly';
        document.getElementById('alert-email').checked = false;
        document.getElementById('alert-inapp').checked = true;

        // If editing, populate form
        if (ruleId) {
            const rule = this.rules.find(r => r.id === ruleId);
            if (rule) {
                document.getElementById('rule-name').value = rule.name || '';
                document.getElementById('rule-keywords').value = (rule.keywords || []).join(', ');

                // Populate handle and platform
                // Since we now support one handle input but multiple in DB, just take the first one or join them
                document.getElementById('rule-handle-input').value = (rule.handles || []).join(', ');

                // Populate platform select
                const platforms = rule.platforms || [];
                if (platforms.length === 0 || platforms.length === 4) { // All or none
                    document.getElementById('rule-platform-select').value = 'all';
                } else if (platforms.length === 1) {
                    document.getElementById('rule-platform-select').value = platforms[0];
                } else {
                    document.getElementById('rule-platform-select').value = 'all'; // Multiple selected, default to all/any for simplicity
                }

                document.getElementById('rule-sentiment').value = rule.sentiment_filter || 'all';
                document.getElementById('rule-frequency').value = rule.frequency || 'hourly';
                if (filterContactEl) filterContactEl.checked = rule.filter_has_contact_email || false;

                // Hidden fields
                document.getElementById('rule-logic').value = rule.logic_type || 'keywords_or_handles';
                document.getElementById('alert-email').checked = rule.alert_email || false;
                document.getElementById('alert-inapp').checked = rule.alert_in_app !== false;
            }
        }

        modal.classList.remove('hidden');
    },

    /**
     * Save a tracking rule
     */
    async saveRule() {
        const name = document.getElementById('rule-name').value.trim();
        const keywords = document.getElementById('rule-keywords').value
            .split(',')
            .map(k => k.trim())
            .filter(k => k.length > 0);

        // Get handle input
        const handleInput = document.getElementById('rule-handle-input').value.trim();
        const handles = handleInput ? handleInput.split(',').map(h => h.trim()).filter(h => h.length > 0) : [];

        const sentimentFilter = document.getElementById('rule-sentiment').value;
        const selectedPlatform = document.getElementById('rule-platform-select').value;

        const logicType = document.getElementById('rule-logic').value;
        const frequency = document.getElementById('rule-frequency').value;
        const alertEmail = document.getElementById('alert-email').checked;
        const alertInApp = document.getElementById('alert-inapp').checked;
        const filterHasContactEmail = document.getElementById('rule-filter-contact-email')?.checked || false;

        // Determine platforms
        let platforms = [];
        if (selectedPlatform === 'all') {
            platforms = ['twitter', 'linkedin', 'reddit', 'news'];
        } else {
            platforms = [selectedPlatform];
        }

        // Validation
        if (!name) {
            alert('Please enter a rule name');
            return;
        }
        if (keywords.length === 0 && handles.length === 0) {
            alert('Please enter at least one keyword or handle');
            return;
        }

        const ruleData = {
            name,
            keywords,
            handles,
            platforms,
            logic_type: logicType,
            frequency,
            sentiment_filter: sentimentFilter,
            filter_has_contact_email: filterHasContactEmail,
            alert_email: alertEmail,
            alert_in_app: alertInApp,
            status: 'active'
        };

        const editId = document.getElementById('rule-edit-id').value.trim();

        try {
            if (editId) {
                const response = await getAPI().patch(`/api/social-listening/rules/${editId}`, ruleData);
                if (response.rule) {
                    const idx = this.rules.findIndex(r => r.id === editId);
                    if (idx !== -1) this.rules[idx] = { ...this.rules[idx], ...ruleData, id: editId, status: response.rule.status || this.rules[idx].status };
                    this.renderRules();
                    this.updateRuleFilters();
                    document.getElementById('rule-edit-id').value = '';
                    document.getElementById('rule-builder-modal').classList.add('hidden');
                    this.showToast('Rule updated.', 'success');
                }
            } else {
                const response = await getAPI().post('/api/social-listening/rules', ruleData);
                if (response.rule) {
                    this.rules.push(response.rule);
                    this.renderRules();
                    this.updateRuleFilters();
                    document.getElementById('rule-builder-modal').classList.add('hidden');
                    try {
                        this.showToast('Rule created! Fetching content...', 'success');
                        await getAPI().post('/api/social-listening/fetch');
                        console.log('[SocialListening] Triggered background fetch for new rule');
                        this.pollForNewContent();
                    } catch (fetchError) {
                        console.error('[SocialListening] Error triggering fetch:', fetchError);
                    }
                }
            }
        } catch (error) {
            console.error('[SocialListening] Error saving rule:', error);
            this.showToast('Failed to save rule: ' + error.message, 'error');
        }
    },

    /**
     * Delete a tracking rule
     */
    async deleteRule(ruleId) {
        if (!confirm('Are you sure you want to delete this rule? This will also delete all associated content.')) return;

        try {
            const response = await getAPI().delete(`/api/social-listening/rules/${ruleId}`);
            this.rules = this.rules.filter(r => r.id !== ruleId);
            this.renderRules();
            this.updateRuleFilters();

            // Refresh feed to remove deleted content
            await this.loadFeed();

            // Show success message with cleanup info
            const cleanedUp = response.cleaned_up_posts || 0;
            const message = cleanedUp > 0
                ? `Rule deleted. Cleaned up ${cleanedUp} orphaned posts.`
                : 'Rule deleted successfully.';
            this.showToast(message, 'success');
        } catch (error) {
            console.error('[SocialListening] Error deleting rule:', error);
            this.showToast('Failed to delete rule', 'error');
        }
    },

    /**
     * Toggle rule status (active/paused)
     */
    async toggleRuleStatus(ruleId) {
        const rule = this.rules.find(r => r.id === ruleId);
        if (!rule) return;

        const newStatus = rule.status === 'active' ? 'paused' : 'active';

        try {
            await getAPI().patch(`/api/social-listening/rules/${ruleId}`, { status: newStatus });
            rule.status = newStatus;
            this.renderRules();
            this.showToast(`Rule ${newStatus}`, 'success');
        } catch (error) {
            console.error('[SocialListening] Error toggling rule:', error);
        }
    },

    /**
     * Mark all alerts as read
     */
    async markAllAlertsRead() {
        try {
            await getAPI().post('/api/social-listening/alerts/mark-read');
            this.alerts.forEach(a => a.read = true);
            this.renderAlerts();
            this.updateAlertBadge();
        } catch (error) {
            console.error('[SocialListening] Error marking alerts read:', error);
        }
    },

    /**
     * Show AI response modal for a feed item
     */
    showResponseModal(itemId) {
        const item = this.feedItems.find(i => i.id === itemId);
        if (!item) return;

        this.currentPostForResponse = item;

        // Populate original content
        document.getElementById('original-content-box').textContent = item.content;
        document.getElementById('generated-response').value = '';

        document.getElementById('ai-response-modal').classList.remove('hidden');
    },

    /**
     * Open a same-tab email draft for a feed item
     */
    openEmailDraft(itemId) {
        const item = this.feedItems.find(i => i.id === itemId);
        if (!item) return;

        const author = item.author || 'Unknown';
        const handle = item.handle ? ` (${item.handle})` : '';
        const platform = item.platform || '';
        const date = item.posted_at ? new Date(item.posted_at).toLocaleString() : '';
        const url = item.url || '';

        const subject = `Live Feed: ${author}${handle}${platform ? ` - ${platform}` : ''}`;
        const bodyLines = [
            `Author: ${author}${handle}`,
            platform ? `Platform: ${platform}` : null,
            date ? `Posted: ${date}` : null,
            url ? `URL: ${url}` : null,
            '',
            item.content || ''
        ].filter(Boolean);

        const body = bodyLines.join('\n');
        const mailto = `mailto:?subject=${encodeURIComponent(subject)}&body=${encodeURIComponent(body)}`;

        // Open in the same tab
        window.location.href = mailto;
    },

    /**
     * Generate AI response
     */
    async generateResponse() {
        if (!this.currentPostForResponse) return;

        const intent = document.getElementById('response-intent').value;
        const tone = document.getElementById('response-tone').value;
        const length = document.getElementById('response-length').value;

        const statusEl = document.getElementById('ai-response-status');
        const responseTextarea = document.getElementById('generated-response');

        statusEl.classList.remove('hidden');
        responseTextarea.value = '';

        try {
            const response = await getAPI().post('/api/social-listening/generate-response', {
                original_content: this.currentPostForResponse.content,
                platform: this.currentPostForResponse.platform,
                intent,
                tone,
                length
            });

            if (response.response) {
                responseTextarea.value = response.response;
            }
        } catch (error) {
            console.error('[SocialListening] Error generating response:', error);
            responseTextarea.value = 'Error generating response. Please try again.';
        } finally {
            statusEl.classList.add('hidden');
        }
    },

    /**
     * Copy generated response to clipboard
     */
    copyResponse() {
        const responseText = document.getElementById('generated-response').value;
        if (!responseText) return;

        navigator.clipboard.writeText(responseText).then(() => {
            this.showToast('Response copied to clipboard!', 'success');
        });
    },

    /**
     * Generate PDF report
     */
    async generateReport() {
        const reportType = document.getElementById('report-type').value;
        const startDate = document.getElementById('report-start-date').value;
        const endDate = document.getElementById('report-end-date').value;
        const source = document.getElementById('report-source')?.value || 'all';
        const platform = document.getElementById('report-platform')?.value || 'all';
        const minRelevance = parseInt(document.getElementById('report-relevance')?.value || '0');

        // Get selected rules
        const ruleSelect = document.getElementById('report-rules');
        let ruleIds = [];
        if (ruleSelect) {
            ruleIds = Array.from(ruleSelect.selectedOptions)
                .map(opt => opt.value)
                .filter(v => v !== 'all');
        }

        if (!startDate || !endDate) {
            this.showToast('Please select a date range', 'error');
            return;
        }

        const reportPreview = document.getElementById('report-preview');

        // Show immediate notification to user
        this.showToast('Report generation started! Analyzing your data...', 'info');

        try {
            // Show loading state with progress in the preview area
            const reportTypeDisplay = reportType.split('_').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
            reportPreview.innerHTML = `
                <div class="report-loading">
                    <div class="loading-spinner"></div>
                    <h3 style="margin: 0 0 10px 0; color: var(--text-primary);">Generating Your ${reportTypeDisplay} Report</h3>
                    <p style="margin: 0 0 5px 0; color: var(--text-secondary);">Analyzing social media data from ${startDate} to ${endDate}...</p>
                    <p style="margin: 0 0 5px 0; color: var(--text-secondary); font-size: 13px;">Processing monitoring data and compiling insights</p>
                    <p style="margin: 0; color: var(--text-secondary); font-size: 12px;">This may take a few moments depending on the date range selected</p>
                    <div style="margin-top: 20px; width: 100%; max-width: 200px;">
                        <div style="height: 4px; background: var(--border); border-radius: 2px; overflow: hidden;">
                            <div style="height: 100%; background: var(--accent); width: 0%; animation: progress 2s ease-in-out infinite;"></div>
                        </div>
                    </div>
                </div>
            `;

            // Add progress animation
            const style = document.createElement('style');
            style.textContent = `
                @keyframes progress {
                    0% { width: 0%; }
                    50% { width: 70%; }
                    100% { width: 100%; }
                }
            `;
            document.head.appendChild(style);

            const response = await getAPI().post('/api/social-listening/reports/generate', {
                type: reportType,
                start_date: startDate,
                end_date: endDate,
                rule_ids: ruleIds,
                source: source,
                platform: platform,
                min_relevance: minRelevance
            });

            if (response.report_content) {
                // Display the clean report content
                const formattedContent = response.report_content
                    .replace(/\n/g, '<br>')
                    .replace(/^([A-Z\s]+)$/gm, '<h3 style="color: var(--text-primary); margin: 25px 0 12px 0; font-weight: 600; font-size: 16px; border-bottom: 2px solid var(--accent); padding-bottom: 8px;">$1</h3>')
                    .replace(/^(- .*)$/gm, '<div style="margin: 8px 0; padding: 8px 0 8px 20px; border-left: 3px solid var(--border); background: rgba(255,255,255,0.02);">$1</div>')
                    .replace(/^(\s{2}- .*)$/gm, '<div style="margin: 5px 0; margin-left: 30px; color: var(--text-secondary); font-size: 13px;">$1</div>');

                reportPreview.innerHTML = `
                    <div class="report-content-container">
                        <div class="report-header">
                            <div class="report-actions">
                                <button onclick="downloadReportText('${response.report_id}')" class="btn-primary btn-download" title="Download report as PDF file">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path>
                                        <polyline points="14,2 14,8 20,8"></polyline>
                                        <line x1="16" y1="13" x2="8" y2="13"></line>
                                        <line x1="16" y1="17" x2="8" y2="17"></line>
                                        <polyline points="10,9 9,9 8,9"></polyline>
                                    </svg>
                                    Download PDF
                                </button>
                                <button onclick="printReport()" class="btn-secondary" title="Print report">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <polyline points="6 9 6 2 18 2 18 9"></polyline>
                                        <path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path>
                                        <rect x="6" y="14" width="12" height="8"></rect>
                                    </svg>
                                    Print
                                </button>
                            </div>
                            <div class="report-meta">
                                <span class="report-type-badge">${reportType.charAt(0).toUpperCase() + reportType.slice(1)} Report</span>
                                <span class="report-date">Generated: ${new Date().toLocaleDateString()}</span>
                            </div>
                        </div>
                        <div class="report-content">
                            ${formattedContent}
                        </div>
                        <div class="report-footer">
                            <p style="margin: 0; font-size: 12px; color: var(--text-secondary); text-align: center;">
                                Report generated successfully • Ready for PDF download
                            </p>
                        </div>
                    </div>
                `;

                this.showToast('Report generated successfully! Check the preview and download PDF options.', 'success');
            }
        } catch (error) {
            console.error('[SocialListening] Error generating report:', error);

            // Show detailed error message
            let errorMessage = 'Failed to generate report. Please try again.';
            if (error.message) {
                errorMessage += ` Error: ${error.message}`;
            }

            reportPreview.innerHTML = `
                <div style="display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 60px 20px; text-align: center;">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#e74c3c" stroke-width="1" stroke-linecap="round" stroke-linejoin="round" style="margin-bottom: 20px;">
                        <circle cx="12" cy="12" r="10"></circle>
                        <line x1="15" y1="9" x2="9" y2="15"></line>
                        <line x1="9" y1="9" x2="15" y2="15"></line>
                    </svg>
                    <h3 style="margin: 0 0 10px 0; color: #e74c3c;">Report Generation Failed</h3>
                    <p style="margin: 0; color: var(--text-secondary); line-height: 1.5;">${errorMessage}</p>
                    <button onclick="SocialListening.generateReport()" class="btn-primary" style="margin-top: 20px;">
                        Try Again
                    </button>
                </div>
            `;

            this.showToast('Failed to generate report', 'error');
        }
    },

    /**
     * Mark feed item as important
     */
    async markImportant(itemId) {
        try {
            await getAPI().post(`/api/social-listening/feed/${itemId}/mark-important`);
            const item = this.feedItems.find(i => i.id === itemId);
            if (item) item.important = true;

            // Add red highlight to the card
            const card = document.querySelector(`[data-item-id="${itemId}"]`);
            if (card) {
                card.classList.add('important');
            }

            this.showToast('Post saved to Saved Posts', 'success');
        } catch (error) {
            console.error('[SocialListening] Error marking important:', error);
        }
    },

    /**
     * Save feed item
     */
    async saveItem(itemId) {
        try {
            await getAPI().post(`/api/social-listening/feed/${itemId}/save`);
            const item = this.feedItems.find(i => i.id === itemId);
            if (item) item.saved = true;
            this.showToast('Item saved', 'success');
        } catch (error) {
            console.error('[SocialListening] Error saving item:', error);
        }
    },

    /**
     * Unsave/unmark item as important
     */
    async unsaveItem(itemId) {
        try {
            await getAPI().post(`/api/social-listening/feed/${itemId}/unmark-important`);

            // Remove from saved posts array
            this.savedPosts = this.savedPosts.filter(i => i.id !== itemId);

            // Update feed items if present
            const item = this.feedItems.find(i => i.id === itemId);
            if (item) {
                item.important = false;
                item.saved = false;
            }

            // Re-render saved posts
            this.renderSavedPosts();

            this.showToast('Post removed from saved', 'success');
        } catch (error) {
            console.error('[SocialListening] Error unsaving item:', error);
        }
    },

    /**
     * Load saved/important posts
     */
    async loadSavedPosts() {
        try {
            // Load posts that are marked as important or saved
            const response = await getAPI().get('/api/social-listening/feed?limit=100');

            // Filter for saved or important posts
            this.savedPosts = response.items.filter(item => item.important || item.saved);

            this.renderSavedPosts();
        } catch (error) {
            console.error('[SocialListening] Error loading saved posts:', error);
            this.savedPosts = [];
            this.renderSavedPosts();
        }
    },

    /**
     * Render saved posts
     */
    renderSavedPosts() {
        const container = document.getElementById('saved-posts-content');
        if (!container) return;

        if (!this.savedPosts || this.savedPosts.length === 0) {
            container.innerHTML = `
                <div class="feed-empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24"
                        fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round"
                        stroke-linejoin="round">
                        <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path>
                    </svg>
                    <h3>No saved posts yet</h3>
                    <p>Click the star button on posts in the Live Feed to save them here.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.savedPosts.map(item => {
            const content = item.content || '';
            const isLongContent = content.length > 300;
            const truncatedContent = isLongContent ? content.substring(0, 300) + '...' : content;

            return `
            <div class="feed-card important" data-item-id="${item.id}">
                <div class="feed-card-header">
                    <div class="platform-badge ${item.platform}">${this.getPlatformIcon(item.platform)}</div>
                    <div class="feed-card-author">
                        <strong>${this.escapeHtml(item.author || 'Unknown')}</strong>
                        <span>${this.escapeHtml(item.handle || '')}</span>
                    </div>
                </div>
                <div class="feed-card-content ${isLongContent ? 'truncated' : ''}" data-full-content="${this.escapeHtml(content)}" data-truncated="${isLongContent}">
                    <span class="content-text">${this.escapeHtml(truncatedContent)}</span>
                    ${isLongContent ? `<button class="expand-content-btn" onclick="SocialListening.toggleContentExpand(this)">Show more</button>` : ''}
                </div>
                <div class="feed-card-meta">
                    <span class="feed-card-rule">${this.escapeHtml(item.rule_name || 'Manual')}</span>
                    <span>${this.formatDate(item.posted_at)}</span>
                </div>
                <div class="feed-card-actions">
                    <button class="feed-action-btn primary" onclick="SocialListening.showResponseModal('${item.id}')">
                        Generate Reply
                    </button>
                    <button class="feed-action-btn" onclick="SocialListening.unsaveItem('${item.id}')">Unsave</button>
                    <a href="${item.url}" target="_blank" class="feed-action-btn">Open</a>
                </div>
            </div>
            `;
        }).join('');
    },

    // ==================== RENDERING ====================

    /**
     * Render tracking rules list
     */
    renderRules() {
        const container = document.getElementById('rules-list');
        if (!container) return;

        if (this.rules.length === 0) {
            container.innerHTML = `
                <div class="rules-empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"></path></svg>
                    <h3>No tracking rules configured</h3>
                    <p>Create rules to monitor keywords, handles, and topics across social platforms.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.rules.map(rule => `
            <div class="rule-card" data-rule-id="${rule.id}">
                <div class="rule-card-info">
                    <h4>${this.escapeHtml(rule.name)}</h4>
                    <div class="rule-tags">
                        ${(rule.keywords || []).slice(0, 3).map(k => `<span class="rule-tag keyword">${this.escapeHtml(k)}</span>`).join('')}
                        ${(rule.keywords || []).length > 3 ? `<span class="rule-tag keyword">+${rule.keywords.length - 3} more</span>` : ''}
                        ${(rule.handles || []).slice(0, 2).map(h => `<span class="rule-tag handle">${this.escapeHtml(h)}</span>`).join('')}
                        ${(rule.platforms || []).map(p => `<span class="rule-tag platform">${p}</span>`).join('')}
                    </div>
                    <div class="rule-meta">
                        <span>Logic: ${this.formatLogicType(rule.logic_type)}</span>
                        <span>Frequency: ${rule.frequency}</span>
                        <span class="rule-status ${rule.status}">${rule.status}</span>
                    </div>
                </div>
                <div class="rule-card-actions">
                    <button class="btn-icon" onclick="SocialListening.toggleRuleStatus('${rule.id}')" title="${rule.status === 'active' ? 'Pause' : 'Resume'}">
                        ${rule.status === 'active' ? '⏸' : '▶'}
                    </button>
                    <button class="btn-icon" onclick="SocialListening.showRuleModal('${rule.id}')" title="Edit">✏️</button>
                    <button class="btn-icon delete" onclick="SocialListening.deleteRule('${rule.id}')" title="Delete">🗑</button>
                </div>
            </div>
        `).join('');
    },

    /**
     * Render feed items
     */
    renderFeed() {
        const container = document.getElementById('feed-content');
        if (!container) return;

        if (this.feedItems.length === 0) {
            // If we are currently polling for new content, show loading state instead of empty state
            if (this.isPolling) {
                container.innerHTML = `
                    <div class="feed-loading-state" style="padding: 60px 20px; text-align: center; color: var(--text-secondary); display: flex; flex-direction: column; align-items: center;">
                        <div class="spinner" style="border: 3px solid rgba(255,255,255,0.1); border-top: 3px solid var(--accent); border-radius: 50%; width: 30px; height: 30px; animation: spin 1s linear infinite; margin-bottom: 15px;"></div>
                        <p style="margin: 0; font-weight: 500;">Searching active sources...</p>
                        <p style="margin-top: 5px; font-size: 0.85em; opacity: 0.7;">This may take up to 30 seconds</p>
                    </div>
                `;
                return;
            }

            container.innerHTML = `
                <div class="feed-empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                    <h3>No monitored content yet</h3>
                    <p>Create a tracking rule to start monitoring social media content.</p>
                    <button class="btn-primary" onclick="showMonitoringSection('rules')">Create First Rule</button>
                </div>
            `;
            return;
        }

        container.innerHTML = this.feedItems.map(item => {
            const qualityScore = item.quality_score || 5;
            const qualityClass = qualityScore >= 8 ? 'high' : qualityScore >= 6 ? 'medium' : 'low';

            // Handle longer authentic content with truncation
            const content = item.content || '';
            const isLongContent = content.length > 300;
            const truncatedContent = isLongContent ? content.substring(0, 300) + '...' : content;

            // Format the posted date for prominent display
            const postedDate = item.posted_at ? this.formatPostedDate(item.posted_at) : '';
            const fullDate = item.posted_at ? new Date(item.posted_at).toLocaleDateString('en-US', {
                year: 'numeric', month: 'short', day: 'numeric'
            }) : '';

            // Gemini analysis data
            const sentiment = item.sentiment || 'neutral';
            const sentimentClass = sentiment === 'positive' ? 'sentiment-positive' :
                sentiment === 'negative' ? 'sentiment-negative' : 'sentiment-neutral';
            const relevanceScore = Math.round((item.relevance_score || 0.5) * 100);
            const matchedKeywords = item.matched_keywords || [];
            const explanation = item.explanation || '';

            return `
            <div class="feed-card ${item.important ? 'important' : ''}" data-item-id="${item.id}">
                <div class="feed-card-header">
                    <div class="platform-badge ${item.platform}">${this.getPlatformIcon(item.platform)}</div>
                    <div class="feed-card-author">
                        <strong>${this.escapeHtml(item.author || 'Unknown')}</strong>
                        <span>${this.escapeHtml(item.handle || '')}</span>
                    </div>
                    <div class="posted-date-badge ${fullDate ? '' : 'date-unknown'} ${item.confidence_level ? 'conf-' + item.confidence_level.toLowerCase() : ''}" 
                         title="${fullDate ? `Verified Date (Source: ${item.timestamp_source}, Confidence: ${item.confidence_level})` : 'No date found in content'}">
                        <span class="date-label">📅</span>
                        <span class="date-value">${fullDate || 'Date not found'}</span>
                        ${item.confidence_level === 'HIGH' ? '<span class="conf-tick">✓</span>' : ''}
                    </div>
                </div>

                <!-- Gemini Analysis Row -->
                <div class="gemini-analysis-row">
                    <div class="sentiment-badge ${sentimentClass}">
                        ${sentiment === 'positive' ? '😊' : sentiment === 'negative' ? '😟' : '😐'} ${sentiment.charAt(0).toUpperCase() + sentiment.slice(1)}
                    </div>
                    <div class="relevance-badge" title="Relevance to your keywords">
                        <span class="relevance-score">${relevanceScore}%</span> Match
                    </div>
                </div>

                ${matchedKeywords.length > 0 ? `
                <div class="matched-keywords-row">
                    <span class="keywords-label">Keywords:</span>
                    ${matchedKeywords.slice(0, 5).map(kw => `<span class="keyword-pill">${this.escapeHtml(kw)}</span>`).join('')}
                </div>
                ` : ''}

                ${explanation ? `
                <div class="explanation-row">
                    <span class="explanation-text">💡 ${this.escapeHtml(explanation)}</span>
                </div>
                ` : ''}

                <div class="feed-card-content ${isLongContent ? 'truncated' : ''}" data-full-content="${this.escapeHtml(content)}" data-truncated="${isLongContent}">
                    <span class="content-text">${this.escapeHtml(truncatedContent)}</span>
                    ${isLongContent ? `<button class="expand-content-btn" onclick="SocialListening.toggleContentExpand(this)">Show more</button>` : ''}
                </div>
                <div class="feed-card-meta">
                    <span class="feed-card-rule">${this.escapeHtml(item.rule_name || 'Manual')}</span>
                    <span class="full-date-text">${fullDate}</span>
                </div>
                <div class="feed-card-actions">
                    <button class="feed-action-btn primary" onclick="SocialListening.showResponseModal('${item.id}')">
                        Generate Reply
                    </button>
                    <button class="feed-action-btn" onclick="SocialListening.saveItem('${item.id}')">Save</button>
                    <button class="feed-action-btn" onclick="SocialListening.markImportant('${item.id}')">⭐</button>
                    <button class="feed-action-btn" onclick="SocialListening.openEmailDraft('${item.id}')">Draft email</button>
                    <a href="${item.url}" target="_blank" class="feed-action-btn">Open</a>
                </div>
            </div>
            `;
        }).join('');
    },

    /**
     * Render alerts list
     */
    renderAlerts() {
        const container = document.getElementById('alerts-list');
        if (!container) return;

        if (this.alerts.length === 0) {
            container.innerHTML = `
                <div class="alerts-empty-state">
                    <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1" stroke-linecap="round" stroke-linejoin="round"><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"></path><path d="M13.73 21a2 2 0 0 1-3.46 0"></path></svg>
                    <h3>No alerts yet</h3>
                    <p>Alerts will appear here when your tracking rules match new content.</p>
                </div>
            `;
            return;
        }

        container.innerHTML = this.alerts.map(alert => `
            <div class="alert-item ${alert.read ? '' : 'unread'}" data-alert-id="${alert.id}">
                <div class="alert-content">
                    <strong>${this.escapeHtml(alert.title)}</strong>
                    <span>${this.escapeHtml(alert.message)}</span>
                </div>
                <span class="alert-time">${this.formatDate(alert.created_at)}</span>
            </div>
        `).join('');
    },

    /**
     * Render analytics dashboard
     */
    renderAnalytics() {
        // Sentiment chart
        const { positive, neutral, negative } = this.analytics.sentiment;
        const total = positive + neutral + negative || 1;

        const positiveBar = document.querySelector('.sentiment-bar.positive');
        const neutralBar = document.querySelector('.sentiment-bar.neutral');
        const negativeBar = document.querySelector('.sentiment-bar.negative');

        if (positiveBar) {
            positiveBar.style.height = `${Math.max(40, (positive / total) * 120)}px`;
            positiveBar.querySelector('.sentiment-value').textContent = `${Math.round((positive / total) * 100)}%`;
        }
        if (neutralBar) {
            neutralBar.style.height = `${Math.max(40, (neutral / total) * 120)}px`;
            neutralBar.querySelector('.sentiment-value').textContent = `${Math.round((neutral / total) * 100)}%`;
        }
        if (negativeBar) {
            negativeBar.style.height = `${Math.max(40, (negative / total) * 120)}px`;
            negativeBar.querySelector('.sentiment-value').textContent = `${Math.round((negative / total) * 100)}%`;
        }

        // Update stat cards
        const totalPostsEl = document.getElementById('total-posts-count');
        if (totalPostsEl) {
            totalPostsEl.textContent = this.analytics.total_posts || 0;
        }

        const activeRulesEl = document.getElementById('active-rules-count');
        if (activeRulesEl) {
            activeRulesEl.textContent = this.rules.filter(r => r.status === 'active').length;
        }

        // Platform stats
        const platforms = this.analytics.platforms;
        document.querySelectorAll('.platform-stat').forEach(stat => {
            const platform = stat.querySelector('.platform-icon')?.classList[1];
            if (platform && platforms[platform] !== undefined) {
                stat.querySelector('.platform-count').textContent = platforms[platform];
            }
        });

        // Keywords cloud
        const keywordsContainer = document.getElementById('keywords-cloud');
        if (keywordsContainer && this.analytics.keywords.length > 0) {
            keywordsContainer.innerHTML = this.analytics.keywords.map((kw, i) => `
                <span class="keyword-tag ${i < 3 ? 'large' : i < 7 ? 'medium' : ''}">${this.escapeHtml(kw.keyword)} (${kw.count})</span>
            `).join('');
        }
    },

    /**
     * Update rule filter dropdown
     */
    updateRuleFilters() {
        const ruleFilter = document.getElementById('feed-rule-filter');
        const reportRules = document.getElementById('report-rules');

        if (ruleFilter) {
            ruleFilter.innerHTML = '<option value="all">All Rules</option>' +
                this.rules.map(r => `<option value="${r.id}">${this.escapeHtml(r.name)}</option>`).join('');
        }

        if (reportRules) {
            reportRules.innerHTML = '<option value="all" selected>All Rules</option>' +
                this.rules.map(r => `<option value="${r.id}">${this.escapeHtml(r.name)}</option>`).join('');
        }
    },

    /**
     * Update alert badge count
     */
    updateAlertBadge() {
        const badge = document.getElementById('alert-badge');
        if (!badge) return;

        const unreadCount = this.alerts.filter(a => !a.read).length;
        if (unreadCount > 0) {
            badge.textContent = unreadCount;
            badge.classList.remove('hidden');
        } else {
            badge.classList.add('hidden');
        }
    },

    // ==================== HELPERS ====================

    /**
     * Get platform icon
     */
    getPlatformIcon(platform) {
        const icons = {
            twitter: '𝕏',
            linkedin: 'in',
            reddit: 'r/',
            news: '📰'
        };
        return icons[platform] || '?';
    },

    /**
     * Format logic type for display
     */
    formatLogicType(type) {
        const labels = {
            keywords_only: 'Keywords Only',
            handles_only: 'Handles Only',
            keywords_and_handles: 'Keywords AND Handles',
            keywords_or_handles: 'Keywords OR Handles',
            exclude_keywords: 'Exclude Keywords'
        };
        return labels[type] || type;
    },

    /**
     * Format date for display
     */
    formatDate(dateString) {
        if (!dateString) return '';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffMins = Math.floor(diffMs / 60000);
        const diffHours = Math.floor(diffMs / 3600000);
        const diffDays = Math.floor(diffMs / 86400000);

        if (diffMins < 1) return 'Just now';
        if (diffMins < 60) return `${diffMins}m ago`;
        if (diffHours < 24) return `${diffHours}h ago`;
        if (diffDays < 7) return `${diffDays}d ago`;

        return date.toLocaleDateString();
    },

    /**
     * Format posted date for prominent display in card header
     * Returns a clean, readable date format
     */
    formatPostedDate(dateString) {
        if (!dateString) return 'Unknown';
        const date = new Date(dateString);
        const now = new Date();
        const diffMs = now - date;
        const diffDays = Math.floor(diffMs / 86400000);

        // For today
        if (diffDays === 0) {
            const diffHours = Math.floor(diffMs / 3600000);
            if (diffHours < 1) return 'Just now';
            return `${diffHours}h ago`;
        }

        // For yesterday
        if (diffDays === 1) return 'Yesterday';

        // For this week
        if (diffDays < 7) return `${diffDays} days ago`;

        // For older dates, show the actual date
        const options = { month: 'short', day: 'numeric' };
        if (date.getFullYear() !== now.getFullYear()) {
            options.year = 'numeric';
        }
        return date.toLocaleDateString('en-US', options);
    },

    /**
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Toggle expand/collapse for long content in feed cards
     */
    toggleContentExpand(button) {
        const contentDiv = button.parentElement;
        const contentSpan = contentDiv.querySelector('.content-text');
        const fullContent = contentDiv.getAttribute('data-full-content');
        const isTruncated = contentDiv.getAttribute('data-truncated') === 'true';

        if (!isTruncated) return;

        const isExpanded = contentDiv.classList.contains('expanded');

        if (isExpanded) {
            // Collapse: show truncated content
            const truncated = fullContent.substring(0, 300) + '...';
            contentSpan.textContent = truncated;
            contentDiv.classList.remove('expanded');
            button.textContent = 'Show more';
        } else {
            // Expand: show full content
            contentSpan.textContent = fullContent;
            contentDiv.classList.add('expanded');
            button.textContent = 'Show less';
        }
    },

    /**
     * Poll for new content
     */
    async pollForNewContent(attempts = 15) {
        console.log('[SocialListening] Starting polling for new content...');
        this.isPolling = true;

        // Force immediate render if empty to show loading state
        if (this.feedItems.length === 0) {
            this.renderFeed();
        }

        const initialCount = this.feedItems.length;

        for (let i = 0; i < attempts; i++) {
            // Adaptive polling: Check frequent initially (1s), then back off (3s)
            // This ensures instant feedback when the first streaming result hits the DB
            const delay = i < 6 ? 1500 : 3000;

            await new Promise(resolve => setTimeout(resolve, delay));

            // Silently reload feed data
            await this.loadFeed(true);

            if (this.feedItems.length > initialCount) {
                const newCount = this.feedItems.length - initialCount;
                this.showToast(`Found ${newCount} new items!`, 'success');
                this.isPolling = false;
                this.renderFeed(); // Re-render to clear loading state if any
                return;
            }
        }
        console.log('[SocialListening] Polling complete, no new items found yet.');
        this.isPolling = false;
        this.renderFeed(); // Re-render to clear loading state
    },

    /**
     * Show toast notification
     */
    showToast(message, type = 'success') {
        // Use existing toast system if available
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
            return;
        }

        // Fallback toast
        let container = document.querySelector('.toast-container');
        if (!container) {
            container = document.createElement('div');
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toast = document.createElement('div');
        toast.className = `toast ${type}`;
        toast.textContent = message;
        container.appendChild(toast);

        setTimeout(() => toast.classList.add('visible'), 10);
        setTimeout(() => {
            toast.classList.remove('visible');
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    }
};

// Event listeners for filter changes
document.addEventListener('DOMContentLoaded', () => {
    const ruleFilter = document.getElementById('feed-rule-filter');
    const platformFilter = document.getElementById('feed-platform-filter');
    const analyticsTimeframe = document.getElementById('analytics-timeframe');

    if (ruleFilter) {
        ruleFilter.addEventListener('change', () => SocialListening.loadFeed());
    }
    if (platformFilter) {
        platformFilter.addEventListener('change', () => SocialListening.loadFeed());
    }
    if (analyticsTimeframe) {
        analyticsTimeframe.addEventListener('change', () => SocialListening.loadAnalytics());
    }
});

/**
 * Load user's current notification email
 */
async function loadUserNotificationEmail() {
    try {
        const response = await getAPI().get('/api/social-listening/user/notification-email');

        if (response.has_email) {
            const emailInput = document.getElementById('user-notification-email');
            emailInput.placeholder = `Current: ${response.email} - Enter new email to update`;
            showEmailStatus(`📧 Current notification email: ${response.email}`, 'info');
        }
    } catch (error) {
        console.log('[Email] Could not load current email:', error.message);
    }
}

/**
 * Save user notification email
 */
async function saveUserNotificationEmail() {
    const emailInput = document.getElementById('user-notification-email');
    const statusDiv = document.getElementById('email-save-status');
    const email = emailInput.value.trim();

    if (!email) {
        showEmailStatus('Please enter a valid email address.', 'error');
        return;
    }

    // Basic email validation
    const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
    if (!emailRegex.test(email)) {
        showEmailStatus('Please enter a valid email address format.', 'error');
        return;
    }

    try {
        showEmailStatus('Saving email...', 'info');

        const response = await getAPI().post('/api/social-listening/user/notification-email', { email });

        if (response.success) {
            showEmailStatus('✅ Email saved successfully! You will now receive instant notifications.', 'success');
            // Keep the email visible and update placeholder to show it's saved
            emailInput.placeholder = `Current: ${email} - Enter new email to update`;

            // Optional: Refresh alerts to show updated status
            setTimeout(() => {
                SocialListening.loadAlerts();
            }, 1000);

        } else {
            showEmailStatus('Failed to save email. Please try again.', 'error');
        }

    } catch (error) {
        console.error('[Email] Save failed:', error);
        showEmailStatus('Failed to save email. Please check your connection and try again.', 'error');
    }
}

/**
 * Show email save status message
 */
function showEmailStatus(message, type) {
    const statusDiv = document.getElementById('email-save-status');

    statusDiv.textContent = message;
    statusDiv.style.display = 'block';

    // Remove existing classes
    statusDiv.classList.remove('success', 'error', 'info');

    // Add appropriate styling based on type
    if (type === 'success') {
        statusDiv.style.backgroundColor = '#d4edda';
        statusDiv.style.color = '#155724';
        statusDiv.style.border = '1px solid #c3e6cb';
    } else if (type === 'error') {
        statusDiv.style.backgroundColor = '#f8d7da';
        statusDiv.style.color = '#721c24';
        statusDiv.style.border = '1px solid #f5c6cb';
    } else if (type === 'info') {
        statusDiv.style.backgroundColor = '#cce7ff';
        statusDiv.style.color = '#004085';
        statusDiv.style.border = '1px solid #b3d7ff';
    }

    // Auto-hide success messages after 5 seconds
    if (type === 'success') {
        setTimeout(() => {
            statusDiv.style.display = 'none';
        }, 5000);
    }
}

/**
/**
 * Download report as PDF file
 */

function downloadReportText(reportId) {
    const reportContent = document.querySelector('.report-content');
    if (!reportContent) return;

    // Get report metadata
    const reportType = document.querySelector('.report-type-badge')?.textContent || 'Social Media Report';
    const reportDate = document.querySelector('.report-date')?.textContent || '';

    // Create a clean HTML version for PDF generation
    const pdfContent = `
        <div style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; line-height: 1.6;">
            <div style="text-align: center; border-bottom: 2px solid #3b82f6; padding-bottom: 20px; margin-bottom: 30px;">
                <h1 style="color: #1f2937; margin: 0; font-size: 28px;">${reportType}</h1>
                <p style="color: #6b7280; margin: 10px 0 0 0; font-size: 14px;">${reportDate}</p>
            </div>
            <div style="color: #1f2937;">
                ${reportContent.innerHTML
            .replace(/style="[^"]*color:[^"]*"/g, '') // Remove inline color styles
            .replace(/class="[^"]*"/g, '') // Remove classes
            .replace(/<br\s*\/?>/g, '<br>') // Normalize br tags
        }
            </div>
        </div>
    `;

    // PDF generation options
    const options = {
        margin: [0.5, 0.5, 0.5, 0.5], // top, left, bottom, right in inches
        filename: `social_monitoring_report_${reportId}.pdf`,
        image: { type: 'jpeg', quality: 0.98 },
        html2canvas: {
            scale: 2,
            useCORS: true,
            letterRendering: true
        },
        jsPDF: {
            unit: 'in',
            format: 'a4',
            orientation: 'portrait'
        }
    };

    // Create a temporary element for PDF generation
    const tempDiv = document.createElement('div');
    tempDiv.innerHTML = pdfContent;
    tempDiv.style.position = 'absolute';
    tempDiv.style.left = '-9999px';
    tempDiv.style.top = '-9999px';
    document.body.appendChild(tempDiv);

    // Generate and download PDF
    html2pdf()
        .set(options)
        .from(tempDiv)
        .save()
        .then(() => {
            // Clean up
            document.body.removeChild(tempDiv);

            // Show success message
            if (window.SocialListening && window.SocialListening.showToast) {
                window.SocialListening.showToast('PDF report downloaded successfully! Check your downloads folder.', 'success');
            }

            // Visual confirmation in download button
            const downloadBtn = document.querySelector('.btn-download');
            if (downloadBtn) {
                downloadBtn.classList.add('success');
                setTimeout(() => {
                    downloadBtn.classList.remove('success');
                }, 2000);
            }
        })
        .catch((error) => {
            console.error('PDF generation failed:', error);
            document.body.removeChild(tempDiv);

            if (window.SocialListening && window.SocialListening.showToast) {
                window.SocialListening.showToast('Failed to generate PDF. Please try again.', 'error');
            }
        });
    const downloadBtn = document.querySelector('.btn-download');
    if (downloadBtn) {
        const originalText = downloadBtn.innerHTML;
        const originalClass = downloadBtn.className;

        downloadBtn.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"></polyline></svg> Downloaded!';
        downloadBtn.className = 'btn-primary btn-download success';
        downloadBtn.disabled = true;

        // Reset button after 3 seconds
        setTimeout(() => {
            downloadBtn.innerHTML = originalText;
            downloadBtn.className = originalClass;
            downloadBtn.disabled = false;
        }, 3000);
    }
}

/**
 * Print the report
 */
function printReport() {
    const reportContent = document.querySelector('.report-content');
    if (!reportContent) return;

    const reportType = document.querySelector('.report-type-badge')?.textContent || 'Social Media Monitoring Report';
    const reportDate = document.querySelector('.report-date')?.textContent || '';

    const printWindow = window.open('', '_blank');
    const content = reportContent.innerHTML;

    printWindow.document.write(`
        <!DOCTYPE html>
        <html>
        <head>
            <title>${reportType}</title>
            <style>
                @media print {
                    body { margin: 0; }
                    .no-print { display: none; }
                }
                body {
                    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif;
                    font-size: 12px;
                    line-height: 1.6;
                    margin: 20px;
                    color: #333;
                }
                h3 {
                    color: #2563eb;
                    margin: 25px 0 12px 0;
                    font-weight: 600;
                    font-size: 14px;
                    border-bottom: 2px solid #2563eb;
                    padding-bottom: 8px;
                    text-transform: uppercase;
                    letter-spacing: 0.5px;
                }
                .report-header {
                    text-align: center;
                    margin-bottom: 30px;
                    padding-bottom: 20px;
                    border-bottom: 1px solid #ddd;
                }
                .report-title {
                    font-size: 18px;
                    font-weight: bold;
                    margin-bottom: 5px;
                }
                .report-date {
                    color: #666;
                    font-size: 11px;
                }
                .report-content div[style*="border-left"] {
                    margin: 8px 0;
                    padding: 8px 0 8px 20px;
                    border-left: 3px solid #ddd;
                    background: #f9f9f9;
                }
                .report-content div[style*="margin-left"] {
                    margin: 5px 0;
                    margin-left: 30px;
                    color: #666;
                    font-size: 11px;
                    font-style: italic;
                }
            </style>
        </head>
        <body>
            <div class="report-header">
                <div class="report-title">${reportType}</div>
                <div class="report-date">${reportDate}</div>
            </div>
            <div class="report-content">${content}</div>
        </body>
        </html>
    `);

    printWindow.document.close();

    // Wait a bit for content to load, then print
    setTimeout(() => {
        printWindow.print();
    }, 500);
}

// Export for global access
window.SocialListening = SocialListening;

// Export for global access
window.SocialListening = SocialListening;
