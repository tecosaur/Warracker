// DOM Elements
const warrantyForm = document.getElementById('warrantyForm');
const settingsBtn = document.getElementById('settingsBtn');
const settingsMenu = document.getElementById('settingsMenu');
const darkModeToggle = document.getElementById('darkModeToggle');
const warrantiesList = document.getElementById('warrantiesList');
const refreshBtn = document.getElementById('refreshBtn');
const searchInput = document.getElementById('searchWarranties');
const statusFilter = document.getElementById('statusFilter');
const sortBySelect = document.getElementById('sortBy');
const exportBtn = document.getElementById('exportBtn');
const gridViewBtn = document.getElementById('gridViewBtn');
const listViewBtn = document.getElementById('listViewBtn');
const tableViewBtn = document.getElementById('tableViewBtn');
const tableViewHeader = document.querySelector('.table-view-header');
const fileInput = document.getElementById('invoice');
const fileName = document.getElementById('fileName');
const manualInput = document.getElementById('manual');
const manualFileName = document.getElementById('manualFileName');
const editModal = document.getElementById('editModal');
const deleteModal = document.getElementById('deleteModal');
const editWarrantyForm = document.getElementById('editWarrantyForm');
const saveWarrantyBtn = document.getElementById('saveWarrantyBtn');
const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
const loadingContainer = document.getElementById('loadingContainer');
const toastContainer = document.getElementById('toastContainer');

/**
 * Get current user type (admin or user)
 * @returns {string} 'admin' or 'user'
 */
function getUserType() {
    try {
        const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
        return userInfo.is_admin === true ? 'admin' : 'user';
    } catch (e) {
        console.error('Error determining user type:', e);
        return 'user'; // Default to user if we can't determine
    }
}

/**
 * Get the appropriate localStorage key prefix based on user type
 * @returns {string} The prefix to use for localStorage keys
 */
function getPreferenceKeyPrefix() {
    return getUserType() === 'admin' ? 'admin_' : 'user_';
}

// Theme Management
function setTheme(isDark) {
    // Get the appropriate key prefix based on user type
    const prefix = getPreferenceKeyPrefix();
    console.log(`Setting theme with prefix: ${prefix}`);
    
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    
    // Update darkMode settings
    localStorage.setItem(`${prefix}darkMode`, isDark);
    localStorage.setItem('darkMode', isDark); // Keep for backward compatibility
    
    // Update DOM
    if (isDark) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    // Set toggle state
    if (darkModeToggle) {
        darkModeToggle.checked = isDark;
    }
    
    // Also update preferences in localStorage for consistency
    try {
        let userPrefs = {};
        const storedPrefs = localStorage.getItem(`${prefix}preferences`);
        if (storedPrefs) {
            userPrefs = JSON.parse(storedPrefs);
        }
        userPrefs.theme = isDark ? 'dark' : 'light';
        localStorage.setItem(`${prefix}preferences`, JSON.stringify(userPrefs));
    } catch (e) {
        console.error(`Error updating theme in ${prefix}preferences:`, e);
    }
}

// Initialize theme based on user preference or system preference
function initializeTheme() {
    // Get the appropriate key prefix based on user type
    const prefix = getPreferenceKeyPrefix();
    console.log(`Initializing theme with prefix: ${prefix}`);
    
    // First check user-specific setting
    const userDarkMode = localStorage.getItem(`${prefix}darkMode`);
    if (userDarkMode !== null) {
        console.log(`Found user-specific dark mode setting: ${userDarkMode}`);
        setTheme(userDarkMode === 'true');
        return;
    }
    
    // Then check global setting for backward compatibility
    const globalDarkMode = localStorage.getItem('darkMode');
    if (globalDarkMode !== null) {
        console.log(`Found global dark mode setting: ${globalDarkMode}`);
        setTheme(globalDarkMode === 'true');
        return;
    }
    
    // Check for system preference if no stored preference
    const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    console.log(`No saved preference, using system preference: ${prefersDarkMode}`);
    setTheme(prefersDarkMode);
}

// Initialize theme when page loads
initializeTheme();

// Variables
let warranties = [];
let currentWarrantyId = null;
let currentFilters = {
    search: '',
    status: 'all',
    sort: 'expiration'
};
let currentView = 'grid'; // Default view
let expiringSoonDays = 30; // Default value, will be updated from user preferences

// API URL
const API_URL = '/api/warranties';

// Form tab navigation variables
const formTabs = Array.from(document.querySelectorAll('.form-tab'));
const tabContents = Array.from(document.querySelectorAll('.tab-content'));
let currentTabIndex = 0;

// Initialize form tabs
function initFormTabs() {
    console.log('Initializing form tabs...');
    
    // Hide the submit button initially
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.style.display = 'none';
    }
    
    // Show/hide navigation buttons based on current tab
    updateNavigationButtons();
    
    // Remove any existing event listeners before adding new ones
    const nextTabButton = document.querySelector('.next-tab');
    const prevTabButton = document.querySelector('.prev-tab');
    
    // Clone and replace the buttons to remove any existing event listeners
    if (nextTabButton && prevTabButton) {
        const nextTabClone = nextTabButton.cloneNode(true);
        const prevTabClone = prevTabButton.cloneNode(true);
        
        nextTabButton.parentNode.replaceChild(nextTabClone, nextTabButton);
        prevTabButton.parentNode.replaceChild(prevTabClone, prevTabButton);
        
        // Add event listeners for tab navigation
        document.querySelector('.next-tab').addEventListener('click', () => {
            console.log('Next button clicked, current tab:', currentTabIndex);
            if (validateTab(currentTabIndex)) {
                switchToTab(currentTabIndex + 1);
            } else {
                showValidationErrors(currentTabIndex);
            }
        });
        
        document.querySelector('.prev-tab').addEventListener('click', () => {
            console.log('Previous button clicked, current tab:', currentTabIndex);
            switchToTab(currentTabIndex - 1);
        });
    }
    
    // Add click event for tab headers
    formTabs.forEach((tab, index) => {
        tab.addEventListener('click', () => {
            // Only allow clicking on previous tabs or current tab
            if (index <= currentTabIndex) {
                switchToTab(index);
            }
        });
    });
}

// Switch to a specific tab
function switchToTab(index) {
    console.log(`Switching to tab ${index} from tab ${currentTabIndex}`);
    
    // Ensure index is within bounds
    if (index < 0 || index >= formTabs.length) {
        console.log(`Invalid tab index: ${index}, not switching`);
        return;
    }
    
    // Update active tab
    formTabs.forEach(tab => tab.classList.remove('active'));
    tabContents.forEach(content => content.classList.remove('active'));
    
    formTabs[index].classList.add('active');
    tabContents[index].classList.add('active');
    
    // Update current tab index
    currentTabIndex = index;
    
    // Update progress indicator
    document.querySelector('.form-tabs').setAttribute('data-step', currentTabIndex);
    
    // Update completed tabs
    updateCompletedTabs();
    
    // Update navigation buttons
    updateNavigationButtons();
    
    // Update summary if on summary tab
    if (index === formTabs.length - 1) {
        updateSummary();
    }
}

// Update navigation buttons based on current tab
function updateNavigationButtons() {
    const prevButton = document.querySelector('.prev-tab');
    const nextButton = document.querySelector('.next-tab');
    const submitButton = document.querySelector('button[type="submit"]');
    
    // Hide/show previous button
    prevButton.style.display = currentTabIndex === 0 ? 'none' : 'block';
    
    // Hide/show next button and submit button
    if (currentTabIndex === formTabs.length - 1) {
        nextButton.style.display = 'none';
        submitButton.style.display = 'block';
    } else {
        nextButton.style.display = 'block';
        submitButton.style.display = 'none';
    }
}

// Update completed tabs
function updateCompletedTabs() {
    formTabs.forEach((tab, index) => {
        if (index < currentTabIndex) {
            tab.classList.add('completed');
        } else {
            tab.classList.remove('completed');
        }
    });
}

// Validate a specific tab
function validateTab(tabIndex) {
    const tabContent = tabContents[tabIndex];
    const requiredInputs = tabContent.querySelectorAll('input[required]');
    
    // If there are no required inputs in this tab, it's automatically valid
    if (requiredInputs.length === 0) {
        return true;
    }
    
    let isValid = true;
    
    requiredInputs.forEach(input => {
        if (!input.value.trim()) {
            isValid = false;
            input.classList.add('invalid');
        } else {
            input.classList.remove('invalid');
        }
    });
    
    return isValid;
}

// Show validation errors for a specific tab
function showValidationErrors(tabIndex) {
    const tabContent = tabContents[tabIndex];
    const requiredInputs = tabContent.querySelectorAll('input[required]');
    
    requiredInputs.forEach(input => {
        if (!input.value.trim()) {
            input.classList.add('invalid');
            
            // Add validation message if not already present
            let validationMessage = input.nextElementSibling;
            if (!validationMessage || !validationMessage.classList.contains('validation-message')) {
                validationMessage = document.createElement('div');
                validationMessage.className = 'validation-message';
                validationMessage.textContent = 'This field is required';
                input.parentNode.insertBefore(validationMessage, input.nextSibling);
            }
        }
    });
    
    // Show toast message
    showToast('Please fill in all required fields', 'error');
}

// Update summary tab with current form values
function updateSummary() {
    // Product information
    document.getElementById('summary-product-name').textContent = 
        document.getElementById('productName').value || '-';
    
    document.getElementById('summary-product-url').textContent = 
        document.getElementById('productUrl').value || '-';
    
    // Serial numbers
    const serialNumbers = [];
    document.querySelectorAll('input[name="serial_numbers[]"]').forEach(input => {
        if (input.value.trim()) {
            serialNumbers.push(input.value.trim());
        }
    });
    
    const serialNumbersContainer = document.getElementById('summary-serial-numbers');
    if (serialNumbers.length > 0) {
        serialNumbersContainer.innerHTML = '<ul>' + 
            serialNumbers.map(sn => `<li>${sn}</li>`).join('') + 
            '</ul>';
    } else {
        serialNumbersContainer.textContent = 'None';
    }
    
    // Warranty details
    const purchaseDate = document.getElementById('purchaseDate').value;
    document.getElementById('summary-purchase-date').textContent = purchaseDate ? 
        new Date(purchaseDate).toLocaleDateString() : '-';
    
    const warrantyYears = document.getElementById('warrantyYears').value;
    document.getElementById('summary-warranty-years').textContent = warrantyYears ? 
        `${warrantyYears} ${warrantyYears > 1 ? 'years' : 'year'}` : '-';
    
    // Calculate and display expiration date
    if (purchaseDate && warrantyYears) {
        const expirationDate = new Date(purchaseDate);
        expirationDate.setFullYear(expirationDate.getFullYear() + parseInt(warrantyYears));
        document.getElementById('summary-expiration-date').textContent = 
            expirationDate.toLocaleDateString();
    } else {
        document.getElementById('summary-expiration-date').textContent = '-';
    }
    
    // Purchase price
    const purchasePrice = document.getElementById('purchasePrice').value;
    document.getElementById('summary-purchase-price').textContent = purchasePrice ? 
        `$${parseFloat(purchasePrice).toFixed(2)}` : 'Not specified';
    
    // Documents
    const invoiceFile = document.getElementById('invoice').files[0];
    document.getElementById('summary-invoice').textContent = invoiceFile ? 
        invoiceFile.name : 'No file selected';
    
    const manualFile = document.getElementById('manual').files[0];
    document.getElementById('summary-manual').textContent = manualFile ? 
        manualFile.name : 'No file selected';
}

// Add input event listeners to remove validation errors when user types
document.addEventListener('input', (e) => {
    if (e.target.hasAttribute('required') && e.target.classList.contains('invalid')) {
        if (e.target.value.trim()) {
            e.target.classList.remove('invalid');
            
            // Remove validation message if exists
            const validationMessage = e.target.nextElementSibling;
            if (validationMessage && validationMessage.classList.contains('validation-message')) {
                validationMessage.remove();
            }
        }
    }
});

// Function to reset the form and initialize serial number inputs
function resetForm() {
    // Reset the form
    warrantyForm.reset();
    
    // Reset serial numbers container
    serialNumbersContainer.innerHTML = '';
    
    // Add the first serial number input
    addSerialNumberInput();
    
    // Reset form tabs
    currentTabIndex = 0;
    switchToTab(0);
    
    // Clear any file input displays
    fileName.textContent = '';
    manualFileName.textContent = '';
}

async function exportWarranties() {
    // Get filtered warranties
    let warrantiesToExport = [...warranties];
    
    // Apply current filters
    if (currentFilters.search) {
        warrantiesToExport = warrantiesToExport.filter(warranty => 
            warranty.product_name.toLowerCase().includes(currentFilters.search)
        );
    }
    
    if (currentFilters.status !== 'all') {
        warrantiesToExport = warrantiesToExport.filter(warranty => 
            warranty.status === currentFilters.status
        );
    }
    
    // Create CSV content
    let csvContent = "data:text/csv;charset=utf-8,";
    
    // Add headers
    csvContent += "Product Name,Purchase Date,Warranty Period,Expiration Date,Status,Serial Numbers\n";
    
    // Add data rows
    warrantiesToExport.forEach(warranty => {
        const purchaseDate = new Date(warranty.purchase_date).toLocaleDateString();
        const expirationDate = new Date(warranty.expiration_date).toLocaleDateString();
        const serialNumbers = Array.isArray(warranty.serial_numbers) 
            ? warranty.serial_numbers.join('; ')
            : '';
        
        // Calculate status if not already set
        if (!warranty.status) {
            const today = new Date();
            const expDate = new Date(warranty.expiration_date);
            const daysRemaining = Math.floor((expDate - today) / (1000 * 60 * 60 * 24));
            
            if (daysRemaining < 0) {
                warranty.status = 'Expired';
            } else if (daysRemaining < expiringSoonDays) {
                warranty.status = 'Expiring Soon';
            } else {
                warranty.status = 'Active';
            }
        }
        
        // Format status for CSV
        let statusText = warranty.status.charAt(0).toUpperCase() + warranty.status.slice(1);
        if (statusText === 'Expiring') statusText = 'Expiring Soon';
        
        // Create CSV row
        csvContent += `"${warranty.product_name}",${purchaseDate},${warranty.warranty_years} years,${expirationDate},${statusText},"${serialNumbers}"\n`;
    });
    
    // Create download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    link.setAttribute("download", "warranties.csv");
    document.body.appendChild(link);
    
    // Trigger download
    link.click();
    
    // Clean up
    document.body.removeChild(link);
    
    showToast('Warranties exported successfully', 'success');
}

// Switch view of warranties list
function switchView(viewType) {
    console.log(`Switching to ${viewType} view...`);
    
    // Update currentView
    currentView = viewType;
    
    // Remove active class from all view buttons
    gridViewBtn.classList.remove('active');
    listViewBtn.classList.remove('active');
    tableViewBtn.classList.remove('active');
    
    // Update the view
    warrantiesList.className = `warranties-list ${viewType}-view`;
    
    // Hide table header if not in table view
    if (tableViewHeader) {
        tableViewHeader.style.display = viewType === 'table' ? 'flex' : 'none';
    }
    
    // Add active class to the selected view button
    if (viewType === 'grid') {
        gridViewBtn.classList.add('active');
    } else if (viewType === 'list') {
        listViewBtn.classList.add('active');
    } else if (viewType === 'table') {
        tableViewBtn.classList.add('active');
    }
    
    // Re-render warranties with the new view
    console.log('Applying filters after switching view...');
    applyFilters();
    
    // Get prefix for user-specific preferences
    const prefix = getPreferenceKeyPrefix();
    
    // Save view preference to localStorage with the appropriate prefix
    localStorage.setItem(`${prefix}warrantyView`, viewType);
    localStorage.setItem('warrantyView', viewType); // Keep global setting for backward compatibility
}

// Load saved view preference
function loadViewPreference() {
    // Get prefix for user-specific preferences
    const prefix = getPreferenceKeyPrefix();
    
    // First check for user-specific warrantyView
    const userSavedView = localStorage.getItem(`${prefix}warrantyView`);
    
    if (userSavedView) {
        console.log(`Found user-specific view preference: ${userSavedView}`);
        switchView(userSavedView);
        return;
    }
    
    // If not found, check for user-specific defaultView
    const userDefaultView = localStorage.getItem(`${prefix}defaultView`);
    if (userDefaultView) {
        console.log(`Found user-specific default view: ${userDefaultView}`);
        switchView(userDefaultView);
        return;
    }
    
    // If no user-specific preferences found, check global preferences for backward compatibility
    const globalSavedView = localStorage.getItem('warrantyView');
    if (globalSavedView) {
        console.log(`Found global view preference: ${globalSavedView}`);
        switchView(globalSavedView);
        return;
    }
    
    const globalDefaultView = localStorage.getItem('defaultView');
    if (globalDefaultView) {
        console.log(`Found global default view: ${globalDefaultView}`);
        switchView(globalDefaultView);
        return;
    }
    
    // Default to grid view if no preferences found
    console.log('No view preference found, defaulting to grid view');
    switchView('grid');
}

// Dark mode toggle
darkModeToggle.addEventListener('change', (e) => {
    setTheme(e.target.checked);
});

const serialNumbersContainer = document.getElementById('serialNumbersContainer');

// Add event listener for adding new serial number inputs
serialNumbersContainer.addEventListener('click', (e) => {
    if (e.target.closest('.add-serial-number')) {
        addSerialNumberInput();
    }
});

function addSerialNumberInput(container = serialNumbersContainer) {
    // Check if this is the first input or an additional one
    const isFirstInput = container.querySelectorAll('.serial-number-input').length === 0;
    
    const newInput = document.createElement('div');
    newInput.className = 'serial-number-input';
    
    if (isFirstInput) {
        // First input should have both Add and Remove buttons
        newInput.innerHTML = `
            <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number">
            <button type="button" class="btn btn-sm btn-primary add-serial-number">
                <i class="fas fa-plus"></i> Add Another
            </button>
        `;
        
        // Add event listener for the Add button
        newInput.querySelector('.add-serial-number').addEventListener('click', function(e) {
            e.stopPropagation(); // Stop event from bubbling up to the container
            addSerialNumberInput(container);
        });
    } else {
        // Additional inputs should have only Remove button
        newInput.innerHTML = `
            <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number">
            <button type="button" class="btn btn-sm btn-danger remove-serial-number">
                <i class="fas fa-minus"></i> Remove
            </button>
        `;
        
        // Add remove button functionality
        newInput.querySelector('.remove-serial-number').addEventListener('click', function() {
            this.parentElement.remove();
        });
    }
    
    container.appendChild(newInput);
}

// Functions
function showLoading() {
    loadingContainer.classList.add('active');
}

function hideLoading() {
    loadingContainer.classList.remove('active');
}

function showToast(message, type = 'info') {
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

function updateFileName(event, inputId = 'invoice', outputId = 'fileName') {
    const input = document.getElementById(inputId);
    const output = document.getElementById(outputId);
    
    if (input.files.length > 0) {
        output.textContent = input.files[0].name;
    } else {
        output.textContent = '';
    }
}

// Helper function to process warranty data
function processWarrantyData(warranty) {
    console.log('Processing warranty data:', warranty);
    
    // Create a copy of the warranty object to avoid modifying the original
    const processedWarranty = { ...warranty };
    
    // Ensure product_name exists
    if (!processedWarranty.product_name) {
        processedWarranty.product_name = 'Unnamed Product';
    }
    
    const today = new Date();
    
    // Handle purchase date
    let purchaseDate = null;
    if (processedWarranty.purchase_date) {
        purchaseDate = new Date(processedWarranty.purchase_date);
        // Check if date is valid
        if (isNaN(purchaseDate.getTime())) {
            purchaseDate = null;
        }
    }
    processedWarranty.purchaseDate = purchaseDate;
    
    // Handle expiration date
    let expirationDate = null;
    if (processedWarranty.expiration_date) {
        expirationDate = new Date(processedWarranty.expiration_date);
        // Check if date is valid
        if (isNaN(expirationDate.getTime())) {
            expirationDate = null;
        }
    }
    processedWarranty.expirationDate = expirationDate;
    
    // Calculate days remaining only if expiration date is valid
    let daysRemaining = null;
    if (expirationDate && !isNaN(expirationDate.getTime())) {
        daysRemaining = Math.floor((expirationDate - today) / (1000 * 60 * 60 * 24));
    }
    
    let statusClass = 'active';
    let statusText = 'Active';
    
    if (daysRemaining === null) {
        statusClass = 'unknown';
        statusText = 'Unknown status';
    } else if (daysRemaining < 0) {
        statusClass = 'expired';
        statusText = 'Expired';
    } else if (daysRemaining < expiringSoonDays) {
        console.log(`Using expiringSoonDays: ${expiringSoonDays} for warranty: ${processedWarranty.product_name}`);
        statusClass = 'expiring';
        statusText = `Expiring Soon (${daysRemaining} days)`;
    } else {
        statusText = `${daysRemaining} days remaining`;
    }
    
    // Add status to warranty object
    processedWarranty.status = statusClass;
    processedWarranty.daysRemaining = daysRemaining;
    processedWarranty.statusText = statusText;
    
    console.log('Processed warranty data result:', processedWarranty);
    return processedWarranty;
}

// Function to process all warranties in the array
function processAllWarranties() {
    console.log('Processing all warranties in array...');
    if (warranties && warranties.length > 0) {
        warranties = warranties.map(warranty => processWarrantyData(warranty));
    }
    console.log('Processed warranties:', warranties);
}

async function loadWarranties() {
    try {
        console.log('Loading warranties...');
        showLoading();
        
        // Get expiring soon days from user preferences if available
        try {
            const prefsResponse = await fetch('/api/auth/preferences', {
                headers: {
                    'Authorization': `Bearer ${localStorage.getItem('auth_token')}`
                }
            });
            
            if (prefsResponse.ok) {
                const data = await prefsResponse.json();
                if (data && data.expiring_soon_days) {
                    const oldValue = expiringSoonDays;
                    expiringSoonDays = data.expiring_soon_days;
                    console.log('Updated expiring soon days from preferences:', expiringSoonDays);
                    
                    // If we already have warranties loaded and the value changed, reprocess them
                    if (warranties && warranties.length > 0 && oldValue !== expiringSoonDays) {
                        console.log('Reprocessing warranties with new expiringSoonDays value');
                        warranties = warranties.map(warranty => processWarrantyData(warranty));
                        renderWarrantiesTable(warranties);
                    }
                }
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
            // Continue with default value
        }
        
        // Use the full URL to avoid path issues
        const apiUrl = window.location.origin + '/api/warranties';
        
        // Check if auth is available and user is authenticated
        if (!window.auth || !window.auth.isAuthenticated()) {
            console.log('User not authenticated, showing empty state');
            renderEmptyState('Please log in to view your warranties.');
            hideLoading();
            return;
        }
        
        // Get the auth token
        const token = window.auth.getToken();
        if (!token) {
            console.log('No auth token available');
            renderEmptyState('Authentication error. Please log in again.');
            hideLoading();
            return;
        }
        
        // Create request with auth header
        const options = {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        };
        
        console.log('Fetching warranties with auth token');
        const response = await fetch(apiUrl, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: `HTTP error ${response.status}` }));
            console.error('Error loading warranties:', response.status, errorData);
            throw new Error(`Error loading warranties: ${errorData.message || response.status}`);
        }
        
        const data = await response.json();
        console.log('Received warranties from server:', data);
        
        // Process each warranty to calculate status and days remaining
        warranties = data.map(warranty => {
            return processWarrantyData(warranty);
        });
        
        console.log('Processed warranties:', warranties);
        
        if (warranties.length === 0) {
            console.log('No warranties found, showing empty state');
            renderEmptyState('No warranties found. Add your first warranty using the form.');
        } else {
            console.log('Applying filters to display warranties');
            applyFilters();
        }
    } catch (error) {
        console.error('Error loading warranties:', error);
        renderEmptyState('Error loading warranties. Please try again later.');
    } finally {
        hideLoading();
    }
}

function renderEmptyState(message = 'No warranties yet. Add your first warranty to get started.') {
    warrantiesList.innerHTML = `
        <div class="empty-state">
            <i class="fas fa-box-open"></i>
            <h3>No warranties found</h3>
            <p>${message}</p>
        </div>
    `;
}

function formatDate(date) {
    if (!date) return 'N/A';
    
    // If date is already a Date object, use it directly
    const dateObj = date instanceof Date ? date : new Date(date);
    
    // Check if date is valid
    if (isNaN(dateObj.getTime())) {
        return 'N/A';
    }
    
    return dateObj.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

async function renderWarranties(warrantiesToRender) {
    console.log('renderWarranties called with:', warrantiesToRender);
    if (!warrantiesToRender || warrantiesToRender.length === 0) {
        renderEmptyState();
        return;
    }
    
    const today = new Date();
    
    warrantiesList.innerHTML = '';
    
    // Apply sorting based on current sort selection
    const sortedWarranties = [...warrantiesToRender].sort((a, b) => {
        switch (currentFilters.sort) {
            case 'name':
                return a.product_name.localeCompare(b.product_name);
            case 'purchase':
                return new Date(b.purchase_date || 0) - new Date(a.purchase_date || 0);
            case 'expiration':
            default:
                const dateA = new Date(a.expiration_date || 0);
                const dateB = new Date(b.expiration_date || 0);
                
                const isExpiredA = dateA < today;
                const isExpiredB = dateB < today;
                
                if (isExpiredA && !isExpiredB) return 1;
                if (!isExpiredA && isExpiredB) return -1;
                
                // Both active or both expired, sort by date
                return dateA - dateB;
        }
    });
    
    console.log('Sorted warranties:', sortedWarranties);
    
    // Update the container class based on current view
    warrantiesList.className = `warranties-list ${currentView}-view`;
    
    // Show/hide table header for table view
    if (tableViewHeader) {
        tableViewHeader.classList.toggle('visible', currentView === 'table');
    }
    
    // Update view buttons to reflect current view
    if (gridViewBtn && listViewBtn && tableViewBtn) {
        gridViewBtn.classList.toggle('active', currentView === 'grid');
        listViewBtn.classList.toggle('active', currentView === 'list');
        tableViewBtn.classList.toggle('active', currentView === 'table');
    }
    
    sortedWarranties.forEach(warranty => {
        // Use the pre-processed dates from the warranty object
        const purchaseDate = warranty.purchaseDate;
        const expirationDate = warranty.expirationDate;
        
        // Use the pre-calculated status and days remaining from the warranty object
        const statusClass = warranty.status || 'unknown';
        const statusText = warranty.statusText || 'Unknown status';
        
        // Debug file paths
        console.log(`Warranty ID ${warranty.id} - Product: ${warranty.product_name}`);
        console.log(`- Invoice path: ${warranty.invoice_path}`);
        console.log(`- Manual path: ${warranty.manual_path}`);
        
        // Make sure serial numbers array exists and is valid
        const validSerialNumbers = Array.isArray(warranty.serial_numbers) 
            ? warranty.serial_numbers.filter(sn => sn && typeof sn === 'string' && sn.trim() !== '')
            : [];
        
        const cardElement = document.createElement('div');
        cardElement.className = `warranty-card ${statusClass === 'expired' ? 'expired' : statusClass === 'expiring' ? 'expiring-soon' : 'active'}`;
        
        // Create different HTML structure based on the current view
        if (currentView === 'grid') {
            // Grid view HTML structure
            cardElement.innerHTML = `
                <div class="product-name-header">
                    <h3 class="warranty-title">${warranty.product_name || 'Unnamed Product'}</h3>
                    <div class="warranty-actions">
                        <button class="action-btn edit-btn" title="Edit" data-id="${warranty.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="action-btn delete-btn" title="Delete" data-id="${warranty.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="warranty-content">
                    <div class="warranty-info">
                        <div>Purchased: <span>${formatDate(purchaseDate)}</span></div>
                        <div>Warranty: <span>${warranty.warranty_years !== undefined ? `${warranty.warranty_years} ${warranty.warranty_years === 1 ? 'year' : 'years'}` : 'N/A'}</span></div>
                        <div>Expires: <span>${formatDate(expirationDate)}</span></div>
                        ${warranty.purchase_price ? `<div>Price: <span>$${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
                        ${validSerialNumbers.length > 0 ? `
                            <div class="serial-numbers">
                                <strong>Serial Numbers:</strong>
                                <ul>
                                    ${validSerialNumbers.map(sn => `<li>${sn}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="warranty-status-row status-${statusClass}">
                    <span>${statusText}</span>
                </div>
                <div class="document-links-row">
                    ${warranty.product_url ? `
                        <a href="${warranty.product_url}" class="product-link" target="_blank">
                            <i class="fas fa-globe"></i> Product Website
                        </a>
                    ` : ''}
                    ${warranty.invoice_path && warranty.invoice_path !== 'null' ? `
                        <a href="#" onclick="openSecureFile('${warranty.invoice_path}'); return false;" class="invoice-link">
                            <i class="fas fa-file-invoice"></i> Invoice
                        </a>` : ''}
                    ${warranty.manual_path && warranty.manual_path !== 'null' ? `
                        <a href="#" onclick="openSecureFile('${warranty.manual_path}'); return false;" class="manual-link">
                            <i class="fas fa-book"></i> Manual
                        </a>` : ''}
                </div>
            `;
        } else if (currentView === 'list') {
            // List view HTML structure
            cardElement.innerHTML = `
                <div class="product-name-header">
                    <h3 class="warranty-title">${warranty.product_name || 'Unnamed Product'}</h3>
                    <div class="warranty-actions">
                        <button class="action-btn edit-btn" title="Edit" data-id="${warranty.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="action-btn delete-btn" title="Delete" data-id="${warranty.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="warranty-content">
                    <div class="warranty-info">
                        <div>Purchased: <span>${formatDate(purchaseDate)}</span></div>
                        <div>Warranty: <span>${warranty.warranty_years !== undefined ? `${warranty.warranty_years} ${warranty.warranty_years === 1 ? 'year' : 'years'}` : 'N/A'}</span></div>
                        <div>Expires: <span>${formatDate(expirationDate)}</span></div>
                        ${warranty.purchase_price ? `<div>Price: <span>$${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
                        ${validSerialNumbers.length > 0 ? `
                            <div class="serial-numbers">
                                <strong>Serial Numbers:</strong>
                                <ul>
                                    ${validSerialNumbers.map(sn => `<li>${sn}</li>`).join('')}
                                </ul>
                            </div>
                        ` : ''}
                    </div>
                </div>
                <div class="warranty-status-row status-${statusClass}">
                    <span>${statusText}</span>
                </div>
                <div class="document-links-row">
                    ${warranty.product_url ? `
                        <a href="${warranty.product_url}" class="product-link" target="_blank">
                            <i class="fas fa-globe"></i> Product Website
                        </a>
                    ` : ''}
                    ${warranty.invoice_path && warranty.invoice_path !== 'null' ? `
                        <a href="#" onclick="openSecureFile('${warranty.invoice_path}'); return false;" class="invoice-link">
                            <i class="fas fa-file-invoice"></i> Invoice
                        </a>` : ''}
                    ${warranty.manual_path && warranty.manual_path !== 'null' ? `
                        <a href="#" onclick="openSecureFile('${warranty.manual_path}'); return false;" class="manual-link">
                            <i class="fas fa-book"></i> Manual
                        </a>` : ''}
                </div>
            `;
        } else if (currentView === 'table') {
            // Table view HTML structure
            cardElement.innerHTML = `
                <div class="product-name-header">
                    <h3 class="warranty-title">${warranty.product_name || 'Unnamed Product'}</h3>
                    <div class="warranty-actions">
                        <button class="action-btn edit-btn" title="Edit" data-id="${warranty.id}">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="action-btn delete-btn" title="Delete" data-id="${warranty.id}">
                            <i class="fas fa-trash"></i>
                        </button>
                    </div>
                </div>
                <div class="warranty-content">
                    <div class="warranty-info">
                        <div>Purchased: <span>${formatDate(purchaseDate)}</span></div>
                        <div>Expires: <span>${formatDate(expirationDate)}</span></div>
                    </div>
                </div>
                <div class="warranty-status-row status-${statusClass}">
                    <span>${statusText}</span>
                </div>
                <div class="document-links-row">
                    ${warranty.product_url ? `
                        <a href="${warranty.product_url}" class="product-link" target="_blank">
                            <i class="fas fa-globe"></i>
                        </a>
                    ` : ''}
                    ${warranty.invoice_path && warranty.invoice_path !== 'null' ? `
                        <a href="#" onclick="openSecureFile('${warranty.invoice_path}'); return false;" class="invoice-link">
                            <i class="fas fa-file-invoice"></i>
                        </a>` : ''}
                    ${warranty.manual_path && warranty.manual_path !== 'null' ? `
                        <a href="#" onclick="openSecureFile('${warranty.manual_path}'); return false;" class="manual-link">
                            <i class="fas fa-book"></i>
                        </a>` : ''}
                </div>
            `;
        }
        
        // Add event listeners
        warrantiesList.appendChild(cardElement);
        
        // Edit button event listener
        cardElement.querySelector('.edit-btn').addEventListener('click', () => {
            openEditModal(warranty);
        });
        
        // Delete button event listener
        cardElement.querySelector('.delete-btn').addEventListener('click', () => {
            openDeleteModal(warranty.id);
        });
    });
}

function filterWarranties() {
    const searchTerm = searchInput.value.toLowerCase();
    
    if (!searchTerm) {
        renderWarranties();
        return;
    }
    
    const filtered = warranties.filter(warranty => 
        warranty.product_name.toLowerCase().includes(searchTerm)
    );
    
    renderWarranties(filtered);
}

function applyFilters() {
    console.log('Applying filters with:', currentFilters);
    
    // Filter warranties based on currentFilters
    const filtered = warranties.filter(warranty => {
        // Status filter
        if (currentFilters.status !== 'all' && warranty.status !== currentFilters.status) {
            return false;
        }
        
        // Search filter
        if (currentFilters.search && !warranty.product_name.toLowerCase().includes(currentFilters.search.toLowerCase())) {
            return false;
        }
        
        return true;
    });
    
    console.log('Filtered warranties:', filtered);
    
    // Render the filtered warranties
    renderWarranties(filtered);
}

function openEditModal(warranty) {
    currentWarrantyId = warranty.id;
    
    // Populate form fields
    document.getElementById('editProductName').value = warranty.product_name;
    document.getElementById('editProductUrl').value = warranty.product_url || '';
    document.getElementById('editPurchaseDate').value = warranty.purchase_date.split('T')[0];
    document.getElementById('editWarrantyYears').value = warranty.warranty_years;
    document.getElementById('editPurchasePrice').value = warranty.purchase_price || '';
    
    // Clear existing serial number inputs
    const editSerialNumbersContainer = document.getElementById('editSerialNumbersContainer');
    editSerialNumbersContainer.innerHTML = '';
    
    // Add event listener for adding new serial number inputs in edit modal
    editSerialNumbersContainer.addEventListener('click', (e) => {
        if (e.target.closest('.add-serial-number')) {
            addSerialNumberInput(editSerialNumbersContainer);
        }
    });
    
    const validSerialNumbers = Array.isArray(warranty.serial_numbers)
        ? warranty.serial_numbers.filter(sn => sn && typeof sn === 'string' && sn.trim() !== '')
        : [];
    
    if (validSerialNumbers.length === 0) {
        // Add a single empty input if there are no serial numbers
        addSerialNumberInput(editSerialNumbersContainer);
    } else {
        // Add the first serial number with an "Add Another" button
        const firstInput = document.createElement('div');
        firstInput.className = 'serial-number-input';
        firstInput.innerHTML = `
            <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number" value="${validSerialNumbers[0]}">
            <button type="button" class="btn btn-sm btn-primary add-serial-number">
                <i class="fas fa-plus"></i> Add Another
            </button>
        `;
        
        // Add event listener for the Add button
        firstInput.querySelector('.add-serial-number').addEventListener('click', function(e) {
            e.stopPropagation(); // Stop event from bubbling up
            addSerialNumberInput(editSerialNumbersContainer);
        });
        
        editSerialNumbersContainer.appendChild(firstInput);
        
        // Add the rest of the serial numbers with "Remove" buttons
        for (let i = 1; i < validSerialNumbers.length; i++) {
            const newInput = document.createElement('div');
            newInput.className = 'serial-number-input';
            newInput.innerHTML = `
                <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number" value="${validSerialNumbers[i]}">
                <button type="button" class="btn btn-sm btn-danger remove-serial-number">
                    <i class="fas fa-minus"></i> Remove
                </button>
            `;
            
            // Add remove button functionality
            newInput.querySelector('.remove-serial-number').addEventListener('click', function() {
                this.parentElement.remove();
            });
            
            editSerialNumbersContainer.appendChild(newInput);
        }
    }
    
    // Show current invoice if exists
    const currentInvoiceElement = document.getElementById('currentInvoice');
    if (currentInvoiceElement) {
        if (warranty.invoice_path && warranty.invoice_path !== 'null') {
            currentInvoiceElement.innerHTML = `
                <span class="text-success">
                    <i class="fas fa-check-circle"></i> Current invoice: 
                    <a href="#" onclick="openSecureFile('${warranty.invoice_path}'); return false;">View</a>
                    (Upload a new file to replace)
                </span>
            `;
        } else {
            currentInvoiceElement.innerHTML = '<span>No invoice uploaded</span>';
        }
    }
    
    // Show current manual if exists
    const currentManualElement = document.getElementById('currentManual');
    if (currentManualElement) {
        if (warranty.manual_path && warranty.manual_path !== 'null') {
            currentManualElement.innerHTML = `
                <span class="text-success">
                    <i class="fas fa-check-circle"></i> Current manual: 
                    <a href="#" onclick="openSecureFile('${warranty.manual_path}'); return false;">View</a>
                    (Upload a new file to replace)
                </span>
            `;
        } else {
            currentManualElement.innerHTML = '<span>No manual uploaded</span>';
        }
    }
    
    // Reset file inputs
    document.getElementById('editInvoice').value = '';
    document.getElementById('editManual').value = '';
    document.getElementById('editFileName').textContent = '';
    document.getElementById('editManualFileName').textContent = '';
    
    // Show edit modal
    const modal = document.getElementById('editModal');
    modal.classList.add('active'); // Add active class instead of setting display style
    
    // Reset tabs to first tab
    const editTabBtns = document.querySelectorAll('.edit-tab-btn');
    editTabBtns.forEach(btn => btn.classList.remove('active'));
    document.querySelector('.edit-tab-btn[data-tab="edit-product-info"]').classList.add('active');
    
    // Reset tab content
    document.querySelectorAll('.edit-tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById('edit-product-info').classList.add('active');
    
    // Validate all tabs to update completion indicators
    validateEditTab('edit-product-info');
    validateEditTab('edit-warranty-details');
    validateEditTab('edit-documents');
    
    // Add input event listeners to update validation status
    document.querySelectorAll('#editWarrantyForm input').forEach(input => {
        input.addEventListener('input', function() {
            // Find the tab this input belongs to
            const tabContent = this.closest('.edit-tab-content');
            if (tabContent) {
                validateEditTab(tabContent.id);
            }
        });
    });
}

function openDeleteModal(warrantyId) {
    currentWarrantyId = warrantyId;
    deleteModal.classList.add('active');
}

function closeModals() {
    editModal.classList.remove('active');
    deleteModal.classList.remove('active');
    currentWarrantyId = null;
}

// Validate file size before upload
function validateFileSize(formData, maxSizeMB = 32) {
    let totalSize = 0;
    
    // Check file sizes
    if (formData.has('invoice') && formData.get('invoice').size > 0) {
        totalSize += formData.get('invoice').size;
    }
    
    if (formData.has('manual') && formData.get('manual').size > 0) {
        totalSize += formData.get('manual').size;
    }
    
    // Convert bytes to MB for comparison and display
    const totalSizeMB = totalSize / (1024 * 1024);
    console.log(`Total upload size: ${totalSizeMB.toFixed(2)} MB`);
    
    // Check if total size exceeds limit
    if (totalSizeMB > maxSizeMB) {
        return {
            valid: false,
            message: `Total file size (${totalSizeMB.toFixed(2)} MB) exceeds the maximum allowed size of ${maxSizeMB} MB. Please reduce file sizes.`
        };
    }
    
    return {
        valid: true
    };
}

// Modify the beginning of the addWarranty function to check file sizes before uploading
async function addWarranty(event) {
    event.preventDefault();
    
    // Check authentication first
    if (!window.auth || !window.auth.isAuthenticated()) {
        showToast('Please log in to add warranties', 'error');
        return;
    }
    
    // Validate the current tab
    if (!validateTab(currentTabIndex)) {
        return;
    }
    
    try {
        showLoading();
        
        // Create FormData object
        const formData = new FormData(warrantyForm);
        
        // Validate file sizes before trying to upload
        const fileSizeValidation = validateFileSize(formData);
        if (!fileSizeValidation.valid) {
            showToast(fileSizeValidation.message, 'error');
            hideLoading();
            return;
        }
        
        // Get all serial numbers
        const serialNumbers = [];
        document.querySelectorAll('input[name="serial_numbers[]"]').forEach(input => {
            if (input.value.trim()) {
                serialNumbers.push(input.value.trim());
            }
        });
        
        // Remove default serial numbers entry and add the collected ones
        formData.delete('serial_numbers[]');
        serialNumbers.forEach(sn => {
            formData.append('serial_numbers', sn);
        });
        
        // Get the auth token
        const token = window.auth.getToken();
        if (!token) {
            showToast('Authentication error. Please log in again.', 'error');
            hideLoading();
            closeModals();
            return;
        }
        
        // Create request with auth header
        const options = {
            method: 'POST',
            body: formData,
            headers: {
                'Authorization': `Bearer ${token}`
            }
        };
        
        // Use the full URL to avoid path issues
        const apiUrl = window.location.origin + '/api/warranties';
        
        console.log('Sending warranty data to server...');
        const response = await fetch(apiUrl, options);
        
        if (!response.ok) {
            // Specifically handle 413 Request Entity Too Large error
            if (response.status === 413) {
                throw new Error('File size too large. Please reduce the file size of your uploads (maximum 32MB total) or split into multiple warranties.');
            }
            
            const errorData = await response.json().catch(() => ({ message: `HTTP error ${response.status}` }));
            throw new Error(errorData.message || `Error adding warranty: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Received add warranty result:', result);
        
        // The server only returns the ID, so we need to fetch the complete warranty data
        if (result.id) {
            console.log('Fetching complete warranty data for ID:', result.id);
            
            // Reload all warranties to get the complete data
            await loadWarranties();
            
            // Reset the form and initialize serial number inputs
            resetForm();
            
            // Show success message
            showToast('Warranty added successfully!', 'success');
        } else {
            throw new Error('Failed to get warranty ID from server response');
        }
    } catch (error) {
        console.error('Error adding warranty:', error);
        showToast(error.message || 'Error adding warranty. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Modify the beginning of the updateWarranty function to check file sizes before uploading
async function updateWarranty() {
    // Check if user is authenticated
    if (window.auth && !window.auth.isAuthenticated()) {
        showToast('Please login to update warranties', 'warning');
        closeModals();
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1500);
        return;
    }
    
    if (!currentWarrantyId) {
        showToast('No warranty selected for update', 'error');
        return;
    }
    
    // Create FormData object
    const formData = new FormData(editWarrantyForm);
    
    // Validate file sizes before trying to upload
    const fileSizeValidation = validateFileSize(formData);
    if (!fileSizeValidation.valid) {
        showToast(fileSizeValidation.message, 'error');
        return;
    }
    
    // Get all serial numbers
    const serialNumbers = [];
    document.querySelectorAll('#editSerialNumbersContainer input[name="serial_numbers[]"]').forEach(input => {
        if (input.value.trim()) {
            serialNumbers.push(input.value.trim());
        }
    });
    
    // Remove default serial numbers entry and add the collected ones
    formData.delete('serial_numbers[]');
    serialNumbers.forEach(sn => {
        formData.append('serial_numbers', sn);
    });
    
    try {
        showLoading();
        
        // Get the auth token
        const token = window.auth.getToken();
        if (!token) {
            showToast('Authentication error. Please log in again.', 'error');
            hideLoading();
            closeModals();
            return;
        }
        
        // Create request with auth header
        const options = {
            method: 'PUT',
            body: formData,
            headers: {
                'Authorization': `Bearer ${token}`
            }
        };
        
        // Use the full URL to avoid path issues
        const apiUrl = `${window.location.origin}/api/warranties/${currentWarrantyId}`;
        
        console.log('Updating warranty with ID:', currentWarrantyId);
        const response = await fetch(apiUrl, options);
        
        if (!response.ok) {
            // Specifically handle 413 Request Entity Too Large error
            if (response.status === 413) {
                throw new Error('File size too large. Please reduce the file size of your uploads (maximum 32MB total) or split into multiple warranties.');
            }
            
            const errorData = await response.json().catch(() => ({ message: `HTTP error ${response.status}` }));
            throw new Error(errorData.message || `Error updating warranty: ${response.status}`);
        }
        
        const result = await response.json();
        console.log('Received update warranty result:', result);
        
        // Reload all warranties to get the complete data
        await loadWarranties();
        
        // Close modal
        closeModals();
        
        // Show success message
        showToast('Warranty updated successfully!', 'success');
    } catch (error) {
        console.error('Error updating warranty:', error);
        showToast(error.message || 'Error updating warranty. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

async function deleteWarranty() {
    // Check if user is authenticated
    if (window.auth && !window.auth.isAuthenticated()) {
        showToast('Please login to delete warranties', 'warning');
        closeModals();
        setTimeout(() => {
            window.location.href = 'login.html';
        }, 1500);
        return;
    }
    
    if (!currentWarrantyId) {
        showToast('No warranty selected for deletion', 'error');
        return;
    }
    
    try {
        showLoading();
        
        // Get the auth token
        const token = window.auth.getToken();
        if (!token) {
            showToast('Authentication error. Please log in again.', 'error');
            hideLoading();
            closeModals();
            return;
        }
        
        // Create request with auth header
        const options = {
            method: 'DELETE',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json'
            }
        };
        
        // Use the full URL to avoid path issues
        const apiUrl = `${window.location.origin}/api/warranties/${currentWarrantyId}`;
        
        console.log('Deleting warranty with ID:', currentWarrantyId);
        const response = await fetch(apiUrl, options);
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({ message: `HTTP error ${response.status}` }));
            throw new Error(errorData.message || `Error deleting warranty: ${response.status}`);
        }
        
        // Reload all warranties to get the updated list
        await loadWarranties();
        
        // Close the modal
        closeModals();
        
        // Show success message
        showToast('Warranty deleted successfully!', 'success');
    } catch (error) {
        console.error('Error deleting warranty:', error);
        showToast(error.message || 'Error deleting warranty. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

// Initialize page
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM fully loaded, initializing app...');
    
    // Ensure auth state is checked
    if (window.auth && window.auth.checkAuthState) {
        window.auth.checkAuthState();
    }
    
    // Initialize settings button
    if (settingsBtn && settingsMenu) {
        settingsBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            settingsMenu.classList.toggle('active');
        });
        
        // Close settings menu when clicking outside
        document.addEventListener('click', (e) => {
            if (settingsMenu.classList.contains('active') && 
                !settingsMenu.contains(e.target) && 
                !settingsBtn.contains(e.target)) {
                settingsMenu.classList.remove('active');
            }
        });
    }
    
    // Initialize the app
    initializeTheme();
    
    // Initialize form tabs
    initFormTabs();
    
    // Initialize the form
    resetForm();
    
    // Close modals when clicking outside or on close button
    document.querySelectorAll('.modal-backdrop, [data-dismiss="modal"]').forEach(element => {
        element.addEventListener('click', (e) => {
            if (e.target === element) {
                closeModals();
            }
        });
    });
    
    // Prevent modal content clicks from closing the modal
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    });
    
    // Filter event listeners
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            currentFilters.search = searchInput.value.toLowerCase();
            applyFilters();
        });
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            currentFilters.status = statusFilter.value;
            applyFilters();
        });
    }
    
    if (sortBySelect) {
        sortBySelect.addEventListener('change', () => {
            currentFilters.sort = sortBySelect.value;
            applyFilters();
        });
    }
    
    // View switcher event listeners
    if (gridViewBtn) gridViewBtn.addEventListener('click', () => switchView('grid'));
    if (listViewBtn) listViewBtn.addEventListener('click', () => switchView('list'));
    if (tableViewBtn) tableViewBtn.addEventListener('click', () => switchView('table'));
    
    // Export button event listener
    if (exportBtn) exportBtn.addEventListener('click', exportWarranties);
    
    // File input change event
    if (fileInput) fileInput.addEventListener('change', (e) => updateFileName(e, 'invoice', 'fileName'));
    if (manualInput) manualInput.addEventListener('change', (e) => updateFileName(e, 'manual', 'manualFileName'));
    
    const editInvoiceInput = document.getElementById('editInvoice');
    if (editInvoiceInput) {
        editInvoiceInput.addEventListener('change', () => {
            updateFileName(null, 'editInvoice', 'editFileName');
        });
    }
    
    const editManualInput = document.getElementById('editManual');
    if (editManualInput) {
        editManualInput.addEventListener('change', () => {
            updateFileName(null, 'editManual', 'editManualFileName');
        });
    }
    
    // Form submission
    if (warrantyForm) warrantyForm.addEventListener('submit', addWarranty);
    
    // Refresh button
    if (refreshBtn) refreshBtn.addEventListener('click', loadWarranties);
    
    // Save warranty changes
    if (saveWarrantyBtn) saveWarrantyBtn.addEventListener('click', updateWarranty);
    
    // Confirm delete button
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', deleteWarranty);
    
    // Load saved view preference
    loadViewPreference();
    
    // Load preferences first to ensure we have the correct expiringSoonDays value
    // before loading warranties
    if (window.auth && window.auth.isAuthenticated()) {
        console.log('User is authenticated, loading preferences...');
        const token = window.auth.getToken();
        
        if (token) {
            fetch('/api/auth/preferences', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            })
            .then(response => {
                if (response.ok) return response.json();
                throw new Error('Failed to load preferences');
            })
            .then(data => {
                if (data && data.expiring_soon_days) {
                    expiringSoonDays = data.expiring_soon_days;
                    console.log('Updated expiring soon days from preferences during initialization:', expiringSoonDays);
                }
                // Now load warranties with the updated preference
                loadWarranties();
            })
            .catch(error => {
                console.error('Error loading preferences during initialization:', error);
                // Still load warranties even if preferences couldn't be loaded
                loadWarranties();
            });
        } else {
            // No token available, load warranties with default preference
            loadWarranties();
        }
    } else {
        // User not authenticated, load warranties (this will show login prompt)
        loadWarranties();
    }
    
    // Initialize edit tabs
    initEditTabs();
    
    console.log('App initialization complete');
});

// Add this function to handle edit tab functionality
function initEditTabs() {
    const editTabBtns = document.querySelectorAll('.edit-tab-btn');
    
    editTabBtns.forEach(btn => {
        btn.addEventListener('click', () => {
            // Remove active class from all tabs
            editTabBtns.forEach(b => b.classList.remove('active'));
            
            // Add active class to clicked tab
            btn.classList.add('active');
            
            // Hide all tab content
            document.querySelectorAll('.edit-tab-content').forEach(content => {
                content.classList.remove('active');
            });
            
            // Show the selected tab content
            const tabId = btn.getAttribute('data-tab');
            document.getElementById(tabId).classList.add('active');
        });
    });
}

// Update validateEditTabs function
function validateEditTab(tabId) {
    const tab = document.getElementById(tabId);
    let isValid = true;
    
    // Get all required inputs in this tab
    const requiredInputs = tab.querySelectorAll('input[required]');
    
    // Check if all required fields are filled
    requiredInputs.forEach(input => {
        if (!input.value) {
            isValid = false;
            input.classList.add('invalid');
        } else {
            input.classList.remove('invalid');
        }
    });
    
    // Update the tab button to show completion status
    const tabBtn = document.querySelector(`.edit-tab-btn[data-tab="${tabId}"]`);
    if (isValid) {
        tabBtn.classList.add('completed');
    } else {
        tabBtn.classList.remove('completed');
    }
    
    return isValid;
}

// Add this function for secure file access
function openSecureFile(filePath) {
    if (!filePath || filePath === 'null') {
        console.error('Invalid file path:', filePath);
        showToast('Invalid file path', 'error');
        return false;
    }
    
    console.log('Opening secure file:', filePath);
    
    // Get the file name from the path
    const fileName = filePath.split('/').pop();
    
    // Get auth token
    const token = window.auth.getToken();
    if (!token) {
        showToast('Authentication error. Please log in again.', 'error');
        return false;
    }
    
    // Use fetch with proper authorization header
    fetch(`/api/secure-file/${fileName}`, {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error(`Error: ${response.status} ${response.statusText}`);
        }
        return response.blob();
    })
    .then(blob => {
        // Create a URL for the blob
        const blobUrl = window.URL.createObjectURL(blob);
        
        // Open in new tab
        window.open(blobUrl, '_blank');
    })
    .catch(error => {
        console.error('Error fetching file:', error);
        showToast('Error opening file: ' + error.message, 'error');
    });
    
    return false;
}