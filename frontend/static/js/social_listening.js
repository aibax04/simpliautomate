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
        await this.loadUserNotificationEmail(); // Load user's notification email
        this.updateRuleFilters();
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
     * Load feed items from backend
     */
    async loadFeed() {
        try {
            const ruleFilter = document.getElementById('feed-rule-filter')?.value || 'all';
            const platformFilter = document.getElementById('feed-platform-filter')?.value || 'all';
            
            const params = new URLSearchParams();
            if (ruleFilter !== 'all') params.append('rule_id', ruleFilter);
            if (platformFilter !== 'all') params.append('platform', platformFilter);
            
            const response = await getAPI().get(`/api/social-listening/feed?${params.toString()}`);
            if (response.items) {
                this.feedItems = response.items;
                this.renderFeed();
            }
        } catch (error) {
            console.log('[SocialListening] No feed items:', error.message);
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
     * Refresh the feed - fetches new content from DuckDuckGo based on rules
     */
    async refreshFeed() {
        const refreshBtn = document.querySelector('.btn-refresh');
        if (refreshBtn) {
            refreshBtn.innerHTML = '<div class="mini-spinner"></div> Fetching...';
            refreshBtn.disabled = true;
        }
        
        try {
            // First, trigger the backend to fetch new content from DuckDuckGo
            console.log('[SocialListening] Triggering fetch from DuckDuckGo...');
            const fetchResponse = await getAPI().post('/api/social-listening/fetch');
            console.log('[SocialListening] Fetch response:', fetchResponse);
            
            if (fetchResponse.stats) {
                const stats = fetchResponse.stats;
                this.showToast(
                    `Fetched ${stats.posts_fetched} new posts from ${stats.rules_processed} rules`, 
                    'success'
                );
            }
            
            // Then reload the feed and alerts
            await this.loadFeed();
            await this.loadAlerts();
            await this.loadAnalytics();
        } catch (error) {
            console.error('[SocialListening] Refresh error:', error);
            this.showToast('Error fetching content: ' + error.message, 'error');
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
        document.getElementById('rule-handles').value = '';
        document.getElementById('rule-logic').value = 'keywords_or_handles';
        document.getElementById('rule-frequency').value = 'hourly';
        document.getElementById('alert-email').checked = false;
        document.getElementById('alert-inapp').checked = true;
        
        // Reset platform checkboxes
        document.getElementById('platform-twitter').checked = true;
        document.getElementById('platform-linkedin').checked = true;
        document.getElementById('platform-reddit').checked = false;
        document.getElementById('platform-news').checked = true;
        
        // If editing, populate form
        if (ruleId) {
            const rule = this.rules.find(r => r.id === ruleId);
            if (rule) {
                document.getElementById('rule-name').value = rule.name || '';
                document.getElementById('rule-keywords').value = (rule.keywords || []).join(', ');
                document.getElementById('rule-handles').value = (rule.handles || []).join(', ');
                document.getElementById('rule-logic').value = rule.logic_type || 'keywords_or_handles';
                document.getElementById('rule-frequency').value = rule.frequency || 'hourly';
                document.getElementById('alert-email').checked = rule.alert_email || false;
                document.getElementById('alert-inapp').checked = rule.alert_in_app !== false;
                
                // Platforms
                const platforms = rule.platforms || [];
                document.getElementById('platform-twitter').checked = platforms.includes('twitter');
                document.getElementById('platform-linkedin').checked = platforms.includes('linkedin');
                document.getElementById('platform-reddit').checked = platforms.includes('reddit');
                document.getElementById('platform-news').checked = platforms.includes('news');
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
        const handles = document.getElementById('rule-handles').value
            .split(',')
            .map(h => h.trim())
            .filter(h => h.length > 0);
        const logicType = document.getElementById('rule-logic').value;
        const frequency = document.getElementById('rule-frequency').value;
        const alertEmail = document.getElementById('alert-email').checked;
        const alertInApp = document.getElementById('alert-inapp').checked;
        
        // Get selected platforms
        const platforms = [];
        if (document.getElementById('platform-twitter').checked) platforms.push('twitter');
        if (document.getElementById('platform-linkedin').checked) platforms.push('linkedin');
        if (document.getElementById('platform-reddit').checked) platforms.push('reddit');
        if (document.getElementById('platform-news').checked) platforms.push('news');
        
        // Validation
        if (!name) {
            alert('Please enter a rule name');
            return;
        }
        if (keywords.length === 0 && handles.length === 0) {
            alert('Please enter at least one keyword or handle');
            return;
        }
        if (platforms.length === 0) {
            alert('Please select at least one platform');
            return;
        }
        
        const ruleData = {
            name,
            keywords,
            handles,
            platforms,
            logic_type: logicType,
            frequency,
            alert_email: alertEmail,
            alert_in_app: alertInApp,
            status: 'active'
        };
        
        try {
            const response = await getAPI().post('/api/social-listening/rules', ruleData);
            if (response.rule) {
                this.rules.push(response.rule);
                this.renderRules();
                this.updateRuleFilters();
                document.getElementById('rule-builder-modal').classList.add('hidden');
                this.showToast('Rule created! Fetching content...', 'success');
                
                // Auto-fetch content for the new rule
                setTimeout(() => this.refreshFeed(), 500);
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

        if (!startDate || !endDate) {
            this.showToast('Please select a date range', 'error');
            return;
        }

        const reportPreview = document.getElementById('report-preview');

        // Show immediate notification to user
        this.showToast('Report generation started! Analyzing your data...', 'info');

        try {
            // Show loading state with progress in the preview area
            const reportTypeDisplay = reportType.charAt(0).toUpperCase() + reportType.slice(1);
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
                end_date: endDate
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
            this.renderFeed();
            this.showToast('Marked as important', 'success');
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
            this.showToast('Item saved', 'success');
        } catch (error) {
            console.error('[SocialListening] Error saving item:', error);
        }
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

            return `
            <div class="feed-card ${item.important ? 'important' : ''}" data-item-id="${item.id}">
                <div class="feed-card-header">
                    <div class="platform-badge ${item.platform}">${this.getPlatformIcon(item.platform)}</div>
                    <div class="feed-card-author">
                        <strong>${this.escapeHtml(item.author || 'Unknown')}</strong>
                        <span>${this.escapeHtml(item.handle || '')}</span>
                        <span class="quality-indicator ${qualityClass}" title="Quality Score: ${qualityScore}/10">
                            ${'★'.repeat(Math.max(1, Math.round(qualityScore / 2)))}
                        </span>
                    </div>
                </div>
                <div class="feed-card-content">${this.escapeHtml(item.content)}</div>
                <div class="feed-card-meta">
                    <span class="feed-card-rule">${this.escapeHtml(item.rule_name || 'Manual')}</span>
                    <span>${this.formatDate(item.posted_at)}</span>
                </div>
                <div class="feed-card-actions">
                    <button class="feed-action-btn primary" onclick="SocialListening.showResponseModal('${item.id}')">
                        Generate Reply
                    </button>
                    <button class="feed-action-btn" onclick="SocialListening.saveItem('${item.id}')">Save</button>
                    <button class="feed-action-btn" onclick="SocialListening.markImportant('${item.id}')">⭐</button>
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
     * Escape HTML to prevent XSS
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
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

        const response = await getAPI().post('/api/user/notification-email', { email });

        if (response.success) {
            showEmailStatus('✅ Email saved successfully! You will now receive instant notifications.', 'success');
            emailInput.value = ''; // Clear the input

            // Reload the user's notification email to update the UI
            await loadUserNotificationEmail();

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
