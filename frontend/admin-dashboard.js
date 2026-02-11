/* Admin Dashboard JavaScript */

const API_BASE = '/api';

// State
let currentUser = null;
let wsConnection = null;
let currentRunId = null;

// DOM Elements
const loginPage = document.getElementById('loginPage');
const dashboardPage = document.getElementById('dashboardPage');
const loginForm = document.getElementById('loginForm');
const logoutBtn = document.getElementById('logoutBtn');
const usernameDisplay = document.getElementById('username-display');
const loginError = document.getElementById('loginError');

// Navigation
const navLinks = document.querySelectorAll('.nav-link');
const viewSections = document.querySelectorAll('.view-section');

// Scraper form
const scraperForm = document.getElementById('scraperForm');
const triggerBtn = document.getElementById('triggerBtn');
const cancelBtn = document.getElementById('cancelBtn');
const progressSection = document.getElementById('progressSection');
const logOutput = document.getElementById('logOutput');
const storiesCount = document.getElementById('storiesCount');
const errorCount = document.getElementById('errorCount');
const elapsed = document.getElementById('elapsed');
const scraperStatus = document.getElementById('scraperStatus');
const scraperMessage = document.getElementById('scraperMessage');

// ===== Authentication =====

async function login(username, password) {
  try {
    const response = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });

    if (!response.ok) {
      const error = await response.json();
      showLoginError(error.detail || 'Login failed');
      return false;
    }

    currentUser = await response.json();
    showDashboard();
    return true;
  } catch (error) {
    showLoginError('Network error: ' + error.message);
    return false;
  }
}

function showLoginError(message) {
  loginError.textContent = message;
  loginError.classList.add('show');
}

async function logout() {
  try {
    await fetch(`${API_BASE}/auth/logout`, { method: 'POST' });
  } catch (error) {
    console.error('Logout error:', error);
  }
  currentUser = null;
  showLogin();
}

function showLogin() {
  loginPage.style.display = 'flex';
  dashboardPage.style.display = 'none';
  loginForm.reset();
  loginError.classList.remove('show');
}

function showDashboard() {
  loginPage.style.display = 'none';
  dashboardPage.style.display = 'flex';
  usernameDisplay.textContent = currentUser.username;
  switchView('scraper-control');
}

// ===== Navigation =====

function switchView(viewName) {
  // Hide all views
  viewSections.forEach(section => section.classList.remove('active'));

  // Show selected view
  const selectedView = document.getElementById(viewName);
  if (selectedView) {
    selectedView.classList.add('active');
  }

  // Update nav links
  navLinks.forEach(link => {
    if (link.dataset.view === viewName) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });
}

// ===== Scraper Control =====

async function triggerScraper(limit, storyTypes) {
  try {
    triggerBtn.disabled = true;
    triggerBtn.style.display = 'none';
    cancelBtn.style.display = 'inline-block';
    progressSection.style.display = 'block';
    logOutput.innerHTML = '';
    storiesCount.textContent = '0';
    errorCount.textContent = '0';
    elapsed.textContent = '0s';

    scraperStatus.textContent = 'Running';
    scraperStatus.className = 'status-badge running';
    scraperMessage.textContent = 'Scraper is running...';

    addLog('Sending trigger request...');

    // Trigger scraper
    const response = await fetch(`${API_BASE}/scraper/trigger`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ limit, story_types: storyTypes })
    });

    if (!response.ok) {
      const error = await response.json();
      addLog(`Error: ${error.detail}`);
      scraperStatus.textContent = 'Failed';
      scraperStatus.className = 'status-badge failed';
      triggerBtn.disabled = false;
      triggerBtn.style.display = 'inline-block';
      cancelBtn.style.display = 'none';
      return;
    }

    const result = await response.json();
    currentRunId = result.run_id;
    addLog(`Scraper run started (ID: ${currentRunId})`);
    addLog(`Limit: ${limit} stories per type`);
    addLog(`Story types: ${storyTypes.join(', ')}`);

    // Start elapsed timer
    startElapsedTimer();

    // Poll for status updates
    pollScraperStatus();

    // Connect to WebSocket for updates (optional, falls back to polling)
    connectWebSocket();

  } catch (error) {
    addLog(`Error: ${error.message}`);
    scraperStatus.textContent = 'Error';
    scraperStatus.className = 'status-badge failed';
    triggerBtn.disabled = false;
    triggerBtn.style.display = 'inline-block';
    cancelBtn.style.display = 'none';
  }
}

let pollInterval = null;

function pollScraperStatus() {
  if (pollInterval) clearInterval(pollInterval);

  pollInterval = setInterval(async () => {
    try {
      const response = await fetch(`${API_BASE}/scraper/status`);
      if (!response.ok) return;

      const data = await response.json();

      if (data.current_run) {
        const run = data.current_run;
        storiesCount.textContent = run.stories_processed || '0';
        errorCount.textContent = run.errors_count || '0';

        if (run.status === 'completed') {
          clearInterval(pollInterval);
          scraperStatus.textContent = 'Completed';
          scraperStatus.className = 'status-badge completed';
          scraperMessage.textContent = `Successfully processed ${run.stories_processed} stories`;
          triggerBtn.disabled = false;
          triggerBtn.style.display = 'inline-block';
          cancelBtn.style.display = 'none';
          addLog('Scraper completed successfully!');
        } else if (run.status === 'failed') {
          clearInterval(pollInterval);
          scraperStatus.textContent = 'Failed';
          scraperStatus.className = 'status-badge failed';
          scraperMessage.textContent = run.error_message || 'Scraper failed';
          triggerBtn.disabled = false;
          triggerBtn.style.display = 'inline-block';
          cancelBtn.style.display = 'none';
          addLog(`Scraper failed: ${run.error_message}`);
        }
      } else if (!data.is_running) {
        clearInterval(pollInterval);
        triggerBtn.disabled = false;
        triggerBtn.style.display = 'inline-block';
        cancelBtn.style.display = 'none';
      }
    } catch (error) {
      console.error('Poll error:', error);
    }
  }, 1000); // Poll every second
}

function connectWebSocket() {
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  const wsUrl = `${protocol}//${window.location.host}${API_BASE}/scraper/ws`;

  try {
    wsConnection = new WebSocket(wsUrl);

    wsConnection.onopen = () => {
      addLog('Connected to live updates');
    };

    wsConnection.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        if (data.type === 'log') {
          addLog(data.message);
        } else if (data.type === 'progress') {
          storiesCount.textContent = data.stories_processed || '0';
          errorCount.textContent = data.errors_count || '0';
        } else if (data.type === 'status') {
          if (data.status === 'completed') {
            clearInterval(pollInterval);
            scraperStatus.textContent = 'Completed';
            scraperStatus.className = 'status-badge completed';
            scraperMessage.textContent = `Successfully processed ${data.stories_processed} stories`;
            triggerBtn.disabled = false;
            triggerBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'none';
            wsConnection.close();
          } else if (data.status === 'failed') {
            clearInterval(pollInterval);
            scraperStatus.textContent = 'Failed';
            scraperStatus.className = 'status-badge failed';
            scraperMessage.textContent = data.error_message || 'Scraper failed';
            triggerBtn.disabled = false;
            triggerBtn.style.display = 'inline-block';
            cancelBtn.style.display = 'none';
            wsConnection.close();
          }
        }
      } catch (e) {
        console.error('Error parsing WebSocket message:', e);
      }
    };

    wsConnection.onerror = (error) => {
      console.warn('WebSocket error, using polling:', error);
      // Will fall back to polling
    };

    wsConnection.onclose = () => {
      console.log('WebSocket closed');
    };
  } catch (error) {
    console.warn('WebSocket unavailable, using polling:', error);
    // Polling is already started
  }
}

function addLog(message) {
  const line = document.createElement('div');
  line.className = 'log-line';
  line.textContent = message;
  logOutput.appendChild(line);
  logOutput.scrollTop = logOutput.scrollHeight;
}

let startTime = null;
let elapsedInterval = null;

function startElapsedTimer() {
  startTime = Date.now();
  if (elapsedInterval) clearInterval(elapsedInterval);

  elapsedInterval = setInterval(() => {
    const seconds = Math.floor((Date.now() - startTime) / 1000);
    elapsed.textContent = `${seconds}s`;
  }, 1000);
}

async function cancelScraper() {
  if (!currentRunId) return;

  try {
    const response = await fetch(`${API_BASE}/scraper/cancel`, {
      method: 'POST'
    });

    if (!response.ok) {
      const error = await response.json();
      addLog(`Error: ${error.detail}`);
      return;
    }

    addLog('Scraper cancellation requested...');
    cancelBtn.disabled = true;
  } catch (error) {
    addLog(`Error cancelling: ${error.message}`);
  }
}

// ===== Event Listeners =====

// Login form
loginForm.addEventListener('submit', async (e) => {
  e.preventDefault();
  const username = document.getElementById('username').value;
  const password = document.getElementById('password').value;

  const success = await login(username, password);
  if (!success) {
    document.getElementById('password').value = '';
  }
});

// Logout
logoutBtn.addEventListener('click', logout);

// Navigation
navLinks.forEach(link => {
  link.addEventListener('click', (e) => {
    e.preventDefault();
    switchView(link.dataset.view);
  });
});

// Scraper form
scraperForm.addEventListener('submit', (e) => {
  e.preventDefault();

  const limit = parseInt(document.getElementById('hnLimit').value);
  const storyTypes = Array.from(document.querySelectorAll('input[name="storyType"]:checked')).map(
    input => input.value
  );

  if (storyTypes.length === 0) {
    alert('Please select at least one story type');
    return;
  }

  triggerScraper(limit, storyTypes);
});

// Cancel button
cancelBtn.addEventListener('click', cancelScraper);

// ===== Initialization =====

async function checkAuth() {
  try {
    const response = await fetch(`${API_BASE}/auth/me`);
    if (response.ok) {
      currentUser = await response.json();
      showDashboard();
    } else {
      showLogin();
    }
  } catch (error) {
    showLogin();
  }
}

// Check authentication on page load
window.addEventListener('load', checkAuth);

// Cleanup on unload
window.addEventListener('beforeunload', () => {
  if (wsConnection) {
    wsConnection.close();
  }
  if (elapsedInterval) {
    clearInterval(elapsedInterval);
  }
  if (pollInterval) {
    clearInterval(pollInterval);
  }
});
