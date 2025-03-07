// DOM Elements
const warrantyForm = document.getElementById('warrantyForm');
const settingsBtn = document.getElementById('settingsBtn');
const settingsMenu = document.getElementById('settingsMenu');
const darkModeToggle = document.getElementById('darkModeToggle');

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

const warrantiesList = document.getElementById('warrantiesList');
const refreshBtn = document.getElementById('refreshBtn');
const searchInput = document.getElementById('searchWarranties');
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

// Variables
let warranties = [];
let currentWarrantyId = null;

// API URL
const API_URL = '/api/warranties'; //  CORRECTED API_URL (relative URL)

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

// Search input
searchInput.addEventListener('input', filterWarranties);

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
    
    // Sort warranties: expiring soon first, then active, then expired
    warrantiesToRender.sort((a, b) => {
        const dateA = new Date(a.expiration_date);
        const dateB = new Date(b.expiration_date);
        
        const isExpiredA = dateA < today;
        const isExpiredB = dateB < today;
        
        if (isExpiredA && !isExpiredB) return 1;
        if (!isExpiredA && isExpiredB) return -1;
        
        // Both active or both expired, sort by date
        return dateA - dateB;
    });
    
    warrantiesToRender.forEach(warranty => {
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
        
        // Make sure serial numbers array exists and is valid
        const validSerialNumbers = Array.isArray(warranty.serial_numbers) 
            ? warranty.serial_numbers.filter(sn => sn && typeof sn === 'string' && sn.trim() !== '')
            : [];
        
        const cardElement = document.createElement('div');
        cardElement.className = `warranty-card ${statusClass === 'expired' ? 'expired' : statusClass === 'expiring' ? 'expiring-soon' : ''}`;
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
                <span class="warranty-status status-${statusClass}">${statusText}</span>
                ${validSerialNumbers.length > 0 ? `
                    <div class="serial-numbers">
                        <strong>Serial Numbers:</strong>
                        <ul>
                            ${validSerialNumbers.map(sn => `<li>${sn}</li>`).join('')}
                        </ul>
                    </div>
                ` : ''}
                ${warranty.invoice_path ? `
                    <div class="document-link-container">
                        <a href="${warranty.invoice_path}" class="invoice-link" target="_blank">
                            <i class="fas fa-file-invoice"></i> View Invoice
                        </a>
                    </div>
                ` : ''}
                ${warranty.manual_path ? `
                    <div class="document-link-container">
                        <a href="${warranty.manual_path}" class="manual-link" target="_blank">
                            <i class="fas fa-book"></i> View Manual
                        </a>
                    </div>
                ` : ''}
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
    document.getElementById('editWarrantyId').value = warranty.id;
    document.getElementById('editProductName').value = warranty.product_name;
    document.getElementById('editPurchaseDate').value = new Date(warranty.purchase_date).toISOString().split('T')[0];
    document.getElementById('editWarrantyYears').value = warranty.warranty_years;
    
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