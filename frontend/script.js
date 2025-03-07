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

// Settings menu toggle
settingsBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    settingsMenu.classList.toggle('active');
});

// Close settings menu when clicking outside
document.addEventListener('click', (e) => {
    if (!settingsMenu.contains(e.target) && !settingsBtn.contains(e.target)) {
        settingsMenu.classList.remove('active');
    }
});

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
    const newInput = document.createElement('div');
    newInput.className = 'serial-number-input';
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
    
    container.appendChild(newInput);
}

// Variables
let warranties = [];
let currentWarrantyId = null;
let currentFilters = {
    search: '',
    status: 'all',
    sort: 'expiration'
};
let currentView = 'grid'; // Default view

// API URL
const API_URL = '/api/warranties';

// Event Listeners
document.addEventListener('DOMContentLoaded', () => {
    loadWarranties();
    
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

    // Initialize form tabs
    initFormTabs();
    
    // Filter event listeners
    searchInput.addEventListener('input', () => {
        currentFilters.search = searchInput.value.toLowerCase();
        applyFilters();
    });
    
    statusFilter.addEventListener('change', () => {
        currentFilters.status = statusFilter.value;
        applyFilters();
    });
    
    sortBySelect.addEventListener('change', () => {
        currentFilters.sort = sortBySelect.value;
        applyFilters();
    });
    
    // View switcher event listeners
    gridViewBtn.addEventListener('click', () => switchView('grid'));
    listViewBtn.addEventListener('click', () => switchView('list'));
    tableViewBtn.addEventListener('click', () => switchView('table'));
    
    // Export button event listener
    exportBtn.addEventListener('click', exportWarranties);
    
    // Load saved view preference
    loadViewPreference();
});

// File input change event
fileInput.addEventListener('change', (e) => updateFileName(e, 'invoice', 'fileName'));
manualInput.addEventListener('change', (e) => updateFileName(e, 'manual', 'manualFileName'));
document.getElementById('editInvoice').addEventListener('change', () => {
    updateFileName(null, 'editInvoice', 'editFileName');
});
document.getElementById('editManual').addEventListener('change', () => {
    updateFileName(null, 'editManual', 'editManualFileName');
});

// Form submission
warrantyForm.addEventListener('submit', addWarranty);

// Refresh button
refreshBtn.addEventListener('click', loadWarranties);

// Save warranty changes
saveWarrantyBtn.addEventListener('click', updateWarranty);

// Confirm delete button
confirmDeleteBtn.addEventListener('click', deleteWarranty);

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

async function loadWarranties() {
    showLoading();
    
    try {
        const response = await fetch(API_URL); // This fetch call now uses the CORRECTED API_URL
        if (!response.ok) {
            throw new Error('Failed to load warranties');
        }
        
        warranties = await response.json();
        renderWarranties();
    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error loading warranties:', error);
        renderEmptyState('Could not load warranties. Please try again.');
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

function renderWarranties(filteredWarranties = null) {
    const warrantiesToRender = filteredWarranties || warranties;
    
    if (warrantiesToRender.length === 0) {
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
                return new Date(b.purchase_date) - new Date(a.purchase_date);
            case 'expiration':
            default:
                const dateA = new Date(a.expiration_date);
                const dateB = new Date(b.expiration_date);
                
                const isExpiredA = dateA < today;
                const isExpiredB = dateB < today;
                
                if (isExpiredA && !isExpiredB) return 1;
                if (!isExpiredA && isExpiredB) return -1;
                
                // Both active or both expired, sort by date
                return dateA - dateB;
        }
    });
    
    sortedWarranties.forEach(warranty => {
        const purchaseDate = new Date(warranty.purchase_date);
        const expirationDate = new Date(warranty.expiration_date);
        const daysRemaining = Math.floor((expirationDate - today) / (1000 * 60 * 60 * 24));
        
        let statusClass = 'active';
        let statusText = 'Active';
        
        if (daysRemaining < 0) {
            statusClass = 'expired';
            statusText = 'Expired';
        } else if (daysRemaining < 30) {
            statusClass = 'expiring';
            statusText = `Expiring Soon (${daysRemaining} days)`;
        } else {
            statusText = `${daysRemaining} days remaining`;
        }
        
        // Add status to warranty object for filtering
        warranty.status = statusClass;
        warranty.daysRemaining = daysRemaining;
        
        // Make sure serial numbers array exists and is valid
        const validSerialNumbers = Array.isArray(warranty.serial_numbers) 
            ? warranty.serial_numbers.filter(sn => sn && typeof sn === 'string' && sn.trim() !== '')
            : [];
        
        const cardElement = document.createElement('div');
        cardElement.className = `warranty-card ${statusClass === 'expired' ? 'expired' : statusClass === 'expiring' ? 'expiring-soon' : 'active'}`;
        cardElement.innerHTML = `
            <div class="warranty-header">
                <h3 class="warranty-title">${warranty.product_name}</h3>
                <div class="warranty-actions">
                    <button class="action-btn edit-btn" title="Edit" data-id="${warranty.id}">
                        <i class="fas fa-edit"></i>
                    </button>
                    <button class="action-btn delete-btn" title="Delete" data-id="${warranty.id}">
                        <i class="fas fa-trash"></i>
                    </button>
                </div>
            </div>
            <div class="warranty-details">
                <div>Purchased: <span>${formatDate(purchaseDate)}</span></div>
                <div>Warranty: <span>${warranty.warranty_years} ${warranty.warranty_years > 1 ? 'years' : 'year'}</span></div>
                <div>Expires: <span>${formatDate(expirationDate)}</span></div>
                ${warranty.purchase_price ? `<div>Price: <span>$${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
                <span class="warranty-status status-${statusClass}">${statusText}</span>
                ${validSerialNumbers.length > 0 ? `
                    <div class="serial-numbers">
                        <strong>Serial Numbers:</strong>
                        <ul>
                            ${validSerialNumbers.map(sn => `<li>${sn}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                <div class="document-links-row">
                    ${warranty.product_url ? `
                        <a href="${warranty.product_url}" class="product-link" target="_blank">
                            <i class="fas fa-globe"></i> Product Website
                        </a>
                    ` : ''}
                    ${warranty.invoice_path ? `
                        <a href="${warranty.invoice_path}" class="invoice-link" target="_blank">
                            <i class="fas fa-file-invoice"></i> Invoice
                        </a>
                    ` : ''}
                    ${warranty.manual_path ? `
                        <a href="${warranty.manual_path}" class="manual-link" target="_blank">
                            <i class="fas fa-book"></i> Manual
                        </a>
                    ` : ''}
                </div>
            </div>
        `;
        
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

function formatDate(date) {
    return new Date(date).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

async function addWarranty(event) {
    event.preventDefault();
    showLoading();
    
    const formData = new FormData(warrantyForm);
    
    // Get all serial numbers and add them to formData
    const serialNumbers = [];
    document.querySelectorAll('input[name="serial_numbers[]"]').forEach(input => {
        if (input.value.trim()) {
            serialNumbers.push(input.value.trim());
        }
    });
    formData.delete('serial_numbers[]'); // Remove the original array
    if (serialNumbers.length > 0) {
        serialNumbers.forEach(sn => formData.append('serial_numbers', sn));
    }
    
    try {
        const response = await fetch(API_URL, {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to add warranty');
        }
        
        const result = await response.json();
        showToast('Warranty added successfully!', 'success');
        
        // Reset form
        warrantyForm.reset();
        fileName.textContent = '';
        manualFileName.textContent = '';
        
        // Completely reset serial number inputs
        serialNumbersContainer.innerHTML = '';
        
        // Create a fresh initial serial number input
        const initialInput = document.createElement('div');
        initialInput.className = 'serial-number-input';
        initialInput.innerHTML = `
            <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number">
            <button type="button" class="btn btn-sm btn-secondary add-serial-number">
                <i class="fas fa-plus"></i> Add Another
            </button>
        `;
        
        // Add the event listener for the "Add Another" button
        initialInput.querySelector('.add-serial-number').addEventListener('click', function() {
            addSerialNumberInput();
        });
        
        serialNumbersContainer.appendChild(initialInput);
        
        // Switch back to the first tab
        switchToTab(0);
        
        // Reload warranties
        loadWarranties();
    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error adding warranty:', error);
    } finally {
        hideLoading();
    }
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
    
    // Make sure serial numbers array exists and is valid
    const validSerialNumbers = Array.isArray(warranty.serial_numbers) 
        ? warranty.serial_numbers.filter(sn => sn && typeof sn === 'string' && sn.trim() !== '')
        : [];
        
    // Add initial serial number input
    const initialInput = document.createElement('div');
    initialInput.className = 'serial-number-input';
    initialInput.innerHTML = `
        <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number">
        <button type="button" class="btn btn-sm btn-secondary add-serial-number">
            <i class="fas fa-plus"></i> Add Another
        </button>
    `;
    editSerialNumbersContainer.appendChild(initialInput);
    
    // Add existing serial numbers
    if (validSerialNumbers.length > 0) {
        validSerialNumbers.forEach((serialNumber, index) => {
            if (index === 0) {
                // Use the first input we already created
                editSerialNumbersContainer.querySelector('input').value = serialNumber;
            } else {
                const newInput = document.createElement('div');
                newInput.className = 'serial-number-input';
                newInput.innerHTML = `
                    <input type="text" name="serial_numbers[]" class="form-control" placeholder="Enter serial number" value="${serialNumber}">
                    <button type="button" class="btn btn-sm btn-danger remove-serial-number">
                        <i class="fas fa-minus"></i> Remove
                    </button>
                `;
                editSerialNumbersContainer.appendChild(newInput);
            }
        });
    }
    
    // Add event listeners for the serial number buttons
    editSerialNumbersContainer.querySelectorAll('.add-serial-number').forEach(btn => {
        btn.addEventListener('click', () => addSerialNumberInput(editSerialNumbersContainer));
    });
    
    editSerialNumbersContainer.querySelectorAll('.remove-serial-number').forEach(btn => {
        btn.addEventListener('click', function() {
            this.parentElement.remove();
        });
    });
    
    // Show current invoice if exists
    const currentInvoiceElement = document.getElementById('currentInvoice');
    if (warranty.invoice_path) {
        currentInvoiceElement.innerHTML = `
            <span class="text-success">
                <i class="fas fa-check-circle"></i> Current invoice: 
                <a href="${warranty.invoice_path}" target="_blank">View</a>
                (Upload a new file to replace)
            </span>
        `;
    } else {
        currentInvoiceElement.innerHTML = '<span>No invoice uploaded</span>';
    }
    
    // Show current manual if exists
    const currentManualElement = document.getElementById('currentManual');
    if (warranty.manual_path) {
        currentManualElement.innerHTML = `
            <span class="text-success">
                <i class="fas fa-check-circle"></i> Current manual: 
                <a href="${warranty.manual_path}" target="_blank">View</a>
                (Upload a new file to replace)
            </span>
        `;
    } else {
        currentManualElement.innerHTML = '<span>No manual uploaded</span>';
    }
    
    // Reset file input display
    document.getElementById('editFileName').textContent = '';
    
    // Show modal
    editModal.classList.add('active');
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

async function updateWarranty() {
    if (!currentWarrantyId) return;
    
    showLoading();
    
    const formData = new FormData(editWarrantyForm);
    
    // Get all serial numbers and add them to formData
    const serialNumbers = [];
    document.querySelectorAll('#editSerialNumbersContainer input[name="serial_numbers[]"]').forEach(input => {
        if (input.value.trim()) {
            serialNumbers.push(input.value.trim());
        }
    });
    
    // Remove the original array and add clean values
    formData.delete('serial_numbers[]');
    if (serialNumbers.length > 0) {
        serialNumbers.forEach(sn => formData.append('serial_numbers', sn));
    }
    
    try {
        const response = await fetch(`${API_URL}/${currentWarrantyId}`, {
            method: 'PUT',
            body: formData
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to update warranty');
        }
        
        showToast('Warranty updated successfully!', 'success');
        closeModals();
        loadWarranties();
    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error updating warranty:', error);
    } finally {
        hideLoading();
    }
}

async function deleteWarranty() {
    if (!currentWarrantyId) return;
    
    showLoading();
    
    try {
        const response = await fetch(`${API_URL}/${currentWarrantyId}`, {
            method: 'DELETE'
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Failed to delete warranty');
        }
        
        showToast('Warranty deleted successfully!', 'success');
        closeModals();
        loadWarranties();
    } catch (error) {
        showToast(error.message, 'error');
        console.error('Error deleting warranty:', error);
    } finally {
        hideLoading();
    }
}

// Form tab navigation variables
const formTabs = Array.from(document.querySelectorAll('.form-tab'));
const tabContents = Array.from(document.querySelectorAll('.tab-content'));
let currentTabIndex = 0;

// Initialize form tabs
function initFormTabs() {
    // Hide the submit button initially
    const submitButton = document.querySelector('button[type="submit"]');
    if (submitButton) {
        submitButton.style.display = 'none';
    }
    
    // Show/hide navigation buttons based on current tab
    updateNavigationButtons();
    
    // Add event listeners for tab navigation
    document.querySelector('.next-tab').addEventListener('click', () => {
        if (validateTab(currentTabIndex)) {
            switchToTab(currentTabIndex + 1);
        } else {
            showValidationErrors(currentTabIndex);
        }
    });
    
    document.querySelector('.prev-tab').addEventListener('click', () => {
        switchToTab(currentTabIndex - 1);
    });
    
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
    // Ensure index is within bounds
    if (index < 0 || index >= formTabs.length) return;
    
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

function applyFilters() {
    let filteredWarranties = [...warranties];
    
    // Apply search filter
    if (currentFilters.search) {
        filteredWarranties = filteredWarranties.filter(warranty => 
            warranty.product_name.toLowerCase().includes(currentFilters.search)
        );
    }
    
    // Apply status filter
    if (currentFilters.status !== 'all') {
        filteredWarranties = filteredWarranties.filter(warranty => {
            // We need to calculate the status if it's not already set
            if (!warranty.status) {
                const today = new Date();
                const expirationDate = new Date(warranty.expiration_date);
                const daysRemaining = Math.floor((expirationDate - today) / (1000 * 60 * 60 * 24));
                
                if (daysRemaining < 0) {
                    warranty.status = 'expired';
                } else if (daysRemaining < 30) {
                    warranty.status = 'expiring';
                } else {
                    warranty.status = 'active';
                }
            }
            
            return warranty.status === currentFilters.status;
        });
    }
    
    renderWarranties(filteredWarranties);
}

function exportWarranties() {
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
            } else if (daysRemaining < 30) {
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

// Function to switch between views
function switchView(viewType) {
    // Update current view
    currentView = viewType;
    
    // Update view buttons
    gridViewBtn.classList.toggle('active', viewType === 'grid');
    listViewBtn.classList.toggle('active', viewType === 'list');
    tableViewBtn.classList.toggle('active', viewType === 'table');
    
    // Update warranties list class
    warrantiesList.className = `warranties-list ${viewType}-view`;
    
    // Show/hide table header for table view
    if (tableViewHeader) {
        tableViewHeader.classList.toggle('visible', viewType === 'table');
    }
    
    // Re-render warranties with the new view
    renderWarranties();
    
    // Save view preference to localStorage
    localStorage.setItem('warrantyView', viewType);
}

// Load saved view preference
function loadViewPreference() {
    const savedView = localStorage.getItem('warrantyView');
    if (savedView) {
        switchView(savedView);
    }
}