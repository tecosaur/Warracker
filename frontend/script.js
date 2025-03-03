// DOM Elements
const warrantyForm = document.getElementById('warrantyForm');
const warrantiesList = document.getElementById('warrantiesList');
const refreshBtn = document.getElementById('refreshBtn');
const searchInput = document.getElementById('searchWarranties');
const fileInput = document.getElementById('invoice');
const fileName = document.getElementById('fileName');
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
fileInput.addEventListener('change', updateFileName);
document.getElementById('editInvoice').addEventListener('change', () => {
    updateFileName(null, 'editInvoice', 'editFileName');
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
                ${warranty.invoice_path ? `
                    <div>
                        <a href="${warranty.invoice_path}" class="invoice-link" target="_blank">
                            <i class="fas fa-file-invoice"></i> View Invoice
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