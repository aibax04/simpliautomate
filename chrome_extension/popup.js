document.addEventListener('DOMContentLoaded', async () => {
  const currentUrlEl = document.getElementById('current-url');
  const apiTokenEl = document.getElementById('api-token');
  const sendBtn = document.getElementById('send-btn');
  const logoutBtn = document.getElementById('logout-btn');
  const statusEl = document.getElementById('status');
  const container = document.querySelector('.container');

  let currentToken = '';

  // Get current tab URL
  const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
  if (tab && tab.url) {
    currentUrlEl.textContent = tab.url;
  } else {
    currentUrlEl.textContent = 'Unable to get URL';
    sendBtn.disabled = true;
  }

  // Load saved token and update UI
  function updateAuthState() {
    chrome.storage.local.get(['simplii_token'], (result) => {
      currentToken = result.simplii_token || '';
      apiTokenEl.value = currentToken;

      if (currentToken) {
        container.classList.remove('logged-out');
        container.classList.add('logged-in');
      } else {
        container.classList.remove('logged-in');
        container.classList.add('logged-out');
      }
    });
  }

  updateAuthState();

  // Save token when changed
  apiTokenEl.addEventListener('input', (e) => {
    const token = e.target.value.trim();
    currentToken = token;
    chrome.storage.local.set({ simplii_token: token });
    updateAuthState();
  });

  // Logout functionality
  logoutBtn.addEventListener('click', () => {
    chrome.storage.local.remove('simplii_token', () => {
      currentToken = '';
      apiTokenEl.value = '';
      updateAuthState();
      showStatus('Logged out successfully', 'success');
      setTimeout(() => statusEl.style.display = 'none', 2000);
    });
  });

  // Send to Simplii
  sendBtn.addEventListener('click', async () => {
    const token = currentToken || apiTokenEl.value.trim();
    const url = currentUrlEl.textContent;

    if (!token) {
      showStatus('Please enter your API token', 'error');
      return;
    }

    if (!url || url === 'Unable to get URL') {
      showStatus('Unable to get current page URL', 'error');
      return;
    }

    // Show loading
    sendBtn.disabled = true;
    sendBtn.classList.add('loading');
    sendBtn.textContent = 'Sending...';

    try {
      const response = await fetch('https://postflow.panscience.ai/api/enqueue-post', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          custom_prompt: url,
          user_prefs: {
            tone: "professional",
            style: "concise",
            platform: "linkedin"
          }
        })
      });

      const data = await response.json();

      if (response.ok) {
        showStatus('Successfully sent to Simplii! Check your queue.', 'success');
        // Save token if entered manually
        if (!currentToken && apiTokenEl.value.trim()) {
          chrome.storage.local.set({ simplii_token: apiTokenEl.value.trim() });
        }
        // Auto-close after success
        setTimeout(() => window.close(), 2500);
      } else {
        showStatus(data.detail || 'Failed to send to Simplii', 'error');
      }
    } catch (error) {
      showStatus('Network error - please check your connection and API token', 'error');
    } finally {
      sendBtn.disabled = false;
      sendBtn.classList.remove('loading');
      sendBtn.textContent = 'Send to Simplii';
    }
  });

  function showStatus(message, type) {
    statusEl.textContent = message;
    statusEl.className = `status ${type}`;
    statusEl.style.display = 'block';
  }
});