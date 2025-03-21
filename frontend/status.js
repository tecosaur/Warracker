// DOM Elements
const settingsBtn = document.getElementById('settingsBtn');
const settingsMenu = document.getElementById('settingsMenu');
const darkModeToggle = document.getElementById('darkModeToggle');
const loadingIndicator = document.getElementById('loadingIndicator');
const errorContainer = document.getElementById('errorContainer');
const errorMessage = document.getElementById('errorMessage');
const errorDetails = document.getElementById('errorDetails');
const dashboardContent = document.getElementById('dashboardContent');
const refreshDashboardBtn = document.getElementById('refreshDashboardBtn');
const searchWarranties = document.getElementById('searchWarranties');
const statusFilter = document.getElementById('statusFilter');
const sortableHeaders = document.querySelectorAll('.sortable');
const exportBtn = document.getElementById('exportBtn');

// Configuration
const API_BASE_URL = '/api/statistics'; // Base URL for statistics endpoint
const API_URL = window.location.origin + API_BASE_URL; // Full URL for statistics endpoint
let EXPIRING_SOON_DAYS = 30; // Default value, will be updated from user preferences

// Global variables for sorting and filtering
let currentSort = { column: 'expiration', direction: 'asc' };
let allWarranties = []; // Store all warranties for filtering/sorting

// Chart instances
window.statusChart = null;
window.timelineChart = null;

// Theme Management
function setTheme(isDark) {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    localStorage.setItem('darkMode', isDark);
    darkModeToggle.checked = isDark;
}

// Initialize theme based on user preference or system preference
function initializeTheme() {
    const savedTheme = localStorage.getItem('darkMode');
    
    if (savedTheme !== null) {
        // Use saved preference
        setTheme(savedTheme === 'true');
    } else {
        // Check for system preference
        const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
        setTheme(prefersDarkMode);
    }
}

// Initialize theme when page loads
initializeTheme();

// Initialize settings button
document.addEventListener('DOMContentLoaded', () => {
    // Ensure auth state is checked
    if (window.auth && window.auth.checkAuthState) {
        window.auth.checkAuthState();
    }
    
    // Ensure settings button works
    if (settingsBtn && settingsMenu) {
        console.log('Status page: Settings button found, adding event listener');
        settingsBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            settingsMenu.classList.toggle('active');
            console.log('Status page: Settings button clicked, menu toggled');
        });
        
        // Close settings menu when clicking outside
        document.addEventListener('click', function(e) {
            if (settingsMenu.classList.contains('active') && 
                !settingsMenu.contains(e.target) && 
                !settingsBtn.contains(e.target)) {
                settingsMenu.classList.remove('active');
            }
        });
    } else {
        console.error('Status page: Settings button or menu not found');
    }
    
    // ... existing code ...
});

// Dark mode toggle
darkModeToggle.addEventListener('change', (e) => {
    setTheme(e.target.checked);
});

// Refresh dashboard button
refreshDashboardBtn.addEventListener('click', () => {
    refreshDashboard();
});

// Search input event listener
searchWarranties.addEventListener('input', () => {
    filterAndSortWarranties();
});

// Status filter change event listener
statusFilter.addEventListener('change', () => {
    filterAndSortWarranties();
});

// Add click event listeners to sortable headers
sortableHeaders.forEach(header => {
    header.addEventListener('click', () => {
        const column = header.getAttribute('data-sort');
        
        // Toggle sort direction if clicking the same column
        if (currentSort.column === column) {
            currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
        } else {
            currentSort.column = column;
            currentSort.direction = 'asc';
        }
        
        // Update header classes
        updateSortHeaderClasses();
        
        // Re-sort the table
        filterAndSortWarranties();
    });
});

// Update the sort header classes
function updateSortHeaderClasses() {
    sortableHeaders.forEach(header => {
        const column = header.getAttribute('data-sort');
        header.classList.remove('sort-asc', 'sort-desc');
        
        if (column === currentSort.column) {
            header.classList.add(currentSort.direction === 'asc' ? 'sort-asc' : 'sort-desc');
        }
    });
}

// Show loading indicator
function showLoading() {
    loadingIndicator.classList.add('active');
    dashboardContent.style.opacity = '0.5';
}

// Hide loading indicator
function hideLoading() {
    loadingIndicator.classList.remove('active');
    dashboardContent.style.opacity = '1';
}

// Show error message
function showError(message, details = '') {
    errorMessage.textContent = message;
    errorDetails.textContent = details;
    errorContainer.style.display = 'block';
    dashboardContent.style.display = 'none';
}

// Hide error message
function hideError() {
    errorContainer.style.display = 'none';
    dashboardContent.style.display = 'block';
}

// Fetch statistics from API
async function fetchStatistics() {
    try {
        console.log('Checking authentication status...');
        console.log('window.auth exists:', !!window.auth);
        
        // Check if auth is available and user is authenticated
        if (!window.auth) {
            console.error('Auth object not available. Make sure auth.js is loaded before status.js');
            throw new Error('Authentication system not available. Please refresh the page.');
        }
        
        console.log('User is authenticated:', window.auth.isAuthenticated());
        if (!window.auth.isAuthenticated()) {
            throw new Error('Authentication required. Please log in to view statistics.');
        }
        
        // Get the auth token
        const token = window.auth.getToken();
        console.log('Auth token available:', !!token);
        if (!token) {
            throw new Error('Authentication token not available. Please log in again.');
        }
        
        // Create request with auth header
        const options = {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        };
        
        console.log('Fetching statistics from:', API_URL);
        const response = await fetch(API_URL, options);
        
        if (!response.ok) {
            const errorText = await response.text();
            throw new Error(`Failed to fetch statistics: ${response.status} ${errorText}`);
        }
        
        // Parse JSON only once
        const data = await response.json();
        return data;
    } catch (error) {
        console.error('Error fetching statistics:', error);
        throw error;
    }
}

// Show a toast notification
function showToast(message, type = 'info') {
    const toastContainer = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        ${message}
        <button class="toast-close">&times;</button>
    `;
    
    // Add close event
    toast.querySelector('.toast-close').addEventListener('click', () => {
        toast.remove();
    });
    
    toastContainer.appendChild(toast);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        if (toast.parentElement) {
            toast.remove();
        }
    }, 3000);
}

// Update the summary counts
function updateSummaryCounts(stats) {
    document.getElementById('activeCount').textContent = stats.active;
    document.getElementById('expiringCount').textContent = stats.expiring_soon;
    document.getElementById('expiredCount').textContent = stats.expired;
    document.getElementById('totalCount').textContent = stats.total;
}

// Create the status distribution chart
function createStatusChart(stats) {
    const ctx = document.getElementById('statusChart').getContext('2d');
    
    // Ensure we have valid stats
    if (!stats || typeof stats !== 'object') {
        console.error('Invalid stats data:', stats);
        stats = { active: 0, expiring_soon: 0, expired: 0, total: 0 };
    }
    
    // Set default values for missing properties
    const active = stats.active || 0;
    const expiringSoon = stats.expiring_soon || 0;
    const expired = stats.expired || 0;
    
    // Calculate truly active (not expiring soon)
    const trulyActive = Math.max(0, active - expiringSoon);
    
    // Destroy existing chart if it exists
    if (window.statusChart) {
        window.statusChart.destroy();
    }
    
    window.statusChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Active', 'Expiring Soon', 'Expired'],
            datasets: [{
                data: [
                    trulyActive,
                    expiringSoon,
                    expired
                ],
                backgroundColor: [
                    '#4CAF50', // Green for active
                    '#FF9800', // Orange for expiring soon
                    '#F44336'  // Red for expired
                ],
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    position: 'bottom'
                }
            }
        }
    });
}

// Create the timeline chart
function createTimelineChart(timeline) {
    const ctx = document.getElementById('timelineChart').getContext('2d');
    
    // Ensure timeline is an array
    if (!Array.isArray(timeline)) {
        console.error('Timeline data is not an array:', timeline);
        timeline = [];
    }
    
    // Format labels as "Month Year"
    const formattedLabels = timeline.map(item => {
        try {
            // Handle different possible formats
            let year, month;
            
            if (item.year !== undefined && item.month !== undefined) {
                year = item.year;
                month = item.month - 1; // JavaScript months are 0-indexed
            } else if (item.date) {
                const date = new Date(item.date);
                year = date.getFullYear();
                month = date.getMonth();
            } else {
                // Default to current month if data format is unknown
                const date = new Date();
                year = date.getFullYear();
                month = date.getMonth();
            }
            
            const date = new Date(year, month, 1);
            return date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });
        } catch (error) {
            console.error('Error formatting timeline label:', error);
            return 'Unknown';
        }
    });
    
    // Get count values, defaulting to 0 if not present
    const counts = timeline.map(item => {
        return item.count !== undefined ? item.count : 0;
    });
    
    // If we have no data, create a default dataset
    if (timeline.length === 0) {
        const currentDate = new Date();
        const currentYear = currentDate.getFullYear();
        const currentMonth = currentDate.getMonth();
        
        // Create labels for the last 3 months
        for (let i = 2; i >= 0; i--) {
            const date = new Date(currentYear, currentMonth - i, 1);
            formattedLabels.push(date.toLocaleDateString(undefined, { month: 'short', year: 'numeric' }));
            counts.push(0);
        }
    }
    
    // Destroy existing chart if it exists
    if (window.timelineChart) {
        window.timelineChart.destroy();
    }
    
    window.timelineChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: formattedLabels,
            datasets: [{
                label: 'Warranties Expiring',
                data: counts,
                backgroundColor: '#3498db',
                borderColor: '#2980b9',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        precision: 0 // Only show integer values
                    }
                }
            }
        }
    });
}

// Update the recent expirations table
function updateRecentExpirations(recentWarranties) {
    // Ensure we have an array
    if (!Array.isArray(recentWarranties)) {
        console.error('Recent warranties data is not an array:', recentWarranties);
        recentWarranties = [];
    }
    
    // Normalize the data format
    const normalizedWarranties = recentWarranties.map(warranty => {
        // Create a standardized warranty object
        return {
            id: warranty.id || Math.random().toString(36).substr(2, 9), // Generate ID if not present
            product_name: warranty.product_name || warranty.name || 'Unknown Product',
            purchase_date: warranty.purchase_date || new Date().toISOString().split('T')[0],
            expiration_date: warranty.expiration_date || new Date().toISOString().split('T')[0],
            invoice_path: warranty.invoice_path || null
        };
    });
    
    // Store all warranties for filtering/sorting
    allWarranties = normalizedWarranties;
    
    // Apply initial filtering and sorting
    filterAndSortWarranties();
}

// Filter and sort warranties based on current settings
function filterAndSortWarranties() {
    const searchTerm = searchWarranties.value.toLowerCase();
    const statusValue = statusFilter.value;
    const tableBody = document.getElementById('recentExpirationsBody');
    
    // Clear the table
    tableBody.innerHTML = '';
    
    if (!allWarranties || allWarranties.length === 0) {
        // Create a full-width, centered overlay message instead of using table structure
        const tableContainer = document.querySelector('.table-responsive');
        const emptyMessage = document.createElement('div');
        
        // Apply styles directly to ensure centering
        emptyMessage.style.position = 'absolute';
        emptyMessage.style.top = '0';
        emptyMessage.style.left = '0';
        emptyMessage.style.width = '100%';
        emptyMessage.style.height = '300px';
        emptyMessage.style.display = 'flex';
        emptyMessage.style.justifyContent = 'center';
        emptyMessage.style.alignItems = 'center';
        emptyMessage.style.fontSize = '1.2em';
        emptyMessage.style.color = 'var(--text-color)';
        emptyMessage.style.backgroundColor = 'var(--card-bg)';
        emptyMessage.style.zIndex = '1'; // Ensure it's on top
        
        // Add the message text
        emptyMessage.textContent = 'No recently expired or expiring warranties.';
        
        // Make sure table container has position relative
        tableContainer.style.position = 'relative';
        
        // Clear any existing error messages
        const existingMessages = tableContainer.querySelectorAll('.empty-message-overlay');
        existingMessages.forEach(msg => msg.remove());
        
        // Add class for easier removal later
        emptyMessage.classList.add('empty-message-overlay');
        
        // Add to the table container
        tableContainer.appendChild(emptyMessage);
        
        // Add a blank row to maintain table structure
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" style="height: 300px;"></td>';
        tableBody.appendChild(row);
        
        return;
    }
    
    const today = new Date();
    
    // Filter warranties
    let filteredWarranties = allWarranties.filter(warranty => {
        // Skip warranties without proper dates
        if (!warranty.expiration_date) return false;
        
        // Apply search filter
        const productName = (warranty.product_name || '').toLowerCase();
        const matchesSearch = searchTerm === '' || productName.includes(searchTerm);
        
        // Apply status filter
        if (statusValue === 'all') {
            return matchesSearch;
        }
        
        const expirationDate = new Date(warranty.expiration_date);
        
        if (statusValue === 'expired') {
            return expirationDate <= today && matchesSearch;
        } else if (statusValue === 'expiring') {
            const timeDiff = expirationDate - today;
            const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
            return expirationDate > today && daysDiff <= EXPIRING_SOON_DAYS && matchesSearch;
        } else if (statusValue === 'active') {
            const timeDiff = expirationDate - today;
            const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
            return expirationDate > today && daysDiff > EXPIRING_SOON_DAYS && matchesSearch;
        }
        
        return matchesSearch;
    });
    
    // Sort warranties
    filteredWarranties.sort((a, b) => {
        let valueA, valueB;
        
        switch (currentSort.column) {
            case 'product':
                valueA = a.product_name || '';
                valueB = b.product_name || '';
                break;
            case 'purchase':
                valueA = new Date(a.purchase_date || 0);
                valueB = new Date(b.purchase_date || 0);
                break;
            case 'expiration':
                valueA = new Date(a.expiration_date || 0);
                valueB = new Date(b.expiration_date || 0);
                break;
            case 'status':
                // Sort by status priority: active, expiring, expired
                const statusA = getStatusPriority(a.expiration_date, today);
                const statusB = getStatusPriority(b.expiration_date, today);
                valueA = statusA;
                valueB = statusB;
                break;
            default:
                valueA = new Date(a.expiration_date || 0);
                valueB = new Date(b.expiration_date || 0);
        }
        
        // Compare values based on sort direction
        if (currentSort.direction === 'asc') {
            return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
        } else {
            return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
        }
    });
    
    // Render filtered and sorted warranties
    if (filteredWarranties.length === 0) {
        // Create a full-width, centered overlay message instead of using table structure
        const tableContainer = document.querySelector('.table-responsive');
        const emptyMessage = document.createElement('div');
        
        // Apply styles directly to ensure centering
        emptyMessage.style.position = 'absolute';
        emptyMessage.style.top = '0';
        emptyMessage.style.left = '0';
        emptyMessage.style.width = '100%';
        emptyMessage.style.height = '300px';
        emptyMessage.style.display = 'flex';
        emptyMessage.style.justifyContent = 'center';
        emptyMessage.style.alignItems = 'center';
        emptyMessage.style.fontSize = '1.2em';
        emptyMessage.style.color = 'var(--text-color)';
        emptyMessage.style.backgroundColor = 'var(--card-bg)';
        emptyMessage.style.zIndex = '1'; // Ensure it's on top
        
        // Add the message text
        emptyMessage.textContent = 'No warranties match your search criteria.';
        
        // Make sure table container has position relative
        tableContainer.style.position = 'relative';
        
        // Clear any existing error messages
        const existingMessages = tableContainer.querySelectorAll('.empty-message-overlay');
        existingMessages.forEach(msg => msg.remove());
        
        // Add class for easier removal later
        emptyMessage.classList.add('empty-message-overlay');
        
        // Add to the table container
        tableContainer.appendChild(emptyMessage);
        
        // Add a blank row to maintain table structure
        const row = document.createElement('tr');
        row.innerHTML = '<td colspan="5" style="height: 300px;"></td>';
        tableBody.appendChild(row);
        
        return;
    }
    
    filteredWarranties.forEach(warranty => {
        const row = document.createElement('tr');
        
        // Make sure we have valid data to work with
        if (!warranty.expiration_date) return;
        
        // Determine status
        const expirationDate = new Date(warranty.expiration_date);
        let status = 'active';
        
        if (expirationDate <= today) {
            status = 'expired';
        } else {
            const timeDiff = expirationDate - today;
            const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
            
            if (daysDiff <= EXPIRING_SOON_DAYS) {
                status = 'expiring';
            }
        }
        
        row.className = `status-${status}`;
        
        // Format dates
        const purchaseDate = warranty.purchase_date ? new Date(warranty.purchase_date).toLocaleDateString() : 'N/A';
        const formattedExpirationDate = expirationDate.toLocaleDateString();
        
        // Status display
        let statusText = status === 'expired' ? 'Expired' : status === 'expiring' ? 'Expiring Soon' : 'Active';
        let statusClass = `status-${status}`;
        
        // Create table cells with proper structure
        row.innerHTML = `
            <td>${warranty.product_name || 'Unknown Product'}</td>
            <td>${purchaseDate}</td>
            <td>${formattedExpirationDate}</td>
            <td><span class="${statusClass}">${statusText}</span></td>
            <td>
                <a href="index.html?edit=${warranty.id}" class="action-btn edit-btn" title="Edit">
                    <i class="fas fa-edit"></i>
                </a>
                <a href="#" onclick="window.openSecureFile ? openSecureFile('${warranty.invoice_path || ''}') : alert('File viewer not available'); return false;" class="action-btn view-btn" title="View Invoice" ${!warranty.invoice_path ? 'style="display: none;"' : ''}>
                    <i class="fas fa-file-alt"></i>
                </a>
            </td>
        `;
        
        tableBody.appendChild(row);
    });
}

// Get status priority for sorting (1: active, 2: expiring, 3: expired)
function getStatusPriority(expirationDateStr, today) {
    const expirationDate = new Date(expirationDateStr);
    
    if (expirationDate <= today) {
        return 3; // Expired
    } else {
        const timeDiff = expirationDate - today;
        const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
        
        if (daysDiff <= EXPIRING_SOON_DAYS) {
            return 2; // Expiring soon
        } else {
            return 1; // Active
        }
    }
}

// Refresh the dashboard
function refreshDashboard() {
    // Add loading animation to refresh button
    refreshDashboardBtn.classList.add('loading');
    
    // Initialize the dashboard
    initDashboard().finally(() => {
        // Remove loading animation
        refreshDashboardBtn.classList.remove('loading');
    });
}

// Initialize the dashboard
async function initDashboard() {
    console.log('Initializing dashboard');
    
    try {
        // Show loading indicator
        showLoading();
        
        // Load user preferences
        await loadUserPreferences();
        
        // Check authentication
        const token = localStorage.getItem('auth_token');
        if (!token) {
            window.location.href = 'login.html';
            return;
        }
        
        const data = await fetchStatistics();
        console.log('API Response:', data); // Log the actual response for debugging
        
        // Handle different possible API response structures
        let summary, timeline, recentWarranties;
        
        // Check if data is directly the summary object
        if (data && typeof data === 'object' && 'active' in data && 'expired' in data) {
            summary = data;
            timeline = data.timeline || [];
            recentWarranties = data.recent_warranties || [];
        } 
        // Check if data has summary as a property
        else if (data && typeof data === 'object' && data.summary && typeof data.summary === 'object') {
            summary = data.summary;
            timeline = data.timeline || [];
            recentWarranties = data.recent_warranties || [];
        } 
        // If we can't find a valid structure, throw an error
        else {
            console.error('Unexpected API response structure:', data);
            throw new Error('Invalid data structure received from API. Expected summary data with active and expired counts.');
        }
        
        // Ensure summary has all required properties
        if (!('active' in summary) || !('expired' in summary)) {
            throw new Error('API response missing required summary fields (active, expired)');
        }
        
        // Set default values for any missing properties
        summary.expiring_soon = summary.expiring_soon || 0;
        summary.total = summary.total || (summary.active + summary.expired);
        
        // Update summary counts
        updateSummaryCounts(summary);
        
        // Create charts
        createStatusChart(summary);
        createTimelineChart(timeline);
        
        // Update recent expirations table with the initial data
        updateRecentExpirations(recentWarranties);
        
        // Fetch all warranties for better filtering
        try {
            const allWarrantiesResponse = await fetch('/api/warranties', {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json'
                }
            });
            
            if (allWarrantiesResponse.ok) {
                const allWarrantiesData = await allWarrantiesResponse.json();
                // Store all warranties for filtering
                allWarranties = allWarrantiesData;
                console.log('Fetched all warranties for filtering:', allWarranties.length);
            } else {
                // If we can't get all warranties, fall back to the recent ones
                allWarranties = recentWarranties;
                console.warn('Could not fetch all warranties, falling back to recent warranties');
            }
        } catch (error) {
            console.error('Error fetching all warranties:', error);
            // Fall back to recent warranties on error
            allWarranties = recentWarranties;
        }
        
        // Set up event listeners for filtering and sorting
        setupEventListeners();
        
        hideLoading();
    } catch (error) {
        console.error('Error initializing dashboard:', error);
        
        // Check if it's an authentication error
        if (error.message.includes('Authentication required') || 
            error.message.includes('Authentication token') || 
            error.message.includes('401')) {
            
            showError('Authentication Required', 
                'Please <a href="login.html">log in</a> to view your warranty statistics.');
        } else {
            showError('Error Loading Dashboard', 
                'There was a problem loading the warranty statistics. Please try refreshing the page.');
        }
    } finally {
        hideLoading();
    }
}

// Initialize the dashboard when the page loads
document.addEventListener('DOMContentLoaded', initDashboard);

// Export button event listener
exportBtn.addEventListener('click', () => {
    exportWarrantyData();
});

// Export warranty data as CSV
function exportWarrantyData() {
    // Get filtered and sorted warranties
    const searchTerm = searchWarranties.value.toLowerCase();
    const statusValue = statusFilter.value;
    const today = new Date();
    
    // Filter warranties
    let filteredWarranties = allWarranties.filter(warranty => {
        // Apply search filter
        const productName = warranty.product_name.toLowerCase();
        const matchesSearch = searchTerm === '' || productName.includes(searchTerm);
        
        // Apply status filter
        if (statusValue === 'all') {
            return matchesSearch;
        }
        
        const expirationDate = new Date(warranty.expiration_date);
        
        if (statusValue === 'expired') {
            return expirationDate <= today && matchesSearch;
        } else if (statusValue === 'expiring') {
            const timeDiff = expirationDate - today;
            const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
            return expirationDate > today && daysDiff <= EXPIRING_SOON_DAYS && matchesSearch;
        } else if (statusValue === 'active') {
            const timeDiff = expirationDate - today;
            const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
            return expirationDate > today && daysDiff > EXPIRING_SOON_DAYS && matchesSearch;
        }
        
        return matchesSearch;
    });
    
    // Sort warranties based on current sort settings
    filteredWarranties.sort((a, b) => {
        let valueA, valueB;
        
        switch (currentSort.column) {
            case 'product':
                valueA = a.product_name;
                valueB = b.product_name;
                break;
            case 'purchase':
                valueA = new Date(a.purchase_date);
                valueB = new Date(b.purchase_date);
                break;
            case 'expiration':
                valueA = new Date(a.expiration_date);
                valueB = new Date(b.expiration_date);
                break;
            case 'status':
                // Sort by status priority: active, expiring, expired
                const statusA = getStatusPriority(a.expiration_date, today);
                const statusB = getStatusPriority(b.expiration_date, today);
                valueA = statusA;
                valueB = statusB;
                break;
            default:
                valueA = new Date(a.expiration_date);
                valueB = new Date(b.expiration_date);
        }
        
        // Compare values based on sort direction
        if (currentSort.direction === 'asc') {
            return valueA > valueB ? 1 : valueA < valueB ? -1 : 0;
        } else {
            return valueA < valueB ? 1 : valueA > valueB ? -1 : 0;
        }
    });
    
    // If no warranties to export
    if (filteredWarranties.length === 0) {
        showToast('No data to export', 'warning');
        return;
    }
    
    // Create CSV content
    let csvContent = 'Product,Purchase Date,Expiration Date,Status\n';
    
    filteredWarranties.forEach(warranty => {
        const purchaseDate = new Date(warranty.purchase_date).toLocaleDateString();
        const expirationDate = new Date(warranty.expiration_date).toLocaleDateString();
        
        // Determine status
        const today = new Date();
        const expDate = new Date(warranty.expiration_date);
        let status = 'Active';
        
        if (expDate <= today) {
            status = 'Expired';
        } else {
            const timeDiff = expDate - today;
            const daysDiff = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
            
            if (daysDiff <= EXPIRING_SOON_DAYS) {
                status = 'Expiring Soon';
            }
        }
        
        // Escape commas in product name
        const escapedProductName = warranty.product_name.includes(',') 
            ? `"${warranty.product_name}"` 
            : warranty.product_name;
        
        csvContent += `${escapedProductName},${purchaseDate},${expirationDate},${status}\n`;
    });
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    
    // Set link properties
    link.setAttribute('href', url);
    link.setAttribute('download', 'warranty_data.csv');
    link.style.visibility = 'hidden';
    
    // Add to document, click and remove
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    showToast('Data exported successfully', 'success');
}

// Set up event listeners for filtering and sorting
function setupEventListeners() {
    // Refresh button
    if (refreshDashboardBtn) {
        refreshDashboardBtn.addEventListener('click', refreshDashboard);
    }
    
    // Search input
    if (searchWarranties) {
        searchWarranties.addEventListener('input', filterAndSortWarranties);
    }
    
    // Status filter
    if (statusFilter) {
        statusFilter.addEventListener('change', filterAndSortWarranties);
    }
    
    // Sortable headers
    if (sortableHeaders) {
        sortableHeaders.forEach(header => {
            header.addEventListener('click', () => {
                const column = header.getAttribute('data-sort');
                
                // Toggle direction if same column, otherwise default to ascending
                if (currentSort.column === column) {
                    currentSort.direction = currentSort.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    currentSort.column = column;
                    currentSort.direction = 'asc';
                }
                
                // Update header classes to show sort direction
                updateSortHeaderClasses();
                
                // Apply the new sort
                filterAndSortWarranties();
            });
        });
    }
    
    // Export button
    if (exportBtn) {
        exportBtn.addEventListener('click', exportWarrantyData);
    }
    
    // Dark mode toggle
    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', (e) => {
            setTheme(e.target.checked);
            
            // Redraw charts with new theme colors if they exist
            if (window.statusChart) {
                createStatusChart({
                    active: parseInt(document.getElementById('activeCount').textContent) || 0,
                    expiring_soon: parseInt(document.getElementById('expiringCount').textContent) || 0,
                    expired: parseInt(document.getElementById('expiredCount').textContent) || 0
                });
            }
            
            if (window.timelineChart && allWarranties.length > 0) {
                createTimelineChart(extractTimelineData(allWarranties));
            }
        });
    }
}

// Helper function to extract timeline data from warranties
function extractTimelineData(warranties) {
    // Create a map to store counts by month and year
    const timelineMap = new Map();
    
    // Get current date for reference
    const today = new Date();
    
    // Process each warranty
    warranties.forEach(warranty => {
        if (warranty.expiration_date) {
            const expDate = new Date(warranty.expiration_date);
            const month = expDate.getMonth() + 1; // 1-12
            const year = expDate.getFullYear();
            
            // Create a key for this month/year
            const key = `${year}-${month}`;
            
            // Increment the count for this month/year
            if (timelineMap.has(key)) {
                timelineMap.set(key, timelineMap.get(key) + 1);
            } else {
                timelineMap.set(key, 1);
            }
        }
    });
    
    // Convert the map to an array of objects
    const timeline = Array.from(timelineMap.entries()).map(([key, count]) => {
        const [year, month] = key.split('-').map(Number);
        return { year, month, count };
    });
    
    // Sort by date
    timeline.sort((a, b) => {
        if (a.year !== b.year) return a.year - b.year;
        return a.month - b.month;
    });
    
    return timeline;
}

// Function to load user preferences
async function loadUserPreferences() {
    try {
        // Get the auth token
        const token = localStorage.getItem('auth_token');
        if (!token) return;
        
        // Get preferences from API
        const response = await fetch('/api/auth/preferences', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data && data.expiring_soon_days) {
                EXPIRING_SOON_DAYS = data.expiring_soon_days;
                console.log('Loaded expiring soon days from preferences:', EXPIRING_SOON_DAYS);
            }
        }
    } catch (error) {
        console.error('Error loading user preferences:', error);
    }
} 