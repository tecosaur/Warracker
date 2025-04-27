// Global variables
let warranties = [];
let currentTabIndex = 0;
let tabContents = []; // Initialize as empty array
let editMode = false;
let currentWarrantyId = null;
let currentFilters = {
    status: 'all',
    tag: 'all',
    search: '',
    sortBy: 'expiration'
};

// Tag related variables
let allTags = [];
let selectedTags = []; // Will hold objects with id, name, color

// Global variable for edit mode tags
let editSelectedTags = [];

// DOM Elements
const warrantyForm = document.getElementById('warrantyForm');
const settingsBtn = document.getElementById('settingsBtn');
const settingsMenu = document.getElementById('settingsMenu');
const darkModeToggle = document.getElementById('darkModeToggle');
const warrantiesList = document.getElementById('warrantiesList');
const refreshBtn = document.getElementById('refreshBtn');
const searchInput = document.getElementById('searchWarranties');
const clearSearchBtn = document.getElementById('clearSearch');
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

// CSV Import Elements
const importBtn = document.getElementById('importBtn');
const csvFileInput = document.getElementById('csvFileInput');
if (importBtn) {
    importBtn.classList.remove('import-btn');
    importBtn.classList.add('export-btn');
}

// Tag DOM Elements
const selectedTagsContainer = document.getElementById('selectedTags');
const tagSearch = document.getElementById('tagSearch');
const tagsList = document.getElementById('tagsList');
const manageTagsBtn = document.getElementById('manageTagsBtn');
const tagManagementModal = document.getElementById('tagManagementModal');
const newTagForm = document.getElementById('newTagForm');
const existingTagsContainer = document.getElementById('existingTags');

// --- Add near other DOM Element declarations ---
const isLifetimeCheckbox = document.getElementById('isLifetime');
const warrantyYearsGroup = document.getElementById('warrantyYearsGroup');
const warrantyYearsInput = document.getElementById('warrantyYears');
const editIsLifetimeCheckbox = document.getElementById('editIsLifetime');
const editWarrantyYearsGroup = document.getElementById('editWarrantyYearsGroup');
const editWarrantyYearsInput = document.getElementById('editWarrantyYears');

// Add near other DOM Element declarations
const showAddWarrantyBtn = document.getElementById('showAddWarrantyBtn');
const addWarrantyModal = document.getElementById('addWarrantyModal');

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

// Theme Management - Simplified
function setTheme(isDark) {
    const theme = isDark ? 'dark' : 'light';
    console.log('Setting theme to:', theme);
    
    // 1. Apply theme attribute to document root
    document.documentElement.setAttribute('data-theme', theme);
        
    // 2. Save the single source of truth to localStorage
    localStorage.setItem('darkMode', isDark);
    
    // Update toggle state if the toggle exists on this page (e.g., in the header)
    const headerToggle = document.getElementById('darkModeToggle'); 
    if (headerToggle) {
        headerToggle.checked = isDark;
    }
}

// Initialization logic on DOMContentLoaded
document.addEventListener('DOMContentLoaded', function() {
    // ... other initialization ...

    // REMOVE call to undefined checkLoginStatus - Handled by auth.js
    // checkLoginStatus(); 
    
    // Load warranties (assuming warrantiesList exists on this page)
    if (document.getElementById('warrantiesList')) {
        loadWarranties();
    }

    // Setup form submission (assuming addWarrantyForm exists)
    const form = document.getElementById('addWarrantyForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
        // Initialize form tabs if the form exists
        initFormTabs(); 
    }

    // REMOVED setupSettingsMenu - Handled by auth.js
    // setupSettingsMenu();
    
    // Initialize theme toggle state *after* DOM is loaded
    // ... (theme toggle init logic) ...
    
    // Setup view switcher (assuming view switcher elements exist)
    if (document.getElementById('gridViewBtn')) {
        // setupViewSwitcher(); // Removed undefined function
        loadViewPreference();
    }
    
    // Setup filter controls (assuming filter controls exist)
    if (document.getElementById('filterControls')) {
        // setupFilterControls(); // Removed: function not defined
        populateTagFilter();
    }
        
    // Initialize modal interactions
    // initializeModals(); // Removed: function not defined, handled by setupModalTriggers
    setupModalTriggers();
    
    // Initialize Tag functionality (assuming tag elements exist)
    if (document.getElementById('tagSearchInput')) {
        initTagFunctionality();
        loadTags();
    }
    
    // Initialize form-specific lifetime checkbox handler
    const lifetimeCheckbox = document.getElementById('isLifetime');
    if (lifetimeCheckbox) {
        lifetimeCheckbox.addEventListener('change', handleLifetimeChange);
        handleLifetimeChange({ target: lifetimeCheckbox }); // Initial check
    }

    updateCurrencySymbols();
});

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

// Variables
let currentView = 'grid'; // Default view
let expiringSoonDays = 30; // Default value, will be updated from user preferences

// API URL
const API_URL = '/api/warranties';

// Form tab navigation variables (simplified)
let formTabs = []; // Changed from const to let, initialized as empty
// Removed const formTabsElements = document.querySelectorAll('.form-tab');
// Removed const formTabs = formTabsElements ? Array.from(formTabsElements) : [];
// Removed const tabContentsElements = document.querySelectorAll('.tab-content');
// Removed tabContents assignment here

const nextButton = document.querySelector('.next-tab'); // Keep these if needed globally, otherwise might remove
const prevButton = document.querySelector('.prev-tab'); // Keep these if needed globally, otherwise might remove

// --- Add near other DOM Element declarations ---
// ... existing code ...

// Initialize form tabs
function initFormTabs() {
    console.log('Initializing form tabs...');
    // Use the modal context if available, otherwise query document
    const modalContext = document.getElementById('addWarrantyModal'); // Assuming this is the context
    const context = modalContext && modalContext.classList.contains('active') ? modalContext : document;

    const tabsContainer = context.querySelector('.form-tabs');
    // Re-query tabContents and formTabs within the correct context and update global variables
    const contentsElements = context.querySelectorAll('.tab-content');
    tabContents = contentsElements ? Array.from(contentsElements) : []; // Update global variable

    const tabsElements = tabsContainer ? tabsContainer.querySelectorAll('.form-tab') : [];
    formTabs = tabsElements ? Array.from(tabsElements) : []; // Update global variable

    const nextButton = context.querySelector('#nextTabBtn'); // Use context
    const prevButton = context.querySelector('#prevTabBtn'); // Use context
    const submitButton = context.querySelector('#submitWarrantyBtn'); // Use context

    // Use the updated global variables length for checks
    if (!tabsContainer || !tabContents.length || !formTabs.length || !nextButton || !prevButton || !submitButton) {
        console.warn('Form tab elements not found in the expected context. Skipping tab initialization.');
        return; // Don't proceed if elements aren't present
    }

    // Remove the local 'tabs' and 'contents' variables, use global ones now
    // let currentTabIndex = 0; // Already global
    // const tabs = tabsContainer.querySelectorAll('.form-tab'); // Use global formTabs
    // const contents = document.querySelectorAll('.tab-content'); // Use global tabContents

    // Remove the inner switchToTab and updateNavigationButtons functions as they are defined globally
    /*
    function switchToTab(index) {
        // ... removed inner function ...
    }

    function updateNavigationButtons() {
        // ... removed inner function ...
    }
    */

    // --- CLONE AND REPLACE NAV BUTTONS TO REMOVE OLD LISTENERS ---
    // Ensure buttons exist before cloning
    let nextButtonCloned = nextButton;
    let prevButtonCloned = prevButton;
    if (nextButton && prevButton) {
        nextButtonCloned = nextButton.cloneNode(true);
        prevButtonCloned = prevButton.cloneNode(true);
        nextButton.parentNode.replaceChild(nextButtonCloned, nextButton);
        prevButton.parentNode.replaceChild(prevButtonCloned, prevButton);
    } else {
        console.warn("Next/Prev buttons not found for cloning listeners.");
    }


    // ... (rest of initFormTabs, including event listeners, ensure element checks)
    // Make sure event listeners use the correct global functions and variables
    formTabs.forEach((tab, index) => { // Use global formTabs
        if (tab) { // Check if tab exists
            tab.addEventListener('click', () => {
                // Allow clicking only on previous tabs if valid, or current
                if (index < currentTabIndex) {
                    let canSwitch = true;
                    for (let i = 0; i < index; i++) {
                        // Ensure validateTab uses the correct global tabContents
                        if (!validateTab(i)) {
                            canSwitch = false;
                            break;
                        }
                    }
                    if (canSwitch) switchToTab(index); // Call global function
                } else if (index === currentTabIndex) {
                    // Clicking current tab does nothing
                } else {
                    // Try to navigate forward by clicking tab
                    // Ensure validateTab uses the correct global tabContents
                    if (validateTab(currentTabIndex)) {
                        // Mark current as completed
                        if(formTabs[currentTabIndex]) formTabs[currentTabIndex].classList.add('completed'); // Use global formTabs
                        switchToTab(index); // Call global function
                    } else {
                         // If current tab is invalid, show errors for it
                         showValidationErrors(currentTabIndex);
                    }
                }
            });
        }
    });

    if (nextButtonCloned) { // Check button exists
        nextButtonCloned.addEventListener('click', () => {
            // Ensure validateTab uses the correct global tabContents
            if (validateTab(currentTabIndex)) {
                if (formTabs[currentTabIndex]) formTabs[currentTabIndex].classList.add('completed'); // Use global formTabs
                // Use global formTabs length
                if (currentTabIndex < formTabs.length - 1) { // <-- Ensure this uses formTabs.length
                    switchToTab(currentTabIndex + 1); // Call global function
                }
            } else {
                // If current tab is invalid, show errors
                showValidationErrors(currentTabIndex);
            }
        });
    } else {
         console.warn("Cloned Next button not found, listener not added.");
    }

    if (prevButtonCloned) { // Check button exists
        prevButtonCloned.addEventListener('click', () => {
            if (currentTabIndex > 0) {
                switchToTab(currentTabIndex - 1);
            }
        });
    }

    // Initialize the first tab
    switchToTab(0);
}

// Switch to a specific tab
function switchToTab(index) {
    console.log(`Switching to tab ${index} from tab ${currentTabIndex}`);
    
    // Ensure index is within bounds
    if (index < 0 || index >= formTabs.length) {
        console.log(`Invalid tab index: ${index}, not switching`);
        return;
    }
    
    // Update summary FIRST if switching TO the summary tab
    if (index === formTabs.length - 1) {
        updateSummary();
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
    const summaryProductName = document.getElementById('summary-product-name');
    if (summaryProductName) {
        summaryProductName.textContent = 
            document.getElementById('productName')?.value || '-';
    }
    
    const summaryProductUrl = document.getElementById('summary-product-url');
    if (summaryProductUrl) {
        summaryProductUrl.textContent = 
            document.getElementById('productUrl')?.value || '-';
    }
    
    // Serial numbers
    const serialNumbers = [];
    document.querySelectorAll('input[name="serial_numbers[]"]').forEach(input => {
        if (input && input.value && input.value.trim()) {
            serialNumbers.push(input.value.trim());
        }
    });
    
    const serialNumbersContainer = document.getElementById('summary-serial-numbers');
    if (serialNumbersContainer) {
        if (serialNumbers.length > 0) {
            serialNumbersContainer.innerHTML = '<ul>' + 
                serialNumbers.map(sn => `<li>${sn}</li>`).join('') + 
                '</ul>';
        } else {
            serialNumbersContainer.textContent = 'None';
        }
    }
    
    // Warranty details
    const purchaseDate = document.getElementById('purchaseDate')?.value;
    const summaryPurchaseDate = document.getElementById('summary-purchase-date');
    if (summaryPurchaseDate) {
        summaryPurchaseDate.textContent = purchaseDate ? 
            new Date(purchaseDate).toLocaleDateString() : '-';
    }
    
    // --- Handle Lifetime in Summary ---
    const isLifetime = isLifetimeCheckbox ? isLifetimeCheckbox.checked : false;
    const warrantyYears = warrantyYearsInput ? warrantyYearsInput.value : null;
    const summaryWarrantyYears = document.getElementById('summary-warranty-years');

    if (summaryWarrantyYears) {
        if (isLifetime) {
            summaryWarrantyYears.textContent = 'Lifetime';
        } else if (warrantyYears) {
            const yearsNum = parseFloat(warrantyYears);
            summaryWarrantyYears.textContent = `${yearsNum} ${yearsNum === 1 ? 'year' : 'years'}`;
        } else {
            summaryWarrantyYears.textContent = '-';
        }
    }
    
    // Calculate and display expiration date
    const summaryExpirationDate = document.getElementById('summary-expiration-date');
    if (summaryExpirationDate && purchaseDate && warrantyYears) {
        const expirationDate = new Date(purchaseDate);
        const yearsNum = parseFloat(warrantyYears);
        if (!isNaN(yearsNum)) {
            expirationDate.setFullYear(expirationDate.getFullYear() + Math.floor(yearsNum));
            expirationDate.setMonth(expirationDate.getMonth() + Math.round((yearsNum % 1) * 12));
            summaryExpirationDate.textContent = expirationDate.toLocaleDateString();
        } else {
            summaryExpirationDate.textContent = '-';
        }
    } else if (summaryExpirationDate) {
        summaryExpirationDate.textContent = '-';
    }
    
    // Purchase price
    const purchasePrice = document.getElementById('purchasePrice')?.value;
    const summaryPurchasePrice = document.getElementById('summary-purchase-price');
    if (summaryPurchasePrice) {
        summaryPurchasePrice.textContent = purchasePrice ? 
            `$${parseFloat(purchasePrice).toFixed(2)}` : 'Not specified';
    }
    
    // Documents
    const invoiceFile = document.getElementById('invoice')?.files[0];
    const summaryInvoice = document.getElementById('summary-invoice');
    if (summaryInvoice) {
        summaryInvoice.textContent = invoiceFile ? 
            invoiceFile.name : 'No file selected';
    }
    
    const manualFile = document.getElementById('manual')?.files[0];
    const summaryManual = document.getElementById('summary-manual');
    if (summaryManual) {
        summaryManual.textContent = manualFile ? 
            manualFile.name : 'No file selected';
    }
    
    // Tags
    const summaryTags = document.getElementById('summary-tags');
    if (summaryTags) {
        if (selectedTags && selectedTags.length > 0) {
            summaryTags.innerHTML = '';
            
            selectedTags.forEach(tag => {
                const tagElement = document.createElement('span');
                tagElement.className = 'tag';
                tagElement.style.backgroundColor = tag.color;
                tagElement.style.color = getContrastColor(tag.color);
                tagElement.textContent = tag.name;
                
                summaryTags.appendChild(tagElement);
            });
        } else {
            summaryTags.textContent = 'No tags selected';
        }
    }
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
        const searchTerm = currentFilters.search.toLowerCase();
        warrantiesToExport = warrantiesToExport.filter(warranty => {
            // Check if product name contains search term
            const productNameMatch = warranty.product_name.toLowerCase().includes(searchTerm);
            
            // Check if any tag name contains search term
            const tagMatch = warranty.tags && Array.isArray(warranty.tags) && 
                warranty.tags.some(tag => tag.name.toLowerCase().includes(searchTerm));
            
            // Return true if either product name or tag name matches
            return productNameMatch || tagMatch;
        });
    }
    
    if (currentFilters.status !== 'all') {
        warrantiesToExport = warrantiesToExport.filter(warranty => 
            warranty.status === currentFilters.status
        );
    }
    
    // Apply tag filter
    if (currentFilters.tag !== 'all') {
        const tagId = parseInt(currentFilters.tag);
        warrantiesToExport = warrantiesToExport.filter(warranty => 
            warranty.tags && Array.isArray(warranty.tags) &&
            warranty.tags.some(tag => tag.id === tagId)
        );
    }
    
    // Create CSV content
    let csvContent = "data:text/csv;charset=utf-8,";
    
    // Add headers
    csvContent += "Product Name,Purchase Date,Warranty Period,Expiration Date,Status,Serial Numbers,Tags\n";
    
    // Add data rows
    warrantiesToExport.forEach(warranty => {
        // Format serial numbers as comma-separated string
        const serialNumbers = Array.isArray(warranty.serial_numbers) 
            ? warranty.serial_numbers.filter(s => s).join(', ')
            : '';
        
        // Format tags as comma-separated string
        const tags = Array.isArray(warranty.tags)
            ? warranty.tags.map(tag => tag.name).join(', ')
            : '';
        
        // Format row data
        const row = [
            warranty.product_name || '',
            formatDate(new Date(warranty.purchase_date)),
            `${warranty.warranty_years || 0} ${warranty.warranty_years === 1 ? 'year' : 'years'}`,
            formatDate(new Date(warranty.expiration_date)),
            warranty.status || '',
            serialNumbers,
            tags
        ];
        
        // Add row to CSV content
        csvContent += row.map(field => `"${field.toString().replace(/"/g, '""')}"`).join(',') + '\n';
    });
    
    // Create a download link
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', `warranties_export_${formatDate(new Date())}.csv`);
    document.body.appendChild(link);
    
    // Trigger download
    link.click();
    
    // Clean up
    document.body.removeChild(link);
    
    // Show success notification
    showToast('Warranties exported successfully', 'success');
}

// Switch view of warranties list
function switchView(viewType) {
    console.log(`Switching to view: ${viewType}`);
    currentView = viewType;

    // Get the appropriate key prefix based on user type
    const prefix = getPreferenceKeyPrefix();
    // --- BEGIN EDIT: Save to all relevant keys ---
    localStorage.setItem(`${prefix}viewPreference`, viewType); // Keep this one
    localStorage.setItem(`${prefix}defaultView`, viewType);    // Add for consistency with settings load priority
    localStorage.setItem(`${prefix}warrantyView`, viewType);   // Add for consistency with settings legacy save
    localStorage.setItem('viewPreference', viewType);         // Keep general key
    // --- END EDIT ---

    // Make sure warrantiesList exists before modifying classes
    if (warrantiesList) {
        warrantiesList.classList.remove('grid-view', 'list-view', 'table-view');
        warrantiesList.classList.add(`${viewType}-view`);
    }

    // Make sure view buttons exist
    if (gridViewBtn && listViewBtn && tableViewBtn) {
        gridViewBtn.classList.remove('active');
        listViewBtn.classList.remove('active');
        tableViewBtn.classList.remove('active');
    }
    
    // Make sure the specific button exists
    if (viewType === 'grid' && gridViewBtn) gridViewBtn.classList.add('active');
    if (viewType === 'list' && listViewBtn) listViewBtn.classList.add('active');
    if (viewType === 'table' && tableViewBtn) tableViewBtn.classList.add('active');

    // Show/hide table header only if it exists
    if (tableViewHeader) {
        tableViewHeader.classList.toggle('visible', viewType === 'table');
    }

    // Re-render warranties only if warrantiesList exists
    if (warrantiesList) {
        renderWarranties(filterWarranties());
    }
}

// Load view preference from localStorage
function loadViewPreference() {
    // Get the appropriate key prefix based on user type
    const prefix = getPreferenceKeyPrefix();
    let savedView = null;

    // --- BEGIN EDIT: Check keys in priority order ---
    const userSpecificView = localStorage.getItem(`${prefix}defaultView`);
    const generalView = localStorage.getItem('viewPreference');
    const legacyWarrantyView = localStorage.getItem(`${prefix}warrantyView`);

    if (userSpecificView) {
        savedView = userSpecificView;
        console.log(`Loaded view preference from ${prefix}defaultView:`, savedView);
    } else if (generalView) {
        savedView = generalView;
        console.log('Loaded view preference from viewPreference:', savedView);
    } else if (legacyWarrantyView) {
        savedView = legacyWarrantyView;
        console.log(`Loaded view preference from legacy ${prefix}warrantyView:`, savedView);
    }
    // --- END EDIT ---

    // Default to grid view if no preference is saved
    savedView = savedView || 'grid';

    console.log(`Applying view preference: ${savedView}`);
    // Switch view only if view buttons exist (implying it's the main page)
    if (gridViewBtn || listViewBtn || tableViewBtn) {
        switchView(savedView);
    }
}

// Dark mode toggle
if (darkModeToggle) { // Add check for darkModeToggle
    darkModeToggle.addEventListener('change', (e) => {
        setTheme(e.target.checked);
    });
}

// Add event listener for adding new serial number inputs
// Add check for serialNumbersContainer before adding listener
if (serialNumbersContainer) {
    serialNumbersContainer.addEventListener('click', (e) => {
        if (e.target.closest('.add-serial-number')) {
            addSerialNumberInput();
        }
    });
}

// Add a serial number input field
function addSerialNumberInput(container = serialNumbersContainer) {
    // Check if the container exists before proceeding
    if (!container) {
        console.warn('Serial numbers container not found, cannot add input.');
        return;
    }

    const div = document.createElement('div');
    div.className = 'serial-number-input d-flex mb-2';
    
    // Create an input element
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'form-control';
    input.name = 'serial_numbers[]';
    input.placeholder = 'Enter serial number';
    
    // Check if this is the first serial number input
    const isFirstInput = container.querySelectorAll('.serial-number-input').length === 0;
    
    // Append input to the input group
    div.appendChild(input);
    
    // Only add remove button if this is not the first input
    if (!isFirstInput) {
        // Create a remove button
        const removeButton = document.createElement('button');
        removeButton.type = 'button';
        removeButton.className = 'btn btn-sm btn-danger remove-serial';
        removeButton.innerHTML = '<i class="fas fa-times"></i>';
        
        // Add event listener to remove button
        removeButton.addEventListener('click', function() {
            container.removeChild(div);
        });
        
        // Append remove button to the input group
        div.appendChild(removeButton);
    }
    
    // Insert the new input group before the add button
    const addButton = container.querySelector('.add-serial');
    if (addButton) {
        container.insertBefore(div, addButton);
    } else {
        container.appendChild(div);
        
        // Create and append an add button if it doesn't exist
        const addButton = document.createElement('button');
        addButton.type = 'button';
        addButton.className = 'btn btn-sm btn-secondary add-serial';
        addButton.innerHTML = '<i class="fas fa-plus"></i> Add Serial Number';
        
        addButton.addEventListener('click', function() {
            addSerialNumberInput(container);
        });
        
        container.appendChild(addButton);
    }
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

// Update file name display when a file is selected
function updateFileName(event, inputId = 'invoice', outputId = 'fileName') {
    const input = event ? event.target : document.getElementById(inputId);
    const output = document.getElementById(outputId);
    
    if (!input || !output) return;
    
    if (input.files && input.files[0]) {
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
    today.setHours(0, 0, 0, 0); // Normalize today to midnight for accurate date comparisons

    processedWarranty.purchaseDate = processedWarranty.purchase_date ? new Date(processedWarranty.purchase_date) : null;
    processedWarranty.expirationDate = processedWarranty.expiration_date ? new Date(processedWarranty.expiration_date) : null;

    // --- Lifetime Handling ---
    if (processedWarranty.is_lifetime) {
        processedWarranty.status = 'active';
        processedWarranty.statusText = 'Lifetime';
        processedWarranty.daysRemaining = Infinity;
    } else if (processedWarranty.expirationDate && !isNaN(processedWarranty.expirationDate.getTime())) {
        // Existing logic for dated warranties
        const expirationDateOnly = new Date(processedWarranty.expirationDate);
        expirationDateOnly.setHours(0,0,0,0);

        const timeDiff = expirationDateOnly - today;
        const daysRemaining = Math.ceil(timeDiff / (1000 * 60 * 60 * 24));
        processedWarranty.daysRemaining = daysRemaining;

        if (daysRemaining < 0) {
            processedWarranty.status = 'expired';
            processedWarranty.statusText = 'Expired';
        } else if (daysRemaining < expiringSoonDays) {
            processedWarranty.status = 'expiring';
            processedWarranty.statusText = `Expiring Soon (${daysRemaining} day${daysRemaining !== 1 ? 's' : ''})`;
        } else {
            processedWarranty.status = 'active';
            processedWarranty.statusText = `${daysRemaining} day${daysRemaining !== 1 ? 's' : ''} remaining`;
        }
    } else {
        processedWarranty.status = 'unknown';
        processedWarranty.statusText = 'Unknown Status';
        processedWarranty.daysRemaining = null;
    }

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
            
            // Populate tag filter dropdown with tags from warranties
            populateTagFilter();
            
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
    const symbol = getCurrencySymbol(); // Get the correct symbol HERE
    
    warrantiesList.innerHTML = '';
    
    // Apply sorting based on current sort selection
    const sortedWarranties = [...warrantiesToRender].sort((a, b) => {
        switch (currentFilters.sortBy) {
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
        // --- Use processed data ---
        const purchaseDate = warranty.purchaseDate;
        const expirationDate = warranty.expirationDate;
        const isLifetime = warranty.is_lifetime;
        const statusClass = warranty.status || 'unknown';
        const statusText = warranty.statusText || 'Unknown Status';
        const warrantyYearsText = isLifetime ? 'Lifetime' : (warranty.warranty_years !== undefined ? `${warranty.warranty_years} ${warranty.warranty_years === 1 ? 'year' : 'years'}` : 'N/A');
        const expirationDateText = isLifetime ? 'Lifetime' : formatDate(expirationDate);
        // Make sure serial numbers array exists and is valid
        const validSerialNumbers = Array.isArray(warranty.serial_numbers) 
            ? warranty.serial_numbers.filter(sn => sn && typeof sn === 'string' && sn.trim() !== '')
            : [];
        // Prepare tags HTML
        const tagsHtml = warranty.tags && warranty.tags.length > 0 
            ? `<div class="tags-row">
                ${warranty.tags.map(tag => 
                    `<span class="tag" style="background-color: ${tag.color}; color: ${getContrastColor(tag.color)}">
                        ${tag.name}
                    </span>`
                ).join('')}
              </div>`
            : '';
        // Add notes display button if present
        let notesHtml = '';
        const hasNotes = warranty.notes && warranty.notes.trim() !== '';
        // Remove the button, and instead prepare a notes link for document-links-row
        let notesLinkHtml = '';
        if (hasNotes) {
            notesLinkHtml = `<a href="#" class="notes-link" data-id="${warranty.id}" title="View Notes"><i class='fas fa-sticky-note'></i> Notes</a>`;
        }
        
        const cardElement = document.createElement('div');
        cardElement.className = `warranty-card ${statusClass === 'expired' ? 'expired' : statusClass === 'expiring' ? 'expiring-soon' : 'active'}`;
        
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
                        <div>Warranty: <span>${warrantyYearsText}</span></div>
                        <div>Expires: <span>${expirationDateText}</span></div>
                        ${warranty.purchase_price ? `<div><span>Price: </span><span class="currency-symbol">${symbol}</span><span>${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
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
                    <div class="document-links-inner-container">
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
                        ${notesLinkHtml}
                    </div>
                </div>
                ${tagsHtml}
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
                        <div>Warranty: <span>${warrantyYearsText}</span></div>
                        <div>Expires: <span>${expirationDateText}</span></div>
                        ${warranty.purchase_price ? `<div><span>Price: </span><span class="currency-symbol">${symbol}</span><span>${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
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
                    <div class="document-links-inner-container">
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
                        ${notesLinkHtml}
                    </div>
                </div>
                ${tagsHtml}
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
                        <div>Expires: <span>${expirationDateText}</span></div>
                    </div>
                </div>
                <div class="warranty-status-row status-${statusClass}">
                    <span>${statusText}</span>
                </div>
                <div class="document-links-row">
                    <div class="document-links-inner-container">
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
                        ${notesLinkHtml}
                    </div>
                </div>
                ${tagsHtml}
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
            openDeleteModal(warranty.id, warranty.product_name);
        });
        // View notes button event listener
        const notesLink = cardElement.querySelector('.notes-link');
        if (notesLink) {
            notesLink.addEventListener('click', (e) => {
                e.preventDefault();
                showNotesModal(warranty.notes, warranty);
            });
        }
    });
}

function filterWarranties() {
    const searchTerm = searchInput ? searchInput.value.toLowerCase() : ''; // Add null check for searchInput

    // Show or hide the clear search button if it exists
    if (clearSearchBtn) {
        clearSearchBtn.style.display = searchTerm ? 'flex' : 'none';
    }

    if (!searchTerm) {
        return warranties; // Return the full list if no search term
        // REMOVED: renderWarranties(); 
        // REMOVED: return;
    }

    const filtered = warranties.filter(warranty => {
        // Check product name
        if (warranty.product_name && warranty.product_name.toLowerCase().includes(searchTerm)) { // Add null check
            return true;
        }

        // Check tags
        if (warranty.tags && Array.isArray(warranty.tags)) {
            if (warranty.tags.some(tag => tag.name && tag.name.toLowerCase().includes(searchTerm))) {
                return true;
            }
        }

        // Check notes
        if (warranty.notes && warranty.notes.toLowerCase().includes(searchTerm)) {
            return true;
        }

        return false;
    });

    // REMOVED: Add visual feedback if no results found
    // REMOVED: if (filtered.length === 0) {
    // REMOVED:     renderEmptyState(`No matches found for "${searchTerm}". Try a different search term.`);
    // REMOVED: } else {
    // REMOVED:     renderWarranties(filtered);
    // REMOVED: }

    return filtered; // Return the filtered list
}

function applyFilters() {
    console.log('Applying filters with:', currentFilters);
    
    // Filter warranties based on currentFilters
    const filtered = warranties.filter(warranty => {
        // Status filter
        if (currentFilters.status !== 'all' && warranty.status !== currentFilters.status) {
            return false;
        }
        
        // Tag filter
        if (currentFilters.tag !== 'all') {
            const tagId = parseInt(currentFilters.tag);
            const hasTag = warranty.tags && Array.isArray(warranty.tags) &&
                warranty.tags.some(tag => tag.id === tagId);
            if (!hasTag) {
                return false;
            }
        }
        
        // Search filter
        if (currentFilters.search) {
            const searchTerm = currentFilters.search.toLowerCase();
            // Check if product name contains search term
            const productNameMatch = warranty.product_name.toLowerCase().includes(searchTerm);
            // Check if any tag name contains search term
            const tagMatch = warranty.tags && Array.isArray(warranty.tags) && 
                warranty.tags.some(tag => tag.name.toLowerCase().includes(searchTerm));
            // Check if notes contains search term
            const notesMatch = warranty.notes && warranty.notes.toLowerCase().includes(searchTerm);
            // Return true if any match
            if (!productNameMatch && !tagMatch && !notesMatch) {
                return false;
            }
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
        // Add the first serial number with an "Add Another" button only (no remove button)
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
    const deleteInvoiceBtn = document.getElementById('deleteInvoiceBtn');
    if (currentInvoiceElement && deleteInvoiceBtn) {
        if (warranty.invoice_path && warranty.invoice_path !== 'null') {
            currentInvoiceElement.innerHTML = `
                <span class="text-success">
                    <i class="fas fa-check-circle"></i> Current invoice: 
                    <a href="#" onclick="openSecureFile('${warranty.invoice_path}'); return false;">View</a>
                    (Upload a new file to replace)
                </span>
            `;
            deleteInvoiceBtn.style.display = '';
        } else {
            currentInvoiceElement.innerHTML = '<span>No invoice uploaded</span>';
            deleteInvoiceBtn.style.display = 'none';
        }
        // Reset delete state
        deleteInvoiceBtn.dataset.delete = 'false';
        deleteInvoiceBtn.onclick = function() {
            deleteInvoiceBtn.dataset.delete = 'true';
            currentInvoiceElement.innerHTML = '<span class="text-danger">Invoice will be deleted on save</span>';
            deleteInvoiceBtn.style.display = 'none';
        };
    }
    // Show current manual if exists
    const currentManualElement = document.getElementById('currentManual');
    const deleteManualBtn = document.getElementById('deleteManualBtn');
    if (currentManualElement && deleteManualBtn) {
        if (warranty.manual_path && warranty.manual_path !== 'null') {
            currentManualElement.innerHTML = `
                <span class="text-success">
                    <i class="fas fa-check-circle"></i> Current manual: 
                    <a href="#" onclick="openSecureFile('${warranty.manual_path}'); return false;">View</a>
                    (Upload a new file to replace)
                </span>
            `;
            deleteManualBtn.style.display = '';
        } else {
            currentManualElement.innerHTML = '<span>No manual uploaded</span>';
            deleteManualBtn.style.display = 'none';
        }
        // Reset delete state
        deleteManualBtn.dataset.delete = 'false';
        deleteManualBtn.onclick = function() {
            deleteManualBtn.dataset.delete = 'true';
            currentManualElement.innerHTML = '<span class="text-danger">Manual will be deleted on save</span>';
            deleteManualBtn.style.display = 'none';
        };
    }
    
    // Reset file inputs
    document.getElementById('editInvoice').value = '';
    document.getElementById('editManual').value = '';
    document.getElementById('editFileName').textContent = '';
    document.getElementById('editManualFileName').textContent = '';
    
    // Initialize file input event listeners
    const editInvoiceInput = document.getElementById('editInvoice');
    if (editInvoiceInput) {
        editInvoiceInput.addEventListener('change', function(event) {
            updateFileName(event, 'editInvoice', 'editFileName');
        });
    }
    
    const editManualInput = document.getElementById('editManual');
    if (editManualInput) {
        editManualInput.addEventListener('change', function(event) {
            updateFileName(event, 'editManual', 'editManualFileName');
        });
    }
    
    // Show edit modal
    const modalBackdrop = document.getElementById('editModal');
    if (modalBackdrop) {
        modalBackdrop.classList.add('active'); // Add active class to display as flex
    }
    
    // Reset tabs to first tab
    const editTabBtns = document.querySelectorAll('.edit-tab-btn');
    editTabBtns.forEach(btn => btn.classList.remove('active'));
    document.querySelector('.edit-tab-btn[data-tab="edit-product-info"]').classList.add('active');
    
    // Reset tab content
    document.querySelectorAll('.edit-tab-content').forEach(content => content.classList.remove('active'));
    document.getElementById('edit-product-info').classList.add('active');
    
    // Initialize edit mode tags
    editSelectedTags = [];
    
    // If warranty has tags, populate editSelectedTags
    if (warranty.tags && Array.isArray(warranty.tags)) {
        editSelectedTags = warranty.tags.map(tag => ({
            id: tag.id,
            name: tag.name,
            color: tag.color
        }));
    }
    
    // Render selected tags using the helper function
    renderEditSelectedTags();
    
    // Set up tag search in edit mode
    const editTagSearch = document.getElementById('editTagSearch');
    const editTagsList = document.getElementById('editTagsList');
    
    if (editTagSearch && editTagsList) {
        // Add event listeners for tag search
        editTagSearch.addEventListener('focus', () => {
            renderEditTagsList();
            editTagsList.classList.add('show');
        });
        
        editTagSearch.addEventListener('input', () => {
            renderEditTagsList(editTagSearch.value);
        });
        
        // Add event listener to close dropdown when clicking outside
        document.addEventListener('click', (e) => {
            if (!editTagSearch.contains(e.target) && !editTagsList.contains(e.target)) {
                editTagsList.classList.remove('show');
            }
        });
    }
    
    // Set up manage tags button in edit mode
    const editManageTagsBtn = document.getElementById('editManageTagsBtn');
    if (editManageTagsBtn) {
        editManageTagsBtn.addEventListener('click', (e) => {
            e.preventDefault();
            openTagManagementModal();
        });
    }
    
    // Validate all tabs to update completion indicators
    validateEditTab('edit-product-info');
    validateEditTab('edit-warranty-details');
    validateEditTab('edit-documents');
    validateEditTab('edit-tags');
    
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

    // --- Set Lifetime Checkbox and Toggle Years Input ---
    if (editIsLifetimeCheckbox && editWarrantyYearsGroup && editWarrantyYearsInput) {
        editIsLifetimeCheckbox.checked = warranty.is_lifetime || false;
        handleEditLifetimeChange(); // Call handler to set initial state

        // Remove previous listener if exists
        editIsLifetimeCheckbox.removeEventListener('change', handleEditLifetimeChange);
        // Add new listener
        editIsLifetimeCheckbox.addEventListener('change', handleEditLifetimeChange);

        // Set years value only if NOT lifetime
        editWarrantyYearsInput.value = warranty.is_lifetime ? '' : (warranty.warranty_years || '');
    } else {
        console.error("Lifetime warranty elements not found in edit form");
    }

    // Set notes
    const notesInput = document.getElementById('editNotes');
    if (notesInput) {
        notesInput.value = warranty.notes || '';
    }
}

function openDeleteModal(warrantyId, productName) {
    currentWarrantyId = warrantyId;
    
    const deleteProductNameElement = document.getElementById('deleteProductName');
    if (deleteProductNameElement) {
        deleteProductNameElement.textContent = productName || '';
    }
    
    const deleteModal = document.getElementById('deleteModal');
    if (deleteModal) {
        deleteModal.classList.add('active');
    }
}

// Function to close all modals
function closeModals() {
    document.querySelectorAll('.modal-backdrop').forEach(modal => {
        modal.classList.remove('active');
    });
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

// Submit form function - event handler for form submit
function submitForm(event) {
    event.preventDefault();
    
    // --- Add Lifetime Check ---
    if (!isLifetimeCheckbox.checked && (!warrantyYearsInput.value || parseFloat(warrantyYearsInput.value) <= 0)) {
        showToast('Warranty period (years) is required and must be greater than 0 unless it\'s a lifetime warranty', 'error');
        switchToTab(1); // Switch to warranty details tab
        warrantyYearsInput.focus();
        warrantyYearsInput.classList.add('invalid');
        return;
    }
    
    // Validate all tabs
    for (let i = 0; i < tabContents.length; i++) {
        if (!validateTab(i)) {
            // Switch to the first invalid tab
            switchToTab(i);
            return;
        }
    }
    
    // Create form data object
    const formData = new FormData(warrantyForm);
    
    // Add serial numbers to form data
    const serialInputs = document.querySelectorAll('#serialNumbersContainer input');
    serialInputs.forEach(input => {
        if (input.value.trim()) {
            formData.append('serial_numbers', input.value.trim());
        }
    });
    
    // Add tag IDs to form data as JSON string
    if (selectedTags && selectedTags.length > 0) {
        const tagIds = selectedTags.map(tag => tag.id);
        formData.append('tag_ids', JSON.stringify(tagIds));
    }
    
    // --- Ensure is_lifetime is correctly added ---
    if (!isLifetimeCheckbox.checked) {
        formData.append('is_lifetime', 'false');
    }
    
    // Show loading spinner
    showLoadingSpinner();
    
    // Send the form data to the server
    fetch('/api/warranties', {
        method: 'POST',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('auth_token')
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to add warranty');
            });
        }
        return response.json();
    })
    .then(data => {
        hideLoadingSpinner();
        showToast('Warranty added successfully', 'success');
        
        // --- Close and reset the modal on success ---
        if (addWarrantyModal) {
            addWarrantyModal.classList.remove('active');
        }
        resetAddWarrantyWizard(); // Reset the wizard form
        // --- End modification ---

        loadWarranties(); // Reload the list
    })
    .catch(error => {
        hideLoadingSpinner();
        console.error('Error adding warranty:', error);
        showToast(error.message || 'Failed to add warranty', 'error');
    });
}

// Initialize page
document.addEventListener('DOMContentLoaded', function() {
    // Initialize the warranty form *only* if the form element exists
    if (warrantyForm) {
        initWarrantyForm();
    }
    
    // Load warranties (might need checks if warrantiesList doesn't always exist)
    if (warrantiesList) { 
        loadWarranties();
        loadViewPreference(); // Load user's preferred view
        loadTags(); // Load tags for the form
        initTagFunctionality(); // Initialize tag search/selection
    }
    
    // Initialize theme (should be safe on all pages)
    initializeTheme();
    
    // Set up event listeners for other UI controls (should contain checks)
    setupUIEventListeners();
    setupModalTriggers(); // Add the new modal listeners
    
    // Check if user is logged in and update UI
    // checkLoginStatus(); // Removed undefined function
    
    // Setup form submission
    const form = document.getElementById('addWarrantyForm');
    if (form) {
        form.addEventListener('submit', handleFormSubmit);
    }
    
    // Setup settings menu toggle
    // setupSettingsMenu(); // Removed: function not defined, handled by auth.js
    
    // Initialize theme toggle state *after* DOM is loaded
    // Find the header toggle (assuming ID 'darkModeToggle')
    const headerToggle = document.getElementById('darkModeToggle'); 
    if (headerToggle) {
        // Set initial state based on theme applied by theme-loader.js
        const currentTheme = document.documentElement.getAttribute('data-theme');
        headerToggle.checked = currentTheme === 'dark';
        
        // Add listener to update theme when toggled
        headerToggle.addEventListener('change', function() {
            setTheme(this.checked);
        });
    }
    
    // REMOVE any direct calls to initializeTheme() from here or globally
    // initializeTheme(); 

    // Setup view switcher
    // setupViewSwitcher(); // Removed undefined function
    
    // Setup filter controls
    // setupFilterControls(); // Removed: function not defined
    
    // Setup form tabs and navigation
    // initFormTabs(); // <-- Remove this line from DOMContentLoaded
    
    // Initialize modal interactions
    // initializeModals(); // Removed: function not defined, handled by setupModalTriggers
    
    // Load preferences (if needed for things other than theme)
    // loadPreferences(); // Consider if needed

    updateCurrencySymbols();
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

// Initialize the warranty form and all its components
function initWarrantyForm() {
    // Initialize form tabs
    if (formTabs && tabContents) {
        initFormTabs();
    }
    
    // Initialize serial number inputs
    addSerialNumberInput();
    
    // Initialize file input display
    if (document.getElementById('invoice')) {
        document.getElementById('invoice').addEventListener('change', function(event) {
            updateFileName(event, 'invoice', 'fileName');
        });
    }
    
    if (document.getElementById('manual')) {
        document.getElementById('manual').addEventListener('change', function(event) {
            updateFileName(event, 'manual', 'manualFileName');
        });
    }
    
    // Initialize tag functionality
    initTagFunctionality();
    
    // Form submission
    if (warrantyForm) {
        warrantyForm.addEventListener('submit', submitForm);
    }

    // Initialize lifetime checkbox listener
    if (isLifetimeCheckbox && warrantyYearsGroup && warrantyYearsInput) {
        isLifetimeCheckbox.addEventListener('change', handleLifetimeChange);
        handleLifetimeChange(); // Initial check
    } else {
        console.error("Lifetime warranty elements not found in add form");
    }
}

// Initialize tag functionality
function initTagFunctionality() {
    // Skip if tag elements don't exist
    if (!tagSearch || !tagsList || !manageTagsBtn || !selectedTagsContainer) {
        console.log('Tag elements not found, skipping tag initialization');
        return;
    }

    // Load tags from API if not already loaded
    if (allTags.length === 0) {
        loadTags();
    }
    
    // Tag search input
    tagSearch.addEventListener('focus', () => {
        renderTagsList();
        tagsList.classList.add('show');
    });
    
    tagSearch.addEventListener('input', () => {
        renderTagsList(tagSearch.value);
    });
    
    document.addEventListener('click', (e) => {
        if (!tagSearch.contains(e.target) && !tagsList.contains(e.target)) {
            tagsList.classList.remove('show');
        }
    });
    
    // Manage tags button
    manageTagsBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openTagManagementModal();
    });
    
    // Tag management form
    if (newTagForm) {
        newTagForm.addEventListener('submit', (e) => {
            e.preventDefault();
            createNewTag();
        });
    }
    
    // Close modal buttons
    if (tagManagementModal) {
        const closeButtons = tagManagementModal.querySelectorAll('[data-dismiss="modal"]');
        closeButtons.forEach(button => {
            button.addEventListener('click', () => {
                tagManagementModal.style.display = 'none';
            });
        });
    }
}

// Function to load all tags
async function loadTags() {
    try {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.error('No auth token found');
            return;
        }
        
        showLoadingSpinner();
        
        const response = await fetch('/api/tags', {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to load tags: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Loaded tags:', data);
        
        // Store tags globally
        allTags = data;
        
        // Populate the tag filter
        populateTagFilter();
        
        // Render selected tags if any
        if (selectedTagsContainer) {
            renderSelectedTags();
        }
        
        hideLoadingSpinner();
        
        return data;
    } catch (error) {
        console.error('Error loading tags:', error);
        hideLoadingSpinner();
        return [];
    }
}

// Render the tags dropdown list
function renderTagsList(searchTerm = '') {
    if (!tagsList) return;
    
    tagsList.innerHTML = '';
    
    // Filter tags based on search term
    const filteredTags = allTags.filter(tag => 
        !searchTerm || tag.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    
    // Add option to create new tag if search term is provided and not in list
    if (searchTerm && !filteredTags.some(tag => tag.name.toLowerCase() === searchTerm.toLowerCase())) {
        const createOption = document.createElement('div');
        createOption.className = 'tag-option create-tag';
        createOption.innerHTML = `<i class="fas fa-plus"></i> Create "${searchTerm}"`;
        createOption.addEventListener('click', () => {
            createTag(searchTerm).then(newTag => {
                // Add the new tag to selectedTags
                selectedTags.push(newTag);
                renderSelectedTags();
                renderTagsList(''); // Clear search and refresh list
            });
            tagsList.classList.remove('show');
        });
        tagsList.appendChild(createOption);
    }
    
    // Add existing tags to dropdown
    filteredTags.forEach(tag => {
        const option = document.createElement('div');
        option.className = 'tag-option';
        
        // Check if tag is already selected
        const isSelected = selectedTags.some(selected => selected.id === tag.id);
        
        option.innerHTML = `
            <span class="tag-color" style="background-color: ${tag.color}"></span>
            ${tag.name}
            <span class="tag-status">${isSelected ? '<i class="fas fa-check"></i>' : ''}</span>
        `;
        
        option.addEventListener('click', () => {
            if (isSelected) {
                // Remove tag if already selected
                selectedTags = selectedTags.filter(selected => selected.id !== tag.id);
            } else {
                // Add tag if not selected
                selectedTags.push({
                    id: tag.id,
                    name: tag.name,
                    color: tag.color
                });
            }
            
            renderSelectedTags();
            renderTagsList(searchTerm);
        });
        
        tagsList.appendChild(option);
    });
    
    // Show the dropdown
    tagsList.classList.add('show');
}

// Update renderEditTagsList to add new tag to editSelectedTags after creation
function renderEditTagsList(searchTerm = '') {
    const editTagsList = document.getElementById('editTagsList');
    if (!editTagsList) return;
    editTagsList.innerHTML = '';
    // Filter tags based on search term
    const filteredTags = allTags.filter(tag => 
        !searchTerm || tag.name.toLowerCase().includes(searchTerm.toLowerCase())
    );
    // Add option to create new tag if search term is provided and not in list
    if (searchTerm && !filteredTags.some(tag => tag.name.toLowerCase() === searchTerm.toLowerCase())) {
        const createOption = document.createElement('div');
        createOption.className = 'tag-option create-tag';
        createOption.innerHTML = `<i class="fas fa-plus"></i> Create "${searchTerm}"`;
        createOption.addEventListener('click', () => {
            createTag(searchTerm).then(newTag => {
                // Add the new tag to editSelectedTags
                editSelectedTags.push(newTag);
                renderEditSelectedTags();
                renderEditTagsList(''); // Clear search and refresh list
            });
            editTagsList.classList.remove('show');
        });
        editTagsList.appendChild(createOption);
    }
    // Add existing tags to dropdown
    filteredTags.forEach(tag => {
        const option = document.createElement('div');
        option.className = 'tag-option';
        
        // Check if tag is already selected
        const isSelected = editSelectedTags.some(selected => selected.id === tag.id);
        
        option.innerHTML = `
            <span class="tag-color" style="background-color: ${tag.color}"></span>
            ${tag.name}
            <span class="tag-status">${isSelected ? '<i class="fas fa-check"></i>' : ''}</span>
        `;
        
        option.addEventListener('click', () => {
            if (isSelected) {
                // Remove tag if already selected
                editSelectedTags = editSelectedTags.filter(selected => selected.id !== tag.id);
            } else {
                // Add tag if not selected
                editSelectedTags.push({
                    id: tag.id,
                    name: tag.name,
                    color: tag.color
                });
            }
            
            // Use our helper function to render selected tags
            renderEditSelectedTags();
            
            renderEditTagsList(searchTerm);
        });
        
        editTagsList.appendChild(option);
    });
    
    // Show the dropdown
    editTagsList.classList.add('show');
}

// Render the selected tags
function renderSelectedTags() {
    if (!selectedTagsContainer) return;
    
    selectedTagsContainer.innerHTML = '';
    
    if (selectedTags.length === 0) {
        const placeholder = document.createElement('span');
        placeholder.className = 'no-tags-selected';
        placeholder.textContent = 'No tags selected';
        selectedTagsContainer.appendChild(placeholder);
        return;
    }
    
    selectedTags.forEach(tag => {
        const tagElement = document.createElement('span');
        tagElement.className = 'tag';
        tagElement.style.backgroundColor = tag.color;
        tagElement.style.color = getContrastColor(tag.color);
        
        tagElement.innerHTML = `
            ${tag.name}
            <span class="remove-tag" data-id="${tag.id}">&times;</span>
        `;
        
        // Add event listener for removing tag
        tagElement.querySelector('.remove-tag').addEventListener('click', (e) => {
            e.stopPropagation();
            selectedTags = selectedTags.filter(t => t.id !== tag.id);
            renderSelectedTags();
            
            // Update summary if needed
            if (document.getElementById('summary-tags')) {
                updateSummary();
            }
        });
        
        selectedTagsContainer.appendChild(tagElement);
    });
}

// Helper function to render the edit selected tags
function renderEditSelectedTags() {
    const editSelectedTagsContainer = document.getElementById('editSelectedTags');
    if (!editSelectedTagsContainer) return;
    
    editSelectedTagsContainer.innerHTML = '';
    
    if (editSelectedTags.length > 0) {
        editSelectedTags.forEach(tag => {
            const tagElement = document.createElement('span');
            tagElement.className = 'tag';
            tagElement.style.backgroundColor = tag.color;
            tagElement.style.color = getContrastColor(tag.color);
            
            tagElement.innerHTML = `
                ${tag.name}
                <span class="remove-tag" data-id="${tag.id}">&times;</span>
            `;
            
            // Add event listener for removing tag
            const removeButton = tagElement.querySelector('.remove-tag');
            removeButton.addEventListener('click', (e) => {
                e.stopPropagation();
                e.preventDefault(); // Add this to prevent default action
                
                // Prevent the event from bubbling up to parent elements
                if (e.cancelBubble !== undefined) {
                    e.cancelBubble = true;
                }
                
                editSelectedTags = editSelectedTags.filter(t => t.id !== tag.id);
                
                // Re-render just the tags
                renderEditSelectedTags();
                return false; // Add return false for older browsers
            });
            
            editSelectedTagsContainer.appendChild(tagElement);
        });
    } else {
        const placeholder = document.createElement('span');
        placeholder.className = 'no-tags-selected';
        placeholder.textContent = 'No tags selected';
        editSelectedTagsContainer.appendChild(placeholder);
    }
}

// Update createTag to return a Promise
function createTag(name) {
    return new Promise((resolve, reject) => {
        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.error('No authentication token found');
            reject(new Error('No authentication token found'));
            return;
        }
        // Generate a random color for the tag
        const color = '#' + Math.floor(Math.random()*16777215).toString(16).padStart(6, '0');
        fetch('/api/tags', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': 'Bearer ' + token
            },
            body: JSON.stringify({
                name: name,
                color: color
            })
        })
        .then(response => {
            if (!response.ok) {
                if (response.status === 409) {
                    reject(new Error('A tag with this name already exists'));
                    return;
                }
                reject(new Error('Failed to create tag'));
                return;
            }
            return response.json();
        })
        .then(data => {
            if (!data) return;
            const newTag = {
                id: data.id,
                name: data.name,
                color: data.color
            };
            allTags.push(newTag);
            renderExistingTags();
            populateTagFilter();
            showToast('Tag created successfully', 'success');
            resolve(newTag);
        })
        .catch(error => {
            console.error('Error creating tag:', error);
            showToast(error.message || 'Failed to create tag', 'error');
            reject(error);
        });
    });
}

// Helper function to determine text color based on background color
function getContrastColor(hexColor) {
    // Convert hex to RGB
    const r = parseInt(hexColor.substr(1, 2), 16);
    const g = parseInt(hexColor.substr(3, 2), 16);
    const b = parseInt(hexColor.substr(5, 2), 16);
    
    // Calculate luminance
    const yiq = ((r * 299) + (g * 587) + (b * 114)) / 1000;
    
    // Return black or white depending on luminance
    return (yiq >= 128) ? '#000000' : '#ffffff';
}

// Open tag management modal
function openTagManagementModal() {
    if (!tagManagementModal) return;
    
    // Populate existing tags
    renderExistingTags();
    
    // Show modal
    tagManagementModal.style.display = 'block';
}

// Render existing tags in the management modal
function renderExistingTags() {
    if (!existingTagsContainer) return;
    
    existingTagsContainer.innerHTML = '';
    
    if (allTags.length === 0) {
        existingTagsContainer.innerHTML = '<div class="no-tags">No tags created yet</div>';
        return;
    }
    
    allTags.forEach(tag => {
        const tagElement = document.createElement('div');
        tagElement.className = 'existing-tag';
        
        tagElement.innerHTML = `
            <div class="existing-tag-info">
                <div class="existing-tag-color" style="background-color: ${tag.color}"></div>
                <div class="existing-tag-name">${tag.name}</div>
            </div>
            <div class="existing-tag-actions">
                <button class="btn btn-sm btn-secondary edit-tag" data-id="${tag.id}">
                    <i class="fas fa-edit"></i>
                </button>
                <button class="btn btn-sm btn-danger delete-tag" data-id="${tag.id}">
                    <i class="fas fa-trash"></i>
                </button>
            </div>
        `;
        
        // Add event listeners for edit and delete
        tagElement.querySelector('.edit-tag').addEventListener('click', () => {
            editTag(tag);
        });
        
        tagElement.querySelector('.delete-tag').addEventListener('click', () => {
            deleteTag(tag.id);
        });
        
        existingTagsContainer.appendChild(tagElement);
    });
}

// Edit a tag
function editTag(tag) {
    const tagInfoElement = document.querySelector(`.existing-tag .existing-tag-info:has(+ .existing-tag-actions button[data-id="${tag.id}"])`);
    
    if (!tagInfoElement) {
        // Alternative selector for browsers that don't support :has
        const tagElement = document.querySelector(`.existing-tag`);
        const buttons = tagElement?.querySelectorAll(`.existing-tag-actions button[data-id="${tag.id}"]`);
        if (buttons?.length > 0) {
            const parent = buttons[0].closest('.existing-tag');
            if (parent) {
                const infoElement = parent.querySelector('.existing-tag-info');
                if (infoElement) {
                    tagInfoElement = infoElement;
                }
            }
        }
        
        if (!tagInfoElement) return;
    }
    
    const originalHTML = tagInfoElement.innerHTML;
    
    tagInfoElement.innerHTML = `
        <input type="text" class="form-control edit-tag-name" value="${tag.name}" style="width: 60%;">
        <input type="color" class="edit-tag-color" value="${tag.color}" style="width: 40px; height: 38px;">
        <button class="btn btn-sm btn-primary save-edit" data-id="${tag.id}">Save</button>
        <button class="btn btn-sm btn-secondary cancel-edit">Cancel</button>
    `;
    
    // Add event listeners
    tagInfoElement.querySelector('.save-edit').addEventListener('click', () => {
        const newName = tagInfoElement.querySelector('.edit-tag-name').value.trim();
        const newColor = tagInfoElement.querySelector('.edit-tag-color').value;
        
        if (!newName) {
            showToast('Tag name is required', 'error');
            return;
        }
        
        updateTag(tag.id, newName, newColor);
    });
    
    tagInfoElement.querySelector('.cancel-edit').addEventListener('click', () => {
        // Restore original HTML
        tagInfoElement.innerHTML = originalHTML;
    });
}

// Update a tag
function updateTag(id, name, color) {
    const token = localStorage.getItem('auth_token');
    if (!token) {
        console.error('No authentication token found');
        return;
    }
    
    fetch(`/api/tags/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': 'Bearer ' + token
        },
        body: JSON.stringify({
            name: name,
            color: color
        })
    })
    .then(response => {
        if (!response.ok) {
            if (response.status === 409) {
                throw new Error('A tag with this name already exists');
            }
            throw new Error('Failed to update tag');
        }
        return response.json();
    })
    .then(data => {
        // Update tag in allTags array
        const index = allTags.findIndex(tag => tag.id === id);
        if (index !== -1) {
            allTags[index].name = name;
            allTags[index].color = color;
        }
        
        // Update tag in selectedTags if present
        const selectedIndex = selectedTags.findIndex(tag => tag.id === id);
        if (selectedIndex !== -1) {
            selectedTags[selectedIndex].name = name;
            selectedTags[selectedIndex].color = color;
        }
        
        // Rerender existing tags and selected tags
        renderExistingTags();
        renderSelectedTags();
        
        // Update summary if needed
        if (document.getElementById('summary-tags')) {
            updateSummary();
        }
        
        showToast('Tag updated successfully', 'success');
    })
    .catch(error => {
        console.error('Error updating tag:', error);
        showToast(error.message || 'Failed to update tag', 'error');
    });
}

// Delete a tag
function deleteTag(id) {
    if (!confirm('Are you sure you want to delete this tag? It will be removed from all warranties.')) {
        return;
    }
    
    const token = localStorage.getItem('auth_token');
    if (!token) {
        console.error('No authentication token found');
        showToast('Authentication required', 'error'); // Added toast for better feedback
        return;
    }
    
    showLoadingSpinner(); // Show loading indicator
    
    fetch(`/api/tags/${id}`, { // Use the correct URL with tag ID
        method: 'DELETE', // Use DELETE method
        headers: {
            'Authorization': 'Bearer ' + token
        }
    })
    .then(response => {
        if (!response.ok) {
            // Log the status for debugging the 405 error
            console.error(`Failed to delete tag. Status: ${response.status} ${response.statusText}`);
            // Try to get error message from response body
            return response.json().then(errData => {
                throw new Error(errData.error || errData.message || 'Failed to delete tag');
            }).catch(() => {
                // If response body is not JSON or empty
                throw new Error(`Failed to delete tag. Status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        // Remove tag from allTags array
        allTags = allTags.filter(tag => tag.id !== id);
        
        // Remove tag from selectedTags if present (in both add and edit modes)
        selectedTags = selectedTags.filter(tag => tag.id !== id);
        editSelectedTags = editSelectedTags.filter(tag => tag.id !== id);
        
        // --- FIX: Re-render UI elements ---
        renderExistingTags(); // Update the list in the modal
        renderSelectedTags(); // Update selected tags in the add form
        renderEditSelectedTags(); // Update selected tags in the edit form
        populateTagFilter(); // Update the filter dropdown on the main page
        // --- END FIX ---
        
        showToast('Tag deleted successfully', 'success');
    })
    .catch(error => {
        console.error('Error deleting tag:', error);
        showToast(error.message || 'Failed to delete tag', 'error'); // Show specific error message
    })
    .finally(() => {
        hideLoadingSpinner(); // Hide loading indicator
    });
}

// Set up event listeners for UI controls
function setupUIEventListeners() {
    // Initialize edit tabs
    initEditTabs();
    
    // Close modals when clicking outside or on close button
    document.querySelectorAll('.modal-backdrop, [data-dismiss="modal"]').forEach(element => {
        element.addEventListener('click', (e) => {
            // Check if the click is on the backdrop itself OR a dismiss button
            if (e.target === element || e.target.matches('[data-dismiss="modal"]')) {
                // Find the closest modal backdrop to the element clicked
                const modalToClose = e.target.closest('.modal-backdrop');

                if (modalToClose) {
                    // *** MODIFIED CHECK ***
                    // If the click target is the backdrop itself (not a dismiss button)
                    // AND the modal is the 'addWarrantyModal', then DO NOTHING.
                    if (modalToClose.id === 'addWarrantyModal' && e.target === modalToClose) {
                        return; // Ignore backdrop click for addWarrantyModal
                    }
                    // *** END MODIFIED CHECK ***

                    // Otherwise, close the modal (handles other modals' backdrop clicks and all dismiss buttons)
                    modalToClose.classList.remove('active');

                    // Reset forms only when closing the respective modal
                    if (modalToClose.id === 'editModal') {
                        // Optional: Add any edit form reset logic here if needed
                        console.log('Edit modal closed, reset logic (if any) can go here.');
                    } else if (modalToClose.id === 'addWarrantyModal') {
                        // This reset will now only trigger if closed via dismiss button
                        resetAddWarrantyWizard();
                    }
                    // Add similar reset logic for other modals like deleteModal if needed
                    // else if (modalToClose.id === 'deleteModal') { ... }
                }
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
    const searchInput = document.getElementById('searchWarranties');
    const clearSearchBtn = document.getElementById('clearSearch');
    const statusFilter = document.getElementById('statusFilter');
    const tagFilter = document.getElementById('tagFilter');
    const sortBySelect = document.getElementById('sortBy');
    
    if (searchInput) {
        searchInput.addEventListener('input', () => {
            currentFilters.search = searchInput.value.toLowerCase();
            
            // Show/hide clear button based on search input
            if (clearSearchBtn) {
                clearSearchBtn.style.display = searchInput.value ? 'flex' : 'none';
            }
            
            // Add visual feedback class to search box when active
            if (searchInput.value) {
                searchInput.parentElement.classList.add('active-search');
            } else {
                searchInput.parentElement.classList.remove('active-search');
            }
            
            applyFilters();
        });
    }
    
    if (clearSearchBtn) {
        clearSearchBtn.addEventListener('click', () => {
            if (searchInput) {
                searchInput.value = '';
                currentFilters.search = '';
                clearSearchBtn.style.display = 'none';
                searchInput.parentElement.classList.remove('active-search');
                searchInput.focus();
                applyFilters();
            }
        });
    }
    
    if (statusFilter) {
        statusFilter.addEventListener('change', () => {
            currentFilters.status = statusFilter.value;
            applyFilters();
        });
    }
    
    if (tagFilter) {
        tagFilter.addEventListener('change', () => {
            currentFilters.tag = tagFilter.value;
            applyFilters();
        });
    }
    
    if (sortBySelect) {
        sortBySelect.addEventListener('change', () => {
            currentFilters.sortBy = sortBySelect.value;
            applyFilters();
        });
    }
    
    // View switcher event listeners
    const gridViewBtn = document.getElementById('gridViewBtn');
    const listViewBtn = document.getElementById('listViewBtn');
    const tableViewBtn = document.getElementById('tableViewBtn');
    
    if (gridViewBtn) gridViewBtn.addEventListener('click', () => switchView('grid'));
    if (listViewBtn) listViewBtn.addEventListener('click', () => switchView('list'));
    if (tableViewBtn) tableViewBtn.addEventListener('click', () => switchView('table'));
    
    // Export button event listener
    const exportBtn = document.getElementById('exportBtn');
    if (exportBtn) exportBtn.addEventListener('click', exportWarranties);
    
    // Import button event listener
    if (importBtn && csvFileInput) {
        importBtn.addEventListener('click', () => {
            csvFileInput.click(); // Trigger hidden file input
        });
        csvFileInput.addEventListener('change', (event) => {
            if (event.target.files && event.target.files.length > 0) {
                handleImport(event.target.files[0]);
            }
        });
    }
    
    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) refreshBtn.addEventListener('click', loadWarranties);
    
    // Save warranty changes
    const saveWarrantyBtn = document.getElementById('saveWarrantyBtn');
    if (saveWarrantyBtn) saveWarrantyBtn.addEventListener('click', saveWarranty);
    
    // Confirm delete button
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', deleteWarranty);
    
    // Load saved view preference
    loadViewPreference();
}

// Function to show loading spinner
function showLoadingSpinner() {
    if (loadingContainer) {
        loadingContainer.style.display = 'flex';
    }
}

// Function to hide loading spinner
function hideLoadingSpinner() {
    if (loadingContainer) {
        loadingContainer.style.display = 'none';
    }
}

// Delete warranty function
function deleteWarranty() {
    if (!currentWarrantyId) {
        showToast('No warranty selected for deletion', 'error');
        return;
    }
    
    const token = localStorage.getItem('auth_token');
    if (!token) {
        showToast('Authentication required', 'error');
        return;
    }
    
    showLoadingSpinner();
    
    fetch(`/api/warranties/${currentWarrantyId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': 'Bearer ' + token
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to delete warranty');
        }
        return response.json();
    })
    .then(data => {
        hideLoadingSpinner();
        showToast('Warranty deleted successfully', 'success');
        closeModals();
        loadWarranties();
    })
    .catch(error => {
        hideLoadingSpinner();
        console.error('Error deleting warranty:', error);
        showToast('Failed to delete warranty', 'error');
    });
}

// Save warranty updates
function saveWarranty() {
    if (!currentWarrantyId) {
        showToast('No warranty selected for update', 'error');
        return;
    }
    
    // --- Get form values ---
    const productName = document.getElementById('editProductName').value.trim();
    const purchaseDate = document.getElementById('editPurchaseDate').value;
    const isLifetime = document.getElementById('editIsLifetime').checked;
    const warrantyYears = document.getElementById('editWarrantyYears').value; // Declare only once
    
    // Basic validation
    if (!productName) {
        showToast('Product name is required', 'error');
        return;
    }
    
    if (!purchaseDate) {
        showToast('Purchase date is required', 'error');
        return;
    }
    
    // --- Modified Validation ---
    if (!isLifetime) {
        if (!warrantyYears || parseFloat(warrantyYears) <= 0) {
            showToast('Warranty period (years) must be greater than 0 for non-lifetime warranties', 'error');
            // Optional: focus the years input again
            const yearsInput = document.getElementById('editWarrantyYears');
            if (yearsInput) { // Check if element exists
                yearsInput.focus();
                yearsInput.classList.add('invalid');
            }
            return;
        }
    }
    // --- End Modified Validation ---
    
    // Create form data
    const formData = new FormData();
    formData.append('product_name', productName);
    formData.append('purchase_date', purchaseDate);
    
    // Optional fields
    const productUrl = document.getElementById('editProductUrl').value.trim();
    if (productUrl) {
        formData.append('product_url', productUrl);
    }
    
    const purchasePrice = document.getElementById('editPurchasePrice').value;
    if (purchasePrice) {
        formData.append('purchase_price', purchasePrice);
    }
    
    // Serial numbers
    const serialInputs = document.querySelectorAll('#editSerialNumbersContainer input');
    serialInputs.forEach(input => {
        if (input.value.trim()) {
            formData.append('serial_numbers', input.value.trim());
        }
    });
    
    // Tags - add tag IDs as JSON string
    if (editSelectedTags && editSelectedTags.length > 0) {
        const tagIds = editSelectedTags.map(tag => tag.id);
        formData.append('tag_ids', JSON.stringify(tagIds));
    } else {
        // Send empty array to clear tags
        formData.append('tag_ids', JSON.stringify([]));
    }
    
    // Files
    const invoiceFile = document.getElementById('editInvoice').files[0];
    if (invoiceFile) {
        formData.append('invoice', invoiceFile);
    }
    
    const manualFile = document.getElementById('editManual').files[0];
    if (manualFile) {
        formData.append('manual', manualFile);
    }
    
    // Document deletion flags
    const deleteInvoiceBtn = document.getElementById('deleteInvoiceBtn');
    if (deleteInvoiceBtn && deleteInvoiceBtn.dataset.delete === 'true') {
        formData.append('delete_invoice', 'true');
    }
    const deleteManualBtn = document.getElementById('deleteManualBtn');
    if (deleteManualBtn && deleteManualBtn.dataset.delete === 'true') {
        formData.append('delete_manual', 'true');
    }
    
    // --- Append is_lifetime and warranty_years ---
    formData.append('is_lifetime', isLifetime.toString());
    if (!isLifetime) {
        formData.append('warranty_years', warrantyYears);
    }
    // Add notes
    const notes = document.getElementById('editNotes').value;
    if (notes && notes.trim() !== '') {
        formData.append('notes', notes);
    } else {
        // Explicitly clear notes if empty
        formData.append('notes', '');
    }
    
    // Get auth token
    const token = localStorage.getItem('auth_token');
    if (!token) {
        showToast('Authentication required', 'error');
        return;
    }
    
    showLoadingSpinner();
    
    // Send request
    fetch(`/api/warranties/${currentWarrantyId}`, {
        method: 'PUT',
        headers: {
            'Authorization': 'Bearer ' + token
        },
        body: formData
    })
    .then(response => {
        if (!response.ok) {
            return response.json().then(data => {
                throw new Error(data.error || 'Failed to update warranty');
            });
        }
        return response.json();
    })
    .then(data => {
        hideLoadingSpinner();
        showToast('Warranty updated successfully', 'success');
        closeModals();
        // Update the notes in the card immediately if present
        if (typeof currentWarrantyId !== 'undefined' && currentWarrantyId !== null) {
            const card = document.querySelector(`.warranty-card .edit-btn[data-id="${currentWarrantyId}"]`);
            if (card) {
                const cardElement = card.closest('.warranty-card');
                if (cardElement) {
                    // Remove old notes button if present
                    const oldNotesBtn = cardElement.querySelector('.view-notes-btn');
                    if (oldNotesBtn) oldNotesBtn.remove();
                    // Get the new notes value
                    const newNotes = document.getElementById('editNotes').value;
                    if (newNotes && newNotes.trim() !== '') {
                        // Add the button if not present
                        let notesBtn = cardElement.querySelector('.view-notes-btn');
                        if (!notesBtn) {
                            const btn = document.createElement('button');
                            btn.className = 'btn btn-secondary btn-sm view-notes-btn';
                            btn.setAttribute('data-id', currentWarrantyId);
                            btn.style.margin = '10px 0 0 0';
                            btn.innerHTML = '<i class="fas fa-sticky-note"></i> View Notes';
                            btn.addEventListener('click', () => showNotesModal(newNotes));
                            // Insert after tags row if present, else at end
                            const tagsRow = cardElement.querySelector('.tags-row');
                            if (tagsRow && tagsRow.nextSibling) {
                                cardElement.insertBefore(btn, tagsRow.nextSibling);
                            } else {
                                cardElement.appendChild(btn);
                            }
                        }
                    } else {
                        // If notes are empty, ensure the button is removed
                        const notesBtn = cardElement.querySelector('.view-notes-btn');
                        if (notesBtn) notesBtn.remove();
                    }
                }
            }
        }
        loadWarranties(); // Still reload to ensure all data is fresh
    })
    .catch(error => {
        hideLoadingSpinner();
        console.error('Error updating warranty:', error);
        showToast(error.message || 'Failed to update warranty', 'error');
    });
}

// Function to populate tag filter dropdown
function populateTagFilter() {
    const tagFilter = document.getElementById('tagFilter');
    if (!tagFilter) return;
    
    // Clear existing options (except "All Tags")
    while (tagFilter.options.length > 1) {
        tagFilter.remove(1);
    }
    
    // Create a Set to store unique tag names
    const uniqueTags = new Set();
    
    // Collect all unique tags from warranties
    warranties.forEach(warranty => {
        if (warranty.tags && Array.isArray(warranty.tags)) {
            warranty.tags.forEach(tag => {
                uniqueTags.add(JSON.stringify({id: tag.id, name: tag.name, color: tag.color}));
            });
        }
    });
    
    // Sort tags alphabetically by name
    const sortedTags = Array.from(uniqueTags)
        .map(tagJson => JSON.parse(tagJson))
        .sort((a, b) => a.name.localeCompare(b.name));
    
    // Add options to the dropdown
    sortedTags.forEach(tag => {
        const option = document.createElement('option');
        option.value = tag.id;
        option.textContent = tag.name;
        option.style.backgroundColor = tag.color;
        tagFilter.appendChild(option);
    });
}

// --- Add New Function ---
function handleLifetimeChange(event) {
    const checkbox = event ? event.target : isLifetimeCheckbox;
    const group = warrantyYearsGroup;
    const input = warrantyYearsInput;

    if (!checkbox || !group || !input) return;

    if (checkbox.checked) {
        group.style.display = 'none';
        input.required = false;
        input.value = '';
    } else {
        group.style.display = 'block';
        input.required = true;
    }
}

// --- Add New Function ---
function handleEditLifetimeChange(event) {
    const checkbox = event ? event.target : editIsLifetimeCheckbox;
    const group = editWarrantyYearsGroup;
    const input = editWarrantyYearsInput;

    if (!checkbox || !group || !input) return;

    if (checkbox.checked) {
        group.style.display = 'none';
        input.required = false;
        input.value = '';
    } else {
        group.style.display = 'block';
        input.required = true;
    }
}

// --- Add this function to reset the wizard ---
function resetAddWarrantyWizard() {
    console.log('Resetting Add Warranty Wizard...');
    // Reset the form fields
    if (warrantyForm) {
        warrantyForm.reset();
    }

    // Reset serial numbers container (remove all but the first input structure)
    if (serialNumbersContainer) {
        serialNumbersContainer.innerHTML = ''; // Clear it
        addSerialNumberInput(); // Add the initial input back
    }

    // Reset file input displays
    if (fileName) fileName.textContent = '';
    if (manualFileName) fileName.textContent = '';

    // Reset selected tags
    selectedTags = [];
    console.log('Resetting Add Warranty Wizard...');
    // Reset the form fields
    if (warrantyForm) {
        warrantyForm.reset();
    }

    // Reset serial numbers container (remove all but the first input structure)
    if (serialNumbersContainer) {
        serialNumbersContainer.innerHTML = ''; // Clear it
        addSerialNumberInput(); // Add the initial input back
    }

    // Reset file input displays
    if (fileName) fileName.textContent = '';
    if (manualFileName) fileName.textContent = '';

    // Reset selected tags
    selectedTags = [];
    renderSelectedTags(); // Update the display

    // Reset tabs to the first one
    // Use the globally defined tabContents if available
    const tabs = addWarrantyModal?.querySelectorAll('.form-tab');
    const contents = addWarrantyModal?.querySelectorAll('.tab-content');
    if (tabs && contents && tabs.length > 0 && contents.length > 0) {
      currentTabIndex = 0;
      switchToTab(0); // Use the existing function to switch
    } else {
       console.warn("Could not find tabs/contents inside addWarrantyModal to reset.");
    }

    // Clear any validation states
    addWarrantyModal?.querySelectorAll('.invalid').forEach(el => el.classList.remove('invalid'));
    addWarrantyModal?.querySelectorAll('.validation-message').forEach(el => el.remove());

    // Reset lifetime checkbox state if needed (ensure handler runs)
    if (isLifetimeCheckbox) {
         isLifetimeCheckbox.checked = false; // Explicitly uncheck
         handleLifetimeChange({ target: isLifetimeCheckbox }); // Trigger handler to reset visibility/required state
    }
}

// --- Modify setupUIEventListeners or add this within DOMContentLoaded ---
function setupModalTriggers() {
    // Show Add Warranty Modal
    if (showAddWarrantyBtn && addWarrantyModal) {
        showAddWarrantyBtn.addEventListener('click', () => {
            resetAddWarrantyWizard(); // Reset before showing
            addWarrantyModal.classList.add('active');
            initFormTabs(); // Initialize tabs only when modal is shown
            switchToTab(0); // Ensure the first tab content is displayed correctly after reset
        });
    }

    // Hide Add Warranty Modal (using existing close logic)
    if (addWarrantyModal) {
        // Close button inside modal
        const closeBtn = addWarrantyModal.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                addWarrantyModal.classList.remove('active');
                resetAddWarrantyWizard(); // Reset on close
            });
        }
        // REMOVED: Backdrop click listener
        /*
        addWarrantyModal.addEventListener('click', (e) => {
            if (e.target === addWarrantyModal) {
                addWarrantyModal.classList.remove('active');
                resetAddWarrantyWizard(); // Reset on close
            }
        });
        */
        // Optional: Cancel button in footer if you add one
        // ... (cancel button logic remains unchanged)
    }

    // --- Edit Modal Triggers (Keep existing logic) ---
    // Close edit/delete modals when clicking outside or on close button
    document.querySelectorAll('#editModal, #deleteModal, [data-dismiss="modal"]').forEach(element => {
        element.addEventListener('click', (e) => {
            // Check if the click is on the backdrop itself OR a dismiss button
            if (e.target === element || e.target.matches('[data-dismiss="modal"]')) {
                 // Find the closest modal backdrop to the element clicked
                const modalToClose = e.target.closest('.modal-backdrop');
                if (modalToClose) {
                    // *** ADD CHECK: Do NOT close addWarrantyModal via this general listener ***
                    if (modalToClose.id === 'addWarrantyModal') {
                        return; // Ignore backdrop clicks for the add modal here
                    }
                    // *** END ADD CHECK ***

                    modalToClose.classList.remove('active');
                    // Reset edit form state if closing edit modal
                    if (modalToClose.id === 'editModal') {
                        // Optional: Add any edit form reset logic here if needed
                    }
                }
            }
        });
    });

    // Prevent modal content clicks from closing the modal (Keep for all modals)
    document.querySelectorAll('.modal').forEach(modal => {
        modal.addEventListener('click', (e) => {
            e.stopPropagation();
        });
    });
}

// --- CSV Import Functionality ---

async function handleImport(file) {
    if (!file) {
        showToast('No file selected.', 'warning');
        return;
    }

    if (!file.name.toLowerCase().endsWith('.csv')) {
        showToast('Invalid file type. Please select a .csv file.', 'error');
        return;
    }

    // Show loading indicator
    showLoadingSpinner();

    const formData = new FormData();
    formData.append('csv_file', file);

    try {
        // const token = localStorage.getItem('token'); // Incorrect key
        const token = localStorage.getItem('auth_token'); // Correct key used elsewhere
        if (!token) {
            showToast('Authentication error. Please log in again.', 'error');
            hideLoadingSpinner();
            // Maybe redirect to login: window.location.href = '/login.html';
            return;
        }

        const response = await fetch('/api/warranties/import', {
            method: 'POST',
            headers: {
                // Content-Type is automatically set by browser when using FormData
                'Authorization': `Bearer ${token}`
            },
            body: formData
        });

        hideLoadingSpinner();
        const result = await response.json();

        if (response.ok) {
            const { success_count, failure_count, errors } = result;
            let message = `${success_count} warranties imported successfully.`;
            if (failure_count > 0) {
                message += ` ${failure_count} rows failed.`;
                // Log detailed errors to the console for now
                console.warn('Import errors:', errors);
                // Consider showing errors in a modal or separate report later
            }
            showToast(message, 'success');

            // ***** FIX: Reload the tags list *****
            console.log("Import successful, reloading tags...");
            await loadTags(); // Fetch the updated list of all tags
            // ***** END FIX *****

            loadWarranties(); // Refresh the list
        } else {
            showToast(`Import failed: ${result.error || 'Unknown error'}`, 'error');
            if (result.errors) {
                 console.error('Detailed import errors:', result.errors);
            }
        }

    } catch (error) {
        hideLoadingSpinner();
        console.error('Error during file import:', error);
        showToast('An error occurred during import. Check console for details.', 'error');
    } finally {
        // Reset the file input so the user can select the same file again if needed
        if (csvFileInput) {
            csvFileInput.value = '';
        }
    }
}

// --- End CSV Import Functionality ---

// --- Add Storage Event Listener for Real-time Sync ---
window.addEventListener('storage', (event) => {
    const prefix = getPreferenceKeyPrefix();
    const viewKeys = [
        `${prefix}defaultView`,
        'viewPreference',
        `${prefix}warrantyView`,
        // Add `${prefix}viewPreference` if still used/relevant
        `${prefix}viewPreference` 
    ];

    if (viewKeys.includes(event.key) && event.newValue) {
        console.log(`Storage event detected for view preference (${event.key}). New value: ${event.newValue}`);
        // Check if the new value is different from the current view to avoid loops
        if (event.newValue !== currentView) {
             // Ensure view buttons exist before switching (we're on the main page)
             if (gridViewBtn || listViewBtn || tableViewBtn) {
                 switchView(event.newValue);
             }
        } else {
             console.log('Storage event value matches current view, ignoring.');
        }
    }
});
// --- End Storage Event Listener ---

// Add modal HTML to the end of the body if not present
if (!document.getElementById('notesModal')) {
    const notesModal = document.createElement('div');
    notesModal.id = 'notesModal';
    notesModal.className = 'modal-backdrop';
    notesModal.innerHTML = `
        <div class="modal" style="max-width: 500px;">
            <div class="modal-header">
                <h3 class="modal-title">Warranty Notes</h3>
                <button class="close-btn" id="closeNotesModal">&times;</button>
            </div>
            <div class="modal-body">
                <div id="notesModalContent" style="white-space: pre-line;"></div>
                <textarea id="notesModalTextarea" style="display:none;width:100%;min-height:100px;"></textarea>
            </div>
            <div class="modal-footer" id="notesModalFooter">
                <button class="btn btn-secondary" id="editNotesBtn">Edit</button>
                <button class="btn btn-primary" id="saveNotesBtn" style="display:none;">Save</button>
                <button class="btn btn-danger" id="cancelEditNotesBtn" style="display:none;">Cancel</button>
            </div>
        </div>
    `;
    document.body.appendChild(notesModal);
    document.getElementById('closeNotesModal').addEventListener('click', () => {
        notesModal.classList.remove('active');
    });
}

// Add global to track which warranty is being edited in the notes modal
let notesModalWarrantyId = null;
let notesModalWarrantyObj = null;

function showNotesModal(notes, warrantyOrId = null) {
    const notesModal = document.getElementById('notesModal');
    const notesModalContent = document.getElementById('notesModalContent');
    const notesModalTextarea = document.getElementById('notesModalTextarea');
    const editBtn = document.getElementById('editNotesBtn');
    const saveBtn = document.getElementById('saveNotesBtn');
    const cancelBtn = document.getElementById('cancelEditNotesBtn');

    // Support both (notes, warrantyObj) and (notes, id) for backward compatibility
    if (typeof warrantyOrId === 'object' && warrantyOrId !== null) {
        notesModalWarrantyId = warrantyOrId.id;
        notesModalWarrantyObj = warrantyOrId;
    } else {
        notesModalWarrantyId = warrantyOrId;
        // Try to find the warranty object from global warranties array
        notesModalWarrantyObj = warranties.find(w => w.id === notesModalWarrantyId) || null;
    }

    // Show note content, hide textarea and edit controls
    notesModalContent.style.display = '';
    notesModalContent.textContent = notes;
    notesModalTextarea.style.display = 'none';
    editBtn.style.display = '';
    saveBtn.style.display = 'none';
    cancelBtn.style.display = 'none';

    // Edit button handler
    editBtn.onclick = function() {
        notesModalContent.style.display = 'none';
        notesModalTextarea.style.display = '';
        notesModalTextarea.value = notes;
        editBtn.style.display = 'none';
        saveBtn.style.display = '';
        cancelBtn.style.display = '';
        notesModalTextarea.focus();
    };
    // Save button handler
    saveBtn.onclick = async function() {
        const newNote = notesModalTextarea.value.trim(); // Trim the note
        if (!notesModalWarrantyId || !notesModalWarrantyObj) {
            showToast('No warranty selected for note update', 'error');
            return;
        }
        // Save note via API, sending all required fields
        try {
            showLoadingSpinner();
            const token = localStorage.getItem('auth_token');
            const formData = new FormData();
            // --- Populate with existing data to avoid clearing fields ---
            formData.append('product_name', notesModalWarrantyObj.product_name);
            formData.append('purchase_date', (notesModalWarrantyObj.purchase_date || '').split('T')[0]);
            formData.append('is_lifetime', notesModalWarrantyObj.is_lifetime ? 'true' : 'false');
            if (!notesModalWarrantyObj.is_lifetime) {
                formData.append('warranty_years', notesModalWarrantyObj.warranty_years || ''); // Use empty string if null/undefined
            }
            if (notesModalWarrantyObj.product_url) {
                formData.append('product_url', notesModalWarrantyObj.product_url);
            }
            if (notesModalWarrantyObj.purchase_price !== null && notesModalWarrantyObj.purchase_price !== undefined) { // Check for null/undefined
                formData.append('purchase_price', notesModalWarrantyObj.purchase_price);
            }
            if (notesModalWarrantyObj.serial_numbers && Array.isArray(notesModalWarrantyObj.serial_numbers)) {
                notesModalWarrantyObj.serial_numbers.forEach(sn => {
                    if (sn && sn.trim() !== '') {
                        formData.append('serial_numbers', sn);
                    }
                });
            }
             // Send empty array if no serial numbers exist or are provided
            else if (!formData.has('serial_numbers')) {
                 formData.append('serial_numbers', JSON.stringify([]));
            }

            if (notesModalWarrantyObj.tags && Array.isArray(notesModalWarrantyObj.tags)) {
                const tagIds = notesModalWarrantyObj.tags.map(tag => tag.id);
                formData.append('tag_ids', JSON.stringify(tagIds));
            }
            // Send empty array if no tags exist or are provided
            else {
                 formData.append('tag_ids', JSON.stringify([]));
            }
            // --- End Populate ---

            formData.append('notes', newNote); // Append the potentially empty, trimmed note

            const response = await fetch(`/api/warranties/${notesModalWarrantyId}`, { // Added await and response handling
                method: 'PUT',
                headers: {
                    'Authorization': 'Bearer ' + token
                },
                body: formData
            });

            if (!response.ok) { // Check if the API call was successful
                 const errorData = await response.json().catch(() => ({})); // Try to parse error, default to empty object
                 throw new Error(errorData.error || `Failed to update note (Status: ${response.status})`);
            }


            hideLoadingSpinner();
            showToast('Note updated', 'success');

            // --- Updated UI logic ---
             if (newNote === '') {
                // If the note is now empty, close the modal
                document.getElementById('notesModal').classList.remove('active');
            } else {
                // If note is not empty, update the view and stay in the modal
                notesModalContent.textContent = newNote;
                notesModalContent.style.display = '';
                notesModalTextarea.style.display = 'none';
                editBtn.style.display = '';
                saveBtn.style.display = 'none';
                cancelBtn.style.display = 'none';
                 // Update the local warranty object's notes
                 if (notesModalWarrantyObj) {
                    notesModalWarrantyObj.notes = newNote;
                }
            }
             // --- End Updated UI logic ---

            // Refresh warranties list to update the card UI state (e.g., show/hide notes link)
            loadWarranties();
        } catch (e) {
            hideLoadingSpinner();
            console.error("Error updating note:", e); // Log the error
            showToast(e.message || 'Failed to update note', 'error'); // Show specific error if available
        }
    };
    // Cancel button handler
    cancelBtn.onclick = function() {
        notesModalContent.style.display = '';
        notesModalTextarea.style.display = 'none';
        editBtn.style.display = '';
        saveBtn.style.display = 'none';
        cancelBtn.style.display = 'none';
    };
    notesModal.classList.add('active');
}

// Utility to get currency symbol from preferences/localStorage
function getCurrencySymbol() {
    const prefix = getPreferenceKeyPrefix();
    console.log(`[getCurrencySymbol] Using prefix: ${prefix}`); // Log prefix
    let symbol = '$'; // Default value
    try {
        const prefsString = localStorage.getItem(`${prefix}preferences`);
        console.log(`[getCurrencySymbol] Read prefsString for ${prefix}preferences:`, prefsString); // Log raw string
        if (prefsString) {
            const prefs = JSON.parse(prefsString);
            // Use the symbol from prefs if it exists, otherwise keep the default
            if (prefs && prefs.currency_symbol) {
                symbol = prefs.currency_symbol;
            }
        }
    } catch (e) {
        console.error(`Error reading ${prefix}preferences from localStorage:`, e);
        // Keep the default '$' symbol in case of error
    }
    console.log(`[getCurrencySymbol] Returning symbol: ${symbol}`); // Log final symbol
    return symbol;
}

function updateCurrencySymbols() {
    const symbol = getCurrencySymbol();
    console.log(`Updating currency symbols to: ${symbol}`); // Log the symbol being applied
    const elements = document.querySelectorAll('.currency-symbol');
    console.log(`Found ${elements.length} elements with class 'currency-symbol'.`); // Log how many elements are found
    elements.forEach(el => {
        // console.log('Updating element:', el); // Optional: Log each element being updated
        el.textContent = symbol;
    });
}

// If you want to update currency symbols live when storage changes (e.g. settings page open in another tab):
window.addEventListener('storage', function(e) {
    const prefix = getPreferenceKeyPrefix();
    // Only update if the main preferences object for the current user type changed
    if (e.key === `${prefix}preferences`) {
        console.log(`Storage event detected for ${prefix}preferences. Updating currency symbols.`);
        updateCurrencySymbols();
    }
});