// alert('script.js loaded!'); // Remove alert after confirming script loads
console.log('[DEBUG] script.js loaded and running');

// Global variables
let warranties = [];
let currentTabIndex = 0;
let tabContents = []; // Initialize as empty array
let editMode = false;
let currentWarrantyId = null;
let userPreferencePrefix = null; // <<< ADDED GLOBAL PREFIX VARIABLE
let currentFilters = {
    status: 'all',
    tag: 'all',
    search: '',
    sortBy: 'expiration',
    vendor: 'all' // Added vendor filter
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
const vendorFilter = document.getElementById('vendorFilter'); // Added vendor filter select
const exportBtn = document.getElementById('exportBtn');
const gridViewBtn = document.getElementById('gridViewBtn');
const listViewBtn = document.getElementById('listViewBtn');
const tableViewBtn = document.getElementById('tableViewBtn');
const tableViewHeader = document.querySelector('.table-view-header');
const fileInput = document.getElementById('invoice');
const fileName = document.getElementById('fileName');
const manualInput = document.getElementById('manual');
const manualFileName = document.getElementById('manualFileName');
const otherDocumentInput = document.getElementById('otherDocument'); 
const otherDocumentFileName = document.getElementById('otherDocumentFileName'); 
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
const warrantyDurationFields = document.getElementById('warrantyDurationFields'); // New container
const warrantyDurationYearsInput = document.getElementById('warrantyDurationYears');
const warrantyDurationMonthsInput = document.getElementById('warrantyDurationMonths');
const warrantyDurationDaysInput = document.getElementById('warrantyDurationDays');

const editIsLifetimeCheckbox = document.getElementById('editIsLifetime');
const editWarrantyDurationFields = document.getElementById('editWarrantyDurationFields'); // New container
const editWarrantyDurationYearsInput = document.getElementById('editWarrantyDurationYears');
const editWarrantyDurationMonthsInput = document.getElementById('editWarrantyDurationMonths');
const editWarrantyDurationDaysInput = document.getElementById('editWarrantyDurationDays');

// Add near other DOM Element declarations
const showAddWarrantyBtn = document.getElementById('showAddWarrantyBtn');
const addWarrantyModal = document.getElementById('addWarrantyModal');
const serialNumbersContainer = document.getElementById('serialNumbersContainer'); // Ensure this is defined

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
    // Register Service Worker
    if ('serviceWorker' in navigator) {
        window.addEventListener('load', () => {
            navigator.serviceWorker.register('./sw.js')
                .then(registration => {
                    console.log('Service Worker registered with scope:', registration.scope);
                })
                .catch(error => {
                    console.error('Service Worker registration failed:', error);
                });
        });
    }

    // --- Search button click triggers search ---
    const searchBtn = document.getElementById('searchBtn');
    const searchInput = document.getElementById('searchWarranties');
    if (searchBtn && searchInput) {
        searchBtn.addEventListener('click', function(e) {
            e.preventDefault();
            currentFilters.search = searchInput.value.toLowerCase();
            applyFilters();
        });
    }
    // --- Ensure globalManageTagsBtn triggers modal and tag form is always initialized ---
    // (Redundant with setupUIEventListeners, but ensures modal is always ready)
    const globalManageTagsBtn = document.getElementById('globalManageTagsBtn');
    if (globalManageTagsBtn) {
        globalManageTagsBtn.addEventListener('click', async () => {
            if (!allTags || allTags.length === 0) {
                showLoadingSpinner();
                try {
                    await loadTags();
                } catch (error) {
                    console.error("Failed to load tags before opening modal:", error);
                    showToast("Could not load tags. Please try again.", "error");
                    hideLoadingSpinner();
                    return;
                }
                hideLoadingSpinner();
            }
            openTagManagementModal();
        });
    }
    console.log('[DEBUG] Registering authStateReady event handler');
    // ... other initialization ...

    // --- BEGIN REFACTORED TAG MODAL AND MAIN FORM TAG UI SETUP ---
    const globalTagManagementModal = document.getElementById('tagManagementModal');
    const globalNewTagForm = document.getElementById('newTagForm'); // Inside tagManagementModal
    const mainTagSearchInput = document.getElementById('tagSearch'); // For the main "Add Warranty" form's tag search
    const warrantyFormElement = document.getElementById('warrantyForm'); // The main add warranty form

    // 1. ALWAYS Initialize listeners for the global Tag Management Modal IF IT EXISTS
    if (globalTagManagementModal) {
        if (globalNewTagForm) {
            // Ensure the event listener is attached only once, or manage it if DOMContentLoaded could fire multiple times (not typical)
            // For simplicity, assuming DOMContentLoaded runs once per page load.
            globalNewTagForm.addEventListener('submit', (e) => {
                e.preventDefault();
                // Inline implementation for creating a new tag from the modal
                const tagNameInput = document.getElementById('newTagName');
                const tagColorInput = document.getElementById('newTagColor');
                const name = tagNameInput ? tagNameInput.value.trim() : '';
                const color = tagColorInput ? tagColorInput.value : '#808080';
                if (!name) {
                    showToast('Tag name is required', 'error');
                    return;
                }
                // Use the existing createTag function if available
                if (typeof createTag === 'function') {
                    createTag(name, color)
                        .then(() => {
                            if (tagNameInput) tagNameInput.value = '';
                            if (tagColorInput) tagColorInput.value = '#808080';
                            renderExistingTags && renderExistingTags();
                        })
                        .catch((err) => {
                            showToast((err && err.message) || 'Failed to create tag', 'error');
                        });
                } else {
                    showToast('Tag creation function not found', 'error');
                }
            });
        }

        const closeButtons = globalTagManagementModal.querySelectorAll('[data-dismiss="modal"]');
        closeButtons.forEach(button => {
            button.addEventListener('click', (event) => {
                globalTagManagementModal.style.display = 'none';
                event.stopPropagation(); // This was the fix from before, ensuring it's applied
            });
        });
        console.log('Global Tag Management Modal listeners initialized directly in DOMContentLoaded.');
    }

    // 2. Initialize Tag functionality FOR THE MAIN ADD WARRANTY FORM (if its specific tag search input exists)
    // initTagFunctionality is now refactored to be specific to the main form's tag UI.
    if (mainTagSearchInput) {
        initTagFunctionality(); // Sets up main form tag search, its manage button, etc.
                                // Also calls loadTags() if needed for the main form.
    }
    // --- END REFACTORED TAG MODAL AND MAIN FORM TAG UI SETUP ---


    // Setup form submission (assuming addWarrantyForm exists - this is 'warrantyFormElement')
    // const form = document.getElementById('addWarrantyForm'); // Old selector
    if (warrantyFormElement) { // Use the variable defined above
        warrantyFormElement.addEventListener('submit', handleFormSubmit);
        // Initialize form tabs if the form exists
        // initFormTabs(); // This should be called when the ADD MODAL is SHOWN, not globally here.
                          // It's correctly in setupModalTriggers for the addWarrantyModal.
    }


    // Initialize theme toggle state *after* DOM is loaded
    // ... (theme toggle init logic remains) ...

    // Setup view switcher (assuming view switcher elements exist)
    if (document.getElementById('gridViewBtn')) {
        // setupViewSwitcher(); // Removed undefined function
        loadViewPreference(); // This is fine here, loads initial view preference.
    }

    // Setup filter controls (assuming filter controls exist)
    if (document.getElementById('filterControls')) {
        // setupFilterControls(); // Removed: function not defined
        // populateTagFilter(); // This should be called AFTER warranties (and their tags) are loaded.
                              // It's called in loadWarranties -> processAllWarranties or similar flow.
    }

    // Initialize modal interactions (general modal triggers like close buttons, backdrop)
    setupModalTriggers(); // This sets up general modal behaviors and specific triggers for add/edit.

    // Initialize form-specific lifetime checkbox handler FOR THE MAIN ADD FORM
    const lifetimeCheckbox = document.getElementById('isLifetime'); // Main form's checkbox
    if (lifetimeCheckbox) {
        lifetimeCheckbox.addEventListener('change', handleLifetimeChange);
        handleLifetimeChange({ target: lifetimeCheckbox }); // Initial check
    }

    // --- LOAD WARRANTIES AFTER AUTH --- 
    // Listen for an event from auth.js indicating authentication is complete and user context is ready.
    // ** IMPORTANT: Replace 'authStateReady' with the actual event name fired by auth.js **
    window.addEventListener('authStateReady', async function handleAuthReady() { // <-- Make handler async
        console.log('[DEBUG] authStateReady handler called');
        console.log("Auth state ready event received. Preparing preferences and warranties...");
        // Ensure this listener runs only once
        window.removeEventListener('authStateReady', handleAuthReady);

        // Set prefix
        userPreferencePrefix = getPreferenceKeyPrefix();
        console.log(`[authStateReady] Determined and stored global prefix: ${userPreferencePrefix}`);

        // Load preferences
        await loadAndApplyUserPreferences();
        await loadTags(); // Ensure all available tags are loaded after authentication

        // Load warranty data (fetches, processes, populates global array)
        if (document.getElementById('warrantiesList')) {
            console.log("[authStateReady] Loading warranty data...");
            await loadWarranties(); // Waits for fetch/process
            console.log('[DEBUG] After loadWarranties, warranties array:', warranties);
        } else {
            console.log("[authStateReady] Warranties list element not found.");
        }

        // Now that data and preferences are ready, apply view/currency and render via applyFilters
        console.log("[authStateReady] Applying preferences and rendering...");
        loadViewPreference(); // Sets currentView and UI classes/buttons
        updateCurrencySymbols(); // Update symbols
        
        // Apply filters using the loaded data and render the list
        if (document.getElementById('warrantiesList')) { 
            applyFilters(); 
        }

    }, { once: true }); // Use { once: true } as a fallback if removeEventListener isn't reliable across scripts
    // --- END LOAD WARRANTIES AFTER AUTH ---

    // updateCurrencySymbols(); // Call removed, rely on loadWarranties triggering render with correct symbol
});

// Initialize theme based on user preference or system preference
function initializeTheme() {
    // Only use the global darkMode key for theme persistence
    const savedTheme = localStorage.getItem('darkMode');
    if (savedTheme !== null) {
        setTheme(savedTheme === 'true');
    } else {
        setTheme(window.matchMedia('(prefers-color-scheme: dark)').matches);
    }
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

// const nextButton = document.querySelector('.next-tab'); // Keep these if needed globally, otherwise might remove
// const prevButton = document.querySelector('.prev-tab'); // Keep these if needed globally, otherwise might remove

// --- Add near other DOM Element declarations ---
    // ... existing code ...
    // Add save button handler for notes modal (if not already present)
    const saveNotesBtn = document.getElementById('saveNotesBtn');
    if (saveNotesBtn) {
        saveNotesBtn.onclick = async function() {
            // Get the warranty ID being edited
            const warrantyId = notesModalWarrantyId;
            const notesValue = document.getElementById('notesModalTextarea').value;
            if (!warrantyId || !notesModalWarrantyObj) return;
            // Get auth token
            const token = localStorage.getItem('auth_token');
            if (!token) {
                showToast('Authentication required', 'error');
                return;
            }
            showLoadingSpinner();
            try {
                // Use FormData and send all required fields, just like the edit modal
                const formData = new FormData();
                formData.append('product_name', notesModalWarrantyObj.product_name);
                formData.append('purchase_date', (notesModalWarrantyObj.purchase_date || '').split('T')[0]);
                formData.append('is_lifetime', notesModalWarrantyObj.is_lifetime ? 'true' : 'false');
                if (!notesModalWarrantyObj.is_lifetime) {
                    // Append duration components instead of warranty_years
                    formData.append('warranty_duration_years', notesModalWarrantyObj.warranty_duration_years || 0);
                    formData.append('warranty_duration_months', notesModalWarrantyObj.warranty_duration_months || 0);
                    formData.append('warranty_duration_days', notesModalWarrantyObj.warranty_duration_days || 0);
                }
                if (notesModalWarrantyObj.product_url) {
                    formData.append('product_url', notesModalWarrantyObj.product_url);
                }
                if (notesModalWarrantyObj.purchase_price !== null && notesModalWarrantyObj.purchase_price !== undefined) {
                    formData.append('purchase_price', notesModalWarrantyObj.purchase_price);
                }
                if (notesModalWarrantyObj.serial_numbers && Array.isArray(notesModalWarrantyObj.serial_numbers)) {
                    notesModalWarrantyObj.serial_numbers.forEach(sn => {
                        if (sn && sn.trim() !== '') {
                            formData.append('serial_numbers[]', sn); // Use [] for arrays
                        }
                    });
                } else if (!formData.has('serial_numbers[]')) {
                    // Send empty array if none exist
                    // formData.append('serial_numbers[]', ''); // Sending empty string might not work as expected, better to not send if empty
                }
                if (notesModalWarrantyObj.tags && Array.isArray(notesModalWarrantyObj.tags)) {
                    const tagIds = notesModalWarrantyObj.tags.map(tag => tag.id);
                    formData.append('tag_ids', JSON.stringify(tagIds));
                } else {
                    formData.append('tag_ids', JSON.stringify([]));
                }
                formData.append('notes', notesValue);
                const response = await fetch(`/api/warranties/${warrantyId}`, {
                    method: 'PUT',
                    headers: {
                        'Authorization': 'Bearer ' + token
                    },
                    body: formData
                });
                if (!response.ok) {
                    const data = await response.json();
                    throw new Error(data.error || 'Failed to update notes');
                }
                hideLoadingSpinner();
                showToast('Notes updated successfully', 'success');
                // Close the modal
                const notesModal = document.getElementById('notesModal');
                if (notesModal) notesModal.style.display = 'none';
                // Now reload warranties and re-render UI
                await loadWarranties();
                applyFilters();
            } catch (error) {
                hideLoadingSpinner();
                console.error('Error updating notes:', error);
                showToast(error.message || 'Failed to update notes', 'error');
            }
        };
    }

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
    // Get all relevant form controls within the tab
    const controls = tabContent.querySelectorAll('input, textarea, select');
    let isTabValid = true;

    controls.forEach(control => {
        // Check the native HTML5 validity state
        if (!control.validity.valid) {
            isTabValid = false;
            control.classList.add('invalid');
            // Ensure a validation message placeholder exists or is updated by showValidationErrors
        } else {
            control.classList.remove('invalid');
            // Remove validation message if control is now valid and message exists
            let validationMessageElement = control.nextElementSibling;
            if (validationMessageElement && validationMessageElement.classList.contains('validation-message')) {
                validationMessageElement.remove();
            }
        }
    });
    return isTabValid;
}

// Show validation errors for a specific tab
function showValidationErrors(tabIndex) {
    const tabContent = tabContents[tabIndex];
    const controls = tabContent.querySelectorAll('input, textarea, select');
    let firstInvalidControl = null;

    controls.forEach(control => {
        if (!control.validity.valid) {
            if (!firstInvalidControl) firstInvalidControl = control;
            control.classList.add('invalid');

            // Add or update validation message
            let validationMessageElement = control.nextElementSibling;
            if (!validationMessageElement || !validationMessageElement.classList.contains('validation-message')) {
                validationMessageElement = document.createElement('div');
                validationMessageElement.className = 'validation-message';
                control.parentNode.insertBefore(validationMessageElement, control.nextSibling);
            }
            validationMessageElement.textContent = control.validationMessage || 'This field is invalid.';
        } else {
            // Ensure invalid class is removed if somehow missed by validateTab (shouldn't happen)
            control.classList.remove('invalid');
            // Remove validation message if control is now valid
            let validationMessageElement = control.nextElementSibling;
            if (validationMessageElement && validationMessageElement.classList.contains('validation-message')) {
                validationMessageElement.remove();
            }
        }
    });

    // The browser will attempt to focus the first invalid field when form submission is prevented.
    // Switching to the tab containing the error (done by handleFormSubmit) is key.
    showToast('Please correct the errors in the current tab.', 'error');
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
    const purchaseDateStr = document.getElementById('purchaseDate')?.value;
    const summaryPurchaseDate = document.getElementById('summary-purchase-date');
    if (summaryPurchaseDate) {
        if (purchaseDateStr) {
            // Use the same logic as formatDate to handle YYYY-MM-DD
            const parts = String(purchaseDateStr).split('-');
            let formattedDate = '-'; // Default
            if (parts.length === 3) {
                const year = parseInt(parts[0], 10);
                const month = parseInt(parts[1], 10) - 1; // JS months are 0-indexed
                const day = parseInt(parts[2], 10);
                const dateObj = new Date(Date.UTC(year, month, day));
                if (!isNaN(dateObj.getTime())) {
                    // Format manually (example: Jan 1, 2023)
                    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
                    formattedDate = `${monthNames[month]} ${day}, ${year}`;
                }
            }
            summaryPurchaseDate.textContent = formattedDate;
        } else {
            summaryPurchaseDate.textContent = '-';
        }
    }
    
    // --- Handle Lifetime in Summary ---
    const isLifetime = isLifetimeCheckbox ? isLifetimeCheckbox.checked : false;
    const summaryWarrantyDuration = document.getElementById('summary-warranty-duration'); // Use new ID

    if (summaryWarrantyDuration) {
        if (isLifetime) {
            summaryWarrantyDuration.textContent = 'Lifetime';
        } else {
            const years = parseInt(warrantyDurationYearsInput?.value || 0);
            const months = parseInt(warrantyDurationMonthsInput?.value || 0);
            const days = parseInt(warrantyDurationDaysInput?.value || 0);
            
            let durationParts = [];
            if (years > 0) durationParts.push(`${years} year${years !== 1 ? 's' : ''}`);
            if (months > 0) durationParts.push(`${months} month${months !== 1 ? 's' : ''}`);
            if (days > 0) durationParts.push(`${days} day${days !== 1 ? 's' : ''}`);
            
            summaryWarrantyDuration.textContent = durationParts.length > 0 ? durationParts.join(', ') : '-';
        }
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

    const otherDocumentFile = document.getElementById('otherDocument')?.files[0]; 
    const summaryOtherDocument = document.getElementById('summary-other-document'); 
    if (summaryOtherDocument) { 
        summaryOtherDocument.textContent = otherDocumentFile ? 
            otherDocumentFile.name : 'No file selected'; 
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

    // Vendor/Retailer
    const vendor = document.getElementById('vendor');
    document.getElementById('summary-vendor').textContent = vendor && vendor.value ? vendor.value : '-';
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
    if (otherDocumentFileName) otherDocumentFileName.textContent = ''; 
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
            
            // Check if vendor name contains search term
            const vendorMatch = warranty.vendor && warranty.vendor.toLowerCase().includes(searchTerm);
            
            // Return true if either product name, tag name, or vendor name matches
            return productNameMatch || tagMatch || vendorMatch;
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
    
    // Add headers - Updated for duration components
    csvContent += "ProductName,PurchaseDate,IsLifetime,WarrantyDurationYears,WarrantyDurationMonths,WarrantyDurationDays,ExpirationDate,Status,PurchasePrice,SerialNumber,ProductURL,Tags,Vendor\n";
    
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
        
        // Format row data - Updated for duration components
        const row = [
            warranty.product_name || '',
            formatDateYYYYMMDD(new Date(warranty.purchase_date)),
            warranty.is_lifetime ? 'TRUE' : 'FALSE',
            warranty.warranty_duration_years || 0,
            warranty.warranty_duration_months || 0,
            warranty.warranty_duration_days || 0,
            warranty.is_lifetime ? '' : formatDateYYYYMMDD(new Date(warranty.expiration_date)), // Expiration date empty for lifetime
            warranty.status || '',
            warranty.purchase_price || '',
            serialNumbers,
            warranty.product_url || '',
            tags,
            warranty.vendor || ''
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
async function switchView(viewType) { // Added async
    console.log(`Switching to view: ${viewType}`);
    currentView = viewType;

    const prefix = getPreferenceKeyPrefix();
    const viewKey = `${prefix}defaultView`;
    const currentStoredValue = localStorage.getItem(viewKey);

    // Save to localStorage immediately for responsiveness
    if (currentStoredValue !== viewType) {
        localStorage.setItem(viewKey, viewType); 
        // Keep legacy keys for now if needed, but primary is viewKey
        localStorage.setItem(`${prefix}warrantyView`, viewType);
        localStorage.setItem('viewPreference', viewType); 
        console.log(`Saved view preference (${viewKey}) to localStorage: ${viewType}`);
    } else {
        console.log(`View preference (${viewKey}) already set to ${viewType} in localStorage.`);
    }

    // --- BEGIN ADDED: Save preference to API --- 
    if (window.auth && window.auth.isAuthenticated()) {
        const token = window.auth.getToken();
        if (token) {
            try {
                console.log(`Attempting to save view preference (${viewType}) to API...`);
                const response = await fetch('/api/auth/preferences', {
                    method: 'PUT',
                    headers: {
                        'Authorization': `Bearer ${token}`,
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ default_view: viewType }) // Send only the changed preference
                });

                if (response.ok) {
                    console.log('Successfully saved view preference to API.');
                } else {
                    const errorData = await response.json().catch(() => ({}));
                    console.warn(`Failed to save view preference to API: ${response.status}`, errorData.message || '');
                    // Optional: Show a non-intrusive warning toast?
                    // showToast('Failed to sync view preference with server.', 'warning'); 
                }
            } catch (error) {
                console.error('Error saving view preference to API:', error);
                // Optional: Show a non-intrusive warning toast?
                // showToast('Error syncing view preference with server.', 'error'); 
            }
        } else {
            console.warn('Cannot save view preference to API: No auth token found.');
        }
    } else {
        console.warn('Cannot save view preference to API: User not authenticated or auth module not loaded.');
    }
    // --- END ADDED: Save preference to API ---

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
        // Add active class to the correct button
        if (viewType === 'grid') gridViewBtn.classList.add('active');
        if (viewType === 'list') listViewBtn.classList.add('active');
        if (viewType === 'table') tableViewBtn.classList.add('active');
    }
    
    // Show/hide table header only if it exists
    if (tableViewHeader) {
        tableViewHeader.classList.toggle('visible', viewType === 'table');
    }

    // Re-render warranties only if warrantiesList exists
    if (warrantiesList) {
        renderWarranties(filterWarranties()); // Assuming filterWarranties() returns the correct array
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

    // Parse purchase_date string (YYYY-MM-DD) into a UTC Date object
    let purchaseDateObj = null;
    if (processedWarranty.purchase_date) {
        const parts = String(processedWarranty.purchase_date).split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1; // JS months are 0-indexed
            const day = parseInt(parts[2], 10);
            purchaseDateObj = new Date(Date.UTC(year, month, day));
            if (isNaN(purchaseDateObj.getTime())) {
                 purchaseDateObj = null; // Invalid date parsed
            }
        } else {
            // Fallback for unexpected formats, though backend should send YYYY-MM-DD
            purchaseDateObj = new Date(processedWarranty.purchase_date);
             if (isNaN(purchaseDateObj.getTime())) {
                 purchaseDateObj = null; 
            }
        }
    }
    processedWarranty.purchaseDate = purchaseDateObj;
    
    // Parse expiration_date similarly (assuming it's also YYYY-MM-DD)
    let expirationDateObj = null;
    if (processedWarranty.expiration_date) {
        const parts = String(processedWarranty.expiration_date).split('-');
        if (parts.length === 3) {
            const year = parseInt(parts[0], 10);
            const month = parseInt(parts[1], 10) - 1;
            const day = parseInt(parts[2], 10);
            expirationDateObj = new Date(Date.UTC(year, month, day));
             if (isNaN(expirationDateObj.getTime())) {
                 expirationDateObj = null;
            }
        } else {
            expirationDateObj = new Date(processedWarranty.expiration_date);
             if (isNaN(expirationDateObj.getTime())) {
                 expirationDateObj = null;
            }
        }
    }
    processedWarranty.expirationDate = expirationDateObj;

    // --- Lifetime Handling ---
    if (processedWarranty.is_lifetime) {
        processedWarranty.status = 'active';
        processedWarranty.statusText = 'Lifetime';
        processedWarranty.daysRemaining = Infinity;
        // Ensure duration components are 0 for lifetime
        processedWarranty.warranty_duration_years = 0;
        processedWarranty.warranty_duration_months = 0;
        processedWarranty.warranty_duration_days = 0;
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
    // +++ REMOVED: Ensure Preferences are loaded FIRST (Now handled by authStateReady) +++
    // await loadAndApplyUserPreferences(); 
    // +++ Preferences Loaded +++
    
    try {
        console.log('[DEBUG] Entered loadWarranties');
        showLoading();
        
        // Fetch user preferences (including date format) before loading warranties
        // --- THIS INNER PREFERENCE FETCH IS NOW REDUNDANT, REMOVE/COMMENT OUT --- 
        /*
        try {
            const token = window.auth.getToken(); // Ensure token is retrieved here
            if (!token) throw new Error("No auth token found"); // Added error handling

            const prefsResponse = await fetch('/api/auth/preferences', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });
            
            if (prefsResponse.ok) {
                const prefsData = await prefsResponse.json();
                console.log("Preferences fetched in loadWarranties:", prefsData);
                
                // Update expiringSoonDays
                if (prefsData && typeof prefsData.expiring_soon_days !== 'undefined') {
                    const oldValue = expiringSoonDays;
                    expiringSoonDays = prefsData.expiring_soon_days;
                    console.log('Updated expiring soon days from preferences:', expiringSoonDays);
                    // Reprocess logic moved below warranty fetch
                }

                // --- ADDED: Update dateFormat in localStorage --- 
                if (prefsData && typeof prefsData.date_format !== 'undefined') {
                    const oldDateFormat = localStorage.getItem('dateFormat');
                    localStorage.setItem('dateFormat', prefsData.date_format);
                    console.log(`Updated dateFormat in localStorage from API: ${prefsData.date_format}`);
                    // Trigger re-render if format changed and warranties already exist (though unlikely at this stage)
                    if (warranties && warranties.length > 0 && oldDateFormat !== prefsData.date_format) {
                        console.log('Date format changed, triggering re-render via applyFilters');
                        applyFilters(); // Re-render warranties with new format
                    }
                } else {
                     // If API doesn't return date_format, ensure localStorage has a default
                     if (!localStorage.getItem('dateFormat')) {
                         localStorage.setItem('dateFormat', 'MDY');
                         console.log('API did not return date_format, setting localStorage default to MDY');
                     }
                }
                // --- END ADDED SECTION ---

            } else {
                 // Handle failed preference fetch
                 console.warn('Failed to fetch preferences:', prefsResponse.status);
                 // Ensure a default date format exists if fetch fails
                 if (!localStorage.getItem('dateFormat')) {
                     localStorage.setItem('dateFormat', 'MDY');
                     console.log('Preferences fetch failed, setting localStorage default date format to MDY');
                 }
            }
        } catch (error) {
            console.error('Error loading preferences:', error);
            // Ensure a default date format exists on error
            if (!localStorage.getItem('dateFormat')) {
                localStorage.setItem('dateFormat', 'MDY');
                console.log('Error fetching preferences, setting localStorage default date format to MDY');
            }
            // Continue loading warranties even if preferences fail
        }
        */
        // --- END REDUNDANT PREFERENCE FETCH ---
        
        // Use the full URL to avoid path issues
        const apiUrl = window.location.origin + '/api/warranties';
        
        // Check if auth is available and user is authenticated
        if (!window.auth || !window.auth.isAuthenticated()) {
            console.log('[DEBUG] Early return: User not authenticated');
            renderEmptyState('Please log in to view your warranties.');
            hideLoading();
            return;
        }
        // Get the auth token
        const token = window.auth.getToken();
        if (!token) {
            console.log('[DEBUG] Early return: No auth token available');
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
        console.log('[DEBUG] Received warranties from server:', data);
        if (!Array.isArray(data)) {
            console.error('[DEBUG] API did not return an array! Data:', data);
        }
        // Process each warranty to calculate status and days remaining
        warranties = Array.isArray(data) ? data.map(warranty => {
            const processed = processWarrantyData(warranty);
            console.log('[DEBUG] Processed warranty:', processed);
            return processed;
        }) : [];
        console.log('[DEBUG] Final warranties array:', warranties);
        
        if (warranties.length === 0) {
            console.log('No warranties found, showing empty state');
            renderEmptyState('No warranties found. Add your first warranty using the form.');
        } else {
            console.log('Applying filters to display warranties');
            
            // Populate tag filter dropdown with tags from warranties
            populateTagFilter();
            populateVendorFilter(); // Added call to populate vendor filter
            
            // REMOVED: applyFilters(); // Now called from authStateReady after data and prefs are loaded
        }
    } catch (error) {
        console.error('[DEBUG] Error loading warranties:', error);
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
    // Input 'date' should now be a Date object created by processWarrantyData (or null)
    if (!date || !(date instanceof Date) || isNaN(date.getTime())) {
        return 'N/A';
    }

    // Get the user's preferred format from localStorage, default to MDY
    const formatPreference = localStorage.getItem('dateFormat') || 'MDY';

    // Manually extract UTC components to avoid timezone discrepancies
    const year = date.getUTCFullYear();
    const monthIndex = date.getUTCMonth(); // 0-indexed for month names array
    const day = date.getUTCDate();

    // Padded numeric values
    const monthPadded = (monthIndex + 1).toString().padStart(2, '0');
    const dayPadded = day.toString().padStart(2, '0');

    // Abbreviated month names
    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                        "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const monthAbbr = monthNames[monthIndex];

    switch (formatPreference) {
        case 'DMY':
            return `${dayPadded}/${monthPadded}/${year}`;
        case 'YMD':
            return `${year}-${monthPadded}-${dayPadded}`;
        case 'MDY_WORDS': // Added
            return `${monthAbbr} ${day}, ${year}`;
        case 'DMY_WORDS': // Added
            return `${day} ${monthAbbr} ${year}`;
        case 'YMD_WORDS': // Added
            return `${year} ${monthAbbr} ${day}`;
        case 'MDY':
        default:
            return `${monthPadded}/${dayPadded}/${year}`;
    }
}

function formatDateYYYYMMDD(date) {
    if (!date || !(date instanceof Date) || isNaN(date.getTime())) {
        return 'N/A';
    }

    const year = date.getUTCFullYear();
    const month = String(date.getUTCMonth() + 1).padStart(2, '0');
    const day = String(date.getUTCDate()).padStart(2, '0');

    return `${year}-${month}-${day}`;
}

async function renderWarranties(warrantiesToRender) {
    console.log('renderWarranties called with:', warrantiesToRender);

    // Guard clause: If the main warrantiesList element doesn't exist on the current page, exit.
    // This can happen if saveWarranty -> applyFilters -> renderWarranties is called from a page
    // that doesn't have the main list view (e.g., the status page).
    if (!warrantiesList) {
        console.warn('renderWarranties: warrantiesList element not found. Aborting render. This might be normal if not on the main warranties page.');
        return;
    }

    if (!warrantiesToRender || warrantiesToRender.length === 0) {
        renderEmptyState(); // renderEmptyState should also check for warrantiesList or its specific container
        return;
    }
    
    const today = new Date();
    const symbol = getCurrencySymbol(); // Get the correct symbol HERE
    
    warrantiesList.innerHTML = '';
    
    // Apply sorting based on current sort selection
    const sortedWarranties = [...warrantiesToRender].sort((a, b) => {
        switch (currentFilters.sortBy) {
            case 'name':
                return (a.product_name || '').toLowerCase().localeCompare((b.product_name || '').toLowerCase());
            case 'purchase':
                return new Date(b.purchase_date || 0) - new Date(a.purchase_date || 0);
            case 'vendor': // Added vendor sorting
                return (a.vendor || '').toLowerCase().localeCompare((b.vendor || '').toLowerCase());
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
        // Format warranty duration text
        let warrantyDurationText = 'N/A';
        if (isLifetime) {
            warrantyDurationText = 'Lifetime';
        } else {
            const years = warranty.warranty_duration_years || 0;
            const months = warranty.warranty_duration_months || 0;
            const days = warranty.warranty_duration_days || 0;
            let parts = [];
            if (years > 0) parts.push(`${years} year${years !== 1 ? 's' : ''}`);
            if (months > 0) parts.push(`${months} month${months !== 1 ? 's' : ''}`);
            if (days > 0) parts.push(`${days} day${days !== 1 ? 's' : ''}`);
            if (parts.length > 0) {
                warrantyDurationText = parts.join(', ');
            }
        }
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
                        <div>Warranty: <span>${warrantyDurationText}</span></div>
                        <div>Expires: <span>${expirationDateText}</span></div>
                        ${warranty.purchase_price ? `<div><span>Price: </span><span class="currency-symbol">${symbol}</span><span>${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
                        ${warranty.vendor ? `<div>Vendor: <span>${warranty.vendor}</span></div>` : ''}
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
                        ${warranty.other_document_path && warranty.other_document_path !== 'null' ? `
                            <a href="#" onclick="openSecureFile('${warranty.other_document_path}'); return false;" class="other-document-link">
                                <i class="fas fa-file-alt"></i> Files
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
                        <div>Warranty: <span>${warrantyDurationText}</span></div>
                        <div>Expires: <span>${expirationDateText}</span></div>
                        ${warranty.purchase_price ? `<div><span>Price: </span><span class="currency-symbol">${symbol}</span><span>${parseFloat(warranty.purchase_price).toFixed(2)}</span></div>` : ''}
                        ${warranty.vendor ? `<div>Vendor: <span>${warranty.vendor}</span></div>` : ''}
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
                        ${warranty.other_document_path && warranty.other_document_path !== 'null' ? `
                            <a href="#" onclick="openSecureFile('${warranty.other_document_path}'); return false;" class="other-document-link">
                                <i class="fas fa-file-alt"></i> Files
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
                        ${warranty.other_document_path && warranty.other_document_path !== 'null' ? `
                            <a href="#" onclick="openSecureFile('${warranty.other_document_path}'); return false;" class="other-document-link">
                                <i class="fas fa-file-alt"></i> Files
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

        // Check vendor
        if (warranty.vendor && warranty.vendor.toLowerCase().includes(searchTerm)) {
            return true;
        }

        // Check if any serial number contains search term
        if (warranty.serial_numbers && Array.isArray(warranty.serial_numbers)) {
            if (warranty.serial_numbers.some(sn => sn && sn.toLowerCase().includes(searchTerm))) {
                return true;
            }
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

        // Vendor filter
        if (currentFilters.vendor !== 'all' && (warranty.vendor || '').toLowerCase() !== currentFilters.vendor.toLowerCase()) {
            return false;
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
            // Check if vendor contains search term
            const vendorMatch = warranty.vendor && warranty.vendor.toLowerCase().includes(searchTerm);
            // Check if any serial number contains search term
            const serialNumberMatch = warranty.serial_numbers && Array.isArray(warranty.serial_numbers) &&
                warranty.serial_numbers.some(sn => sn && sn.toLowerCase().includes(searchTerm));
            // Return true if any match
            if (!productNameMatch && !tagMatch && !notesMatch && !vendorMatch && !serialNumberMatch) {
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
    // Populate new duration fields
    document.getElementById('editWarrantyDurationYears').value = warranty.warranty_duration_years || 0;
    document.getElementById('editWarrantyDurationMonths').value = warranty.warranty_duration_months || 0;
    document.getElementById('editWarrantyDurationDays').value = warranty.warranty_duration_days || 0;
    
    document.getElementById('editPurchasePrice').value = warranty.purchase_price || '';
    document.getElementById('editVendor').value = warranty.vendor || '';
    
    // Clear existing serial number inputs
    const editSerialNumbersContainer = document.getElementById('editSerialNumbersContainer');
    editSerialNumbersContainer.innerHTML = '';

    // Normalize serial_numbers to array of strings if needed
    if (Array.isArray(warranty.serial_numbers) && warranty.serial_numbers.length > 0 && typeof warranty.serial_numbers[0] === 'object') {
        warranty.serial_numbers = warranty.serial_numbers
            .map(snObj => snObj && snObj.serial_number)
            .filter(sn => typeof sn === 'string' && sn.trim() !== '');
    }

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
                    <a href="#" class="view-document-link" onclick="openSecureFile('${warranty.invoice_path}'); return false;">View</a>
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
                    <a href="#" class="view-document-link" onclick="openSecureFile('${warranty.manual_path}'); return false;">View</a>
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

    // Show current other document if exists
    const currentOtherDocumentElement = document.getElementById('currentOtherDocument'); 
    const deleteOtherDocumentBtn = document.getElementById('deleteOtherDocumentBtn'); 
    if (currentOtherDocumentElement && deleteOtherDocumentBtn) { 
        if (warranty.other_document_path && warranty.other_document_path !== 'null') { 
            currentOtherDocumentElement.innerHTML = ` 
                <span class="text-success">
                    <i class="fas fa-check-circle"></i> Current other document: 
                    <a href="#" class="view-document-link" onclick="openSecureFile('${warranty.other_document_path}'); return false;">View</a>
                    (Upload a new file to replace)
                </span>
            `; 
            deleteOtherDocumentBtn.style.display = ''; 
        } else { 
            currentOtherDocumentElement.innerHTML = '<span>No other document uploaded</span>'; 
            deleteOtherDocumentBtn.style.display = 'none'; 
        } 
        // Reset delete state
        deleteOtherDocumentBtn.dataset.delete = 'false'; 
        deleteOtherDocumentBtn.onclick = function() { 
            deleteOtherDocumentBtn.dataset.delete = 'true'; 
            currentOtherDocumentElement.innerHTML = '<span class="text-danger">Other document will be deleted on save</span>'; 
            deleteOtherDocumentBtn.style.display = 'none'; 
        }; 
    } 
    
    // Reset file inputs
    document.getElementById('editInvoice').value = '';
    document.getElementById('editManual').value = '';
    document.getElementById('editOtherDocument').value = ''; 
    document.getElementById('editFileName').textContent = '';
    document.getElementById('editManualFileName').textContent = '';
    document.getElementById('editOtherDocumentFileName').textContent = ''; 
    
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

    const editOtherDocumentInput = document.getElementById('editOtherDocument'); 
    if (editOtherDocumentInput) { 
        editOtherDocumentInput.addEventListener('change', function(event) { 
            updateFileName(event, 'editOtherDocument', 'editOtherDocumentFileName'); 
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

    // --- Set Lifetime Checkbox and Toggle Duration Fields ---
    if (editIsLifetimeCheckbox && editWarrantyDurationFields) {
        editIsLifetimeCheckbox.checked = warranty.is_lifetime || false;
        handleEditLifetimeChange(); // Call handler to set initial state

        // Remove previous listener if exists
        editIsLifetimeCheckbox.removeEventListener('change', handleEditLifetimeChange);
        // Add new listener
        editIsLifetimeCheckbox.addEventListener('change', handleEditLifetimeChange);

        // Set duration values only if NOT lifetime
        if (!warranty.is_lifetime) {
            document.getElementById('editWarrantyDurationYears').value = warranty.warranty_duration_years || 0;
            document.getElementById('editWarrantyDurationMonths').value = warranty.warranty_duration_months || 0;
            document.getElementById('editWarrantyDurationDays').value = warranty.warranty_duration_days || 0;
        } else {
            document.getElementById('editWarrantyDurationYears').value = '';
            document.getElementById('editWarrantyDurationMonths').value = '';
            document.getElementById('editWarrantyDurationDays').value = '';
        }
    } else {
        console.error("Lifetime warranty elements or duration fields not found in edit form");
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

    if (formData.has('other_document') && formData.get('other_document').size > 0) { 
        totalSize += formData.get('other_document').size; 
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
function handleFormSubmit(event) { // Renamed from submitForm
    event.preventDefault();
    
    const isLifetime = isLifetimeCheckbox.checked;
    const years = parseInt(warrantyDurationYearsInput.value || 0);
    const months = parseInt(warrantyDurationMonthsInput.value || 0);
    const days = parseInt(warrantyDurationDaysInput.value || 0);

    // --- Updated Lifetime Check ---
    if (!isLifetime && years === 0 && months === 0 && days === 0) {
        showToast('Warranty duration (years, months, or days) is required unless it\'s a lifetime warranty', 'error');
        switchToTab(1); // Switch to warranty details tab
        // Optionally focus the first duration input
        if (warrantyDurationYearsInput) warrantyDurationYearsInput.focus();
        // Add invalid class to the container or individual inputs if needed
        if (warrantyDurationFields) warrantyDurationFields.classList.add('invalid-duration'); // Example
        return;
    } else {
         if (warrantyDurationFields) warrantyDurationFields.classList.remove('invalid-duration');
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
    
    // Product URL handling
    let productUrlValue = formData.get('product_url');
    if (productUrlValue && typeof productUrlValue === 'string') {
        productUrlValue = productUrlValue.trim();
        if (productUrlValue && !productUrlValue.startsWith('http://') && !productUrlValue.startsWith('https://')) {
            formData.set('product_url', 'https://' + productUrlValue);
        } else if (productUrlValue) {
            // Ensure trimmed value is set back if it was already valid
            formData.set('product_url', productUrlValue);
        }
    }
    
    // Remove old warranty_years if it exists in formData (it shouldn't if HTML is correct)
    formData.delete('warranty_years'); 
    
    // Append new duration fields (already handled by FormData constructor if names match)
    // formData.append('warranty_duration_years', years);
    // formData.append('warranty_duration_months', months);
    // formData.append('warranty_duration_days', days);
    
    // Add serial numbers to form data (using correct name 'serial_numbers[]')
    const serialInputs = document.querySelectorAll('#serialNumbersContainer input[name="serial_numbers[]"]');
    // Clear existing serial_numbers[] from formData before appending new ones
    formData.delete('serial_numbers[]'); 
    serialInputs.forEach(input => {
        if (input.value.trim()) {
            formData.append('serial_numbers[]', input.value.trim()); // Use [] for arrays
        }
    });
    
    // Add tag IDs to form data as JSON string
    if (selectedTags && selectedTags.length > 0) {
        const tagIds = selectedTags.map(tag => tag.id);
        formData.append('tag_ids', JSON.stringify(tagIds));
    } else {
        formData.append('tag_ids', JSON.stringify([])); // Send empty array if no tags
    }
    
    // --- Ensure is_lifetime is correctly added ---
    // FormData already includes it if the checkbox is checked. If not checked, it's omitted.
    // We need to explicitly add 'false' if it's not checked.
    if (!isLifetimeCheckbox.checked) {
        formData.append('is_lifetime', 'false');
    } else {
        // Ensure duration fields are 0 if lifetime is checked
        formData.set('warranty_duration_years', '0');
        formData.set('warranty_duration_months', '0');
        formData.set('warranty_duration_days', '0');
    }

    // Add other_document file
    const otherDocumentFile = document.getElementById('otherDocument').files[0]; 
    if (otherDocumentFile) { 
        formData.append('other_document', otherDocumentFile); 
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

        loadWarranties().then(() => {
            applyFilters();
        }); // Reload the list and update UI
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
        // REMOVED: loadWarranties(); // Now called after authStateReady
        // REMOVED: loadViewPreference(); // Now called after authStateReady
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
        form.addEventListener('submit', handleFormSubmit); // Use renamed handler
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

    // REMOVED: updateCurrencySymbols(); // Now called after authStateReady
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
    if (!tab) {
        console.warn('validateEditTab: Could not find tab with ID:', tabId);
        return false; // Or true, depending on desired behavior for missing tabs
    }
    let isTabValid = true;

    // Get all relevant form controls within the tab
    const controls = tab.querySelectorAll('input, textarea, select');

    controls.forEach(control => {
        // Check the native HTML5 validity state
        if (!control.validity.valid) {
            isTabValid = false;
            control.classList.add('invalid');
            // Optionally, you could add logic here to display specific messages
            // or rely on browser default behavior if the form is submitted.
        } else {
            control.classList.remove('invalid');
        }
    });

    // Update the tab button to show completion status
    const tabBtn = document.querySelector(`.edit-tab-btn[data-tab="${tabId}"]`);
    if (tabBtn) {
        if (isTabValid) {
            tabBtn.classList.add('completed');
        } else {
            tabBtn.classList.remove('completed');
        }
    }
    return isTabValid;
}

// Add this function for secure file access
function openSecureFile(filePath) {
    if (!filePath || filePath === 'null') {
        console.error('Invalid file path:', filePath);
        showToast('Invalid file path', 'error');
        return false;
    }
    
    console.log('Opening secure file:', filePath);
    
    // Get the file name from the path, handling both uploads/ prefix and direct filenames
    let fileName = filePath;
    if (filePath.startsWith('uploads/')) {
        fileName = filePath.substring(8); // Remove 'uploads/' prefix
    } else if (filePath.startsWith('/uploads/')) {
        fileName = filePath.substring(9); // Remove '/uploads/' prefix
    }
    
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
            if (response.status === 404) {
                throw new Error('File not found. It may have been deleted or moved.');
            } else if (response.status === 401) {
                throw new Error('Authentication error. Please log in again.');
            } else {
                throw new Error(`Error: ${response.status} ${response.statusText}`);
            }
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

    if (document.getElementById('otherDocument')) { 
        document.getElementById('otherDocument').addEventListener('change', function(event) { 
            updateFileName(event, 'otherDocument', 'otherDocumentFileName'); 
        }); 
    } 
    
    // Initialize tag functionality
    initTagFunctionality();
    
    // Form submission
    if (warrantyForm) {
        warrantyForm.addEventListener('submit', handleFormSubmit); // Use renamed handler
    }

    // Initialize lifetime checkbox listener
    if (isLifetimeCheckbox && warrantyDurationFields) { // Check for new container
        isLifetimeCheckbox.addEventListener('change', handleLifetimeChange);
        handleLifetimeChange(); // Initial check
    } else {
        console.error("Lifetime warranty elements or duration fields not found in add form");
    }
}

// Initialize tag functionality
function initTagFunctionality() {
    // This function now ONLY sets up listeners for the main "Add Warranty" form's tag interface.
    // Assumes globalTagManagementModal listeners (new tag form, close buttons) are set up separately if the modal exists.

    // Get main form tag elements
    const mainFormTagSearch = document.getElementById('tagSearch');
    const mainFormTagsList = document.getElementById('tagsList'); // Dropdown for search in main form
    const mainFormManageTagsBtn = document.getElementById('manageTagsBtn'); // "Manage Tags" button in main form
    const mainFormSelectedTagsContainer = document.getElementById('selectedTags'); // Container for selected tags in main form

    // Skip if main form specific tag elements don't exist
    if (!mainFormTagSearch || !mainFormTagsList || !mainFormManageTagsBtn || !mainFormSelectedTagsContainer) {
        console.log('Main form tag UI elements (tagSearch, tagsList, manageTagsBtn, or selectedTagsContainer) not found, skipping main form tag UI initialization.');
        return;
    }

    console.log('Initializing main form tag UI functionality (search, selection, manage button).');

    // Load allTags if not already loaded (needed for search suggestions in the main form)
    if (allTags.length === 0) {
        loadTags(); // loadTags is async
    }

    mainFormTagSearch.addEventListener('focus', () => {
        renderTagsList(); // Renders suggestions into mainFormTagsList based on allTags
        mainFormTagsList.classList.add('show');
    });

    mainFormTagSearch.addEventListener('input', () => {
        renderTagsList(mainFormTagSearch.value); // Filters suggestions
    });

    // Hide main form's tag suggestion dropdown when clicking outside
    document.addEventListener('click', (e) => {
        // Check if mainFormTagSearch and mainFormTagsList are still valid (e.g. not removed from DOM)
        if (mainFormTagSearch && mainFormTagsList && 
            !mainFormTagSearch.contains(e.target) && 
            !mainFormTagsList.contains(e.target)) {
            mainFormTagsList.classList.remove('show');
        }
    });

    // "Manage Tags" button in the main form opens the global tagManagementModal
    mainFormManageTagsBtn.addEventListener('click', (e) => {
        e.preventDefault();
        openTagManagementModal(); // This function shows the global modal
    });

    // Initial rendering of selected tags for the main form (if any are pre-selected or loaded)
    renderSelectedTags(); // Renders into mainFormSelectedTagsContainer
}

// Function to load all tags
async function loadTags() {
    console.log('[script.js] loadTags() called. Current page:', window.location.pathname);
    
    // Check if tags are already loaded and reasonably populated
    if (allTags && allTags.length > 0) {
        console.log('[script.js] Tags already loaded in allTags global. Skipping fetch. Count:', allTags.length);
        // Optionally, re-dispatch the event if other components might need it on subsequent (though now less likely) calls
        // document.dispatchEvent(new CustomEvent('allTagsLoaded', { detail: allTags }));
        return;
    }

    try {
        const token = auth.getToken();
        if (!token) {
            console.warn('[script.js] No token available for loadTags. User might not be authenticated yet.');
            allTags = []; // Ensure allTags is empty if we can't load
            return;
        }
        const response = await fetch('/api/tags', {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) {
            const errorText = await response.text();
            console.error('[script.js] Failed to load tags:', response.status, errorText);
            allTags = []; // Default to empty on error
            return;
        }
        const fetchedTags = await response.json();
        // Assuming fetchedTags is an array of {id, name, color, ...} as expected by other functions
        allTags = fetchedTags;
        console.log('[script.js] All tags loaded into global allTags variable:', allTags.length, 'tags. Sample:', allTags.slice(0,2));
        // Dispatch event for any components that might be waiting for tags (e.g., Tagify instances)
        document.dispatchEvent(new CustomEvent('allTagsLoaded', { detail: allTags }));

    } catch (error) {
        console.error('[script.js] Error in loadTags():', error);
        allTags = []; // Default to empty on critical error
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
    tagManagementModal.classList.add('active');
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
    // --- Global Manage Tags Button ---
    const globalManageTagsBtn = document.getElementById('globalManageTagsBtn');
    if (globalManageTagsBtn) {
        globalManageTagsBtn.addEventListener('click', async () => {
            // Ensure allTags are loaded before opening the modal
            if (!allTags || allTags.length === 0) {
                showLoadingSpinner();
                try {
                    await loadTags();
                } catch (error) {
                    console.error("Failed to load tags before opening modal:", error);
                    showToast("Could not load tags. Please try again.", "error");
                    hideLoadingSpinner();
                    return;
                }
                hideLoadingSpinner();
            }
            openTagManagementModal();
        });
    }
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
                    // AND the modal is the 'addWarrantyModal' or 'editModal', then DO NOTHING.
                    if ((modalToClose.id === 'addWarrantyModal' || modalToClose.id === 'editModal') && e.target === modalToClose) {
                        return; // Ignore backdrop click for addWarrantyModal and editModal
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
    const vendorFilter = document.getElementById('vendorFilter'); // Added vendor filter select
    
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
    
    if (vendorFilter) { // Added event listener for vendor filter
        vendorFilter.addEventListener('change', () => {
            currentFilters.vendor = vendorFilter.value;
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
    if (saveWarrantyBtn) {
        let functionToAttachOnClick = saveWarranty; // Default to the original saveWarranty from script.js

        // Check if the observer setup function from status.js is available
        if (typeof window.setupSaveWarrantyObserver === 'function') {
            console.log('[script.js] window.setupSaveWarrantyObserver (from status.js) was FOUND. Attempting to wrap local saveWarranty function.');
            try {
                // Call the observer setup function, passing it the original saveWarranty from this script.
                // The observer setup function is expected to return a new function that wraps the original.
                functionToAttachOnClick = window.setupSaveWarrantyObserver(saveWarranty);
                
                // Optional: A flag to let status.js know that script.js has handled the wrapping.
                // This can be useful if status.js has any fallback/polling logic to prevent double-wrapping.
                window.saveWarrantyObserverAttachedByScriptJS = true; 
                console.log('[script.js] Local saveWarranty function has been successfully WRAPPED by the observer from status.js.');
            } catch (e) {
                console.error('[script.js] An error occurred while trying to wrap saveWarranty with the observer from status.js:', e);
                // If an error occurs during wrapping, functionToAttachOnClick will remain the original saveWarranty.
            }
        } else {
            console.log('[script.js] window.setupSaveWarrantyObserver (from status.js) was NOT FOUND. Using the original saveWarranty function for the button.');
        }

        // Add the event listener using the (potentially) wrapped function.
        saveWarrantyBtn.addEventListener('click', () => {
            console.log('[script.js] Save button (saveWarrantyBtn) clicked. Invoking the determined save function (functionToAttachOnClick).');
            if (typeof functionToAttachOnClick === 'function') {
                functionToAttachOnClick(); // Execute the determined save function
            } else {
                console.error('[script.js] CRITICAL: functionToAttachOnClick is not a function when save button was clicked!');
            }
        });

    } else {
        console.warn('[script.js] saveWarrantyBtn DOM element not found. Cannot attach click listener.');
    }
    
    // Confirm delete button
    const confirmDeleteBtn = document.getElementById('confirmDeleteBtn');
    if (confirmDeleteBtn) confirmDeleteBtn.addEventListener('click', deleteWarranty);
    
    // Load saved view preference
    // loadViewPreference(); // Disabled: now called after authStateReady
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

        // --- BEGIN FIX: Update UI immediately ---
        // Remove the deleted warranty from the global array
        const deletedId = currentWarrantyId; // Store ID before resetting
        warranties = warranties.filter(warranty => warranty.id !== deletedId);
        currentWarrantyId = null; // Reset current ID

        // Re-render the list using the updated local array
        applyFilters();
        // --- END FIX ---
    })
    .catch(error => {
        hideLoadingSpinner();
        console.error('Error deleting warranty:', error);
        showToast('Failed to delete warranty', 'error');
    });
}

// Save warranty updates
function saveWarranty() {
    console.log("[script.js] CORE saveWarranty (original from script.js) EXECUTING.");
    if (!currentWarrantyId) {
        showToast('No warranty selected for update', 'error');
        return;
    }
    
    // --- Get form values ---
    const productName = document.getElementById('editProductName').value.trim();
    const purchaseDate = document.getElementById('editPurchaseDate').value;
    const isLifetime = document.getElementById('editIsLifetime').checked;
    // Get new duration values
    const years = parseInt(document.getElementById('editWarrantyDurationYears').value || 0);
    const months = parseInt(document.getElementById('editWarrantyDurationMonths').value || 0);
    const days = parseInt(document.getElementById('editWarrantyDurationDays').value || 0);
    
    // Basic validation
    if (!productName) {
        showToast('Product name is required', 'error');
        return;
    }
    
    if (!purchaseDate) {
        showToast('Purchase date is required', 'error');
        return;
    }
    
    // --- Updated Validation ---
    if (!isLifetime && years === 0 && months === 0 && days === 0) {
        showToast('Warranty duration (years, months, or days) is required unless it\'s a lifetime warranty', 'error');
        // Optional: focus the years input again
        const yearsInput = document.getElementById('editWarrantyDurationYears');
        if (yearsInput) { // Check if element exists
            yearsInput.focus();
            // Add invalid class to container or inputs
            if (editWarrantyDurationFields) editWarrantyDurationFields.classList.add('invalid-duration');
        }
        return;
    } else {
         if (editWarrantyDurationFields) editWarrantyDurationFields.classList.remove('invalid-duration');
    }
    // --- End Updated Validation ---
    
    // Create form data
    const formData = new FormData();
    formData.append('product_name', productName);
    formData.append('purchase_date', purchaseDate);
    
    // Optional fields
    let productUrl = document.getElementById('editProductUrl').value.trim();
    if (productUrl) {
        if (!productUrl.startsWith('http://') && !productUrl.startsWith('https://')) {
            productUrl = 'https://' + productUrl;
        }
        formData.append('product_url', productUrl);
    }
    
    const purchasePrice = document.getElementById('editPurchasePrice').value;
    if (purchasePrice) {
        formData.append('purchase_price', purchasePrice);
    }
    
    // Serial numbers (use correct name 'serial_numbers[]')
    const serialInputs = document.querySelectorAll('#editSerialNumbersContainer input[name="serial_numbers[]"]');
    // Clear existing before appending
    formData.delete('serial_numbers[]'); 
    serialInputs.forEach(input => {
        if (input.value.trim()) {
            formData.append('serial_numbers[]', input.value.trim()); // Use []
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

    const otherDocumentFile = document.getElementById('editOtherDocument').files[0]; 
    if (otherDocumentFile) { 
        formData.append('other_document', otherDocumentFile); 
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
    const deleteOtherDocumentBtn = document.getElementById('deleteOtherDocumentBtn'); 
    if (deleteOtherDocumentBtn && deleteOtherDocumentBtn.dataset.delete === 'true') { 
        formData.append('delete_other_document', 'true'); 
    } 
    
    // --- Append is_lifetime and duration components ---
    formData.append('is_lifetime', isLifetime.toString());
    if (!isLifetime) {
        formData.append('warranty_duration_years', years);
        formData.append('warranty_duration_months', months);
        formData.append('warranty_duration_days', days);
    } else {
        // Ensure duration is 0 if lifetime
        formData.append('warranty_duration_years', 0);
        formData.append('warranty_duration_months', 0);
        formData.append('warranty_duration_days', 0);
    }
    // Add notes
    const notes = document.getElementById('editNotes').value;
    if (notes && notes.trim() !== '') {
        formData.append('notes', notes);
    } else {
        // Explicitly clear notes if empty
        formData.append('notes', '');
    }
    
    // Add vendor/retailer to form data
    const editVendorInput = document.getElementById('editVendor'); // Use the correct ID
    formData.append('vendor', editVendorInput ? editVendorInput.value.trim() : ''); // Use the correct variable
    
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
        // Instantly reload and re-render the warranties list
        loadWarranties().then(() => {
            applyFilters();
            // Always close the notes modal if open, to ensure UI is in sync
            const notesModal = document.getElementById('notesModal');
            if (notesModal && notesModal.style.display === 'block') {
                notesModal.style.display = 'none';
            }

            // --- NEW: Refresh expanded details row if open and keep it open ---
            // Find the row with details-expanded class (if any)
            let expandedWarrantyId = null;
            const expandedRow = document.querySelector('tr.details-expanded');
            if (expandedRow) {
                // Try to get the warranty id from the row (assume data-warranty-id or from first cell if needed)
                expandedWarrantyId = expandedRow.dataset.warrantyId;
                if (!expandedWarrantyId) {
                    // Fallback: try to get from first cell if id is rendered there
                    const firstCell = expandedRow.querySelector('td');
                    if (firstCell && firstCell.dataset && firstCell.dataset.warrantyId) {
                        expandedWarrantyId = firstCell.dataset.warrantyId;
                    }
                }
                // If still not found, try to match by product name and purchase date (less robust)
                if (!expandedWarrantyId && typeof allWarranties !== 'undefined') {
                    const productName = expandedRow.cells[0]?.textContent?.trim();
                    const purchaseDate = expandedRow.cells[1]?.textContent?.trim();
                    const match = allWarranties.find(w => w.product_name === productName && w.purchase_date && purchaseDate && w.purchase_date.startsWith(purchaseDate));
                    if (match) expandedWarrantyId = match.id;
                }
            }

            // After re-render, re-expand the row for the same warranty ID
            if (expandedWarrantyId) {
                // Wait for DOM update (next tick)
                setTimeout(() => {
                    // Find the new row for this warranty ID
                    // Try by data-warranty-id attribute
                    let newRow = document.querySelector(`tr[data-warranty-id="${expandedWarrantyId}"]`);
                    // If not found, try to match by product name and purchase date (fallback)
                    if (!newRow) {
                        const allRows = document.querySelectorAll('tr');
                        for (const row of allRows) {
                            const productName = row.cells?.[0]?.textContent?.trim();
                            const purchaseDate = row.cells?.[1]?.textContent?.trim();
                            const match = allWarranties.find(w => w.id == expandedWarrantyId && w.product_name === productName && w.purchase_date && purchaseDate && w.purchase_date.startsWith(purchaseDate));
                            if (match) {
                                newRow = row;
                                break;
                            }
                        }
                    }
                    if (newRow) {
                        // Expand the details for this row
                        if (typeof window.toggleWarrantyDetails === 'function') {
                            window.toggleWarrantyDetails(expandedWarrantyId, newRow);
                        } else if (typeof toggleWarrantyDetails === 'function') {
                            toggleWarrantyDetails(expandedWarrantyId, newRow);
                        }
                        newRow.classList.add('details-expanded');
                    }
                }, 0);
            }
            // --- END NEW ---
        });
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
    // Add options to the dropdown
    sortedTags.forEach(tag => {
        const option = document.createElement('option');
        option.value = tag.id;
        option.textContent = tag.name; // Reverted to textContent
        // Apply background color directly for now, acknowledging potential contrast issues
        // option.style.backgroundColor = tag.color; // Removed to prevent individual option background colors
        tagFilter.appendChild(option);
    });
}

// Function to populate vendor filter dropdown
function populateVendorFilter() {
    const vendorFilterElement = document.getElementById('vendorFilter');
    if (!vendorFilterElement) return;

    // Clear existing options (except "All Vendors")
    while (vendorFilterElement.options.length > 1) {
        vendorFilterElement.remove(1);
    }

    // Create a Set to store unique vendor names (case-insensitive)
    const uniqueVendors = new Set();

    // Collect all unique, non-empty vendors from warranties
    warranties.forEach(warranty => {
        if (warranty.vendor && warranty.vendor.trim() !== '') {
            uniqueVendors.add(warranty.vendor.trim().toLowerCase());
        }
    });

    // Sort vendors alphabetically (after converting back to original case for display if needed, or just use lowercase)
    // For simplicity, we'll sort the lowercase versions and display them as is.
    // If original casing is important, a map could be used to store original values.
    const sortedVendors = Array.from(uniqueVendors).sort((a, b) => a.localeCompare(b));

    // Add options to the dropdown
    sortedVendors.forEach(vendor => {
        const option = document.createElement('option');
        option.value = vendor; // Use lowercase for value consistency
        // Capitalize first letter for display
        option.textContent = vendor.charAt(0).toUpperCase() + vendor.slice(1);
        vendorFilterElement.appendChild(option);
    });
}

// --- Updated Function ---
function handleLifetimeChange(event) {
    const checkbox = event ? event.target : isLifetimeCheckbox;
    const durationFields = warrantyDurationFields; // Use new container ID
    const yearsInput = warrantyDurationYearsInput;
    const monthsInput = warrantyDurationMonthsInput;
    const daysInput = warrantyDurationDaysInput;

    if (!checkbox || !durationFields || !yearsInput || !monthsInput || !daysInput) {
        console.error("Lifetime or duration elements not found in add form");
        return;
    }

    if (checkbox.checked) {
        durationFields.style.display = 'none';
        // Clear and make duration fields not required
        yearsInput.required = false;
        monthsInput.required = false;
        daysInput.required = false;
        yearsInput.value = '';
        monthsInput.value = '';
        daysInput.value = '';
    } else {
        durationFields.style.display = 'block';
        // Make duration fields required (or handle validation differently)
        // Note: Backend validation ensures at least one is > 0 if not lifetime
        yearsInput.required = false; // Let backend handle combined validation
        monthsInput.required = false;
        daysInput.required = false;
    }
}

// --- Updated Function ---
function handleEditLifetimeChange(event) {
    const checkbox = event ? event.target : editIsLifetimeCheckbox;
    const durationFields = editWarrantyDurationFields; // Use new container ID
    const yearsInput = editWarrantyDurationYearsInput;
    const monthsInput = editWarrantyDurationMonthsInput;
    const daysInput = editWarrantyDurationDaysInput;

    if (!checkbox || !durationFields || !yearsInput || !monthsInput || !daysInput) {
        console.error("Lifetime or duration elements not found in edit form");
        return;
    }

    if (checkbox.checked) {
        durationFields.style.display = 'none';
        // Clear and make duration fields not required
        yearsInput.required = false;
        monthsInput.required = false;
        daysInput.required = false;
        yearsInput.value = '';
        monthsInput.value = '';
        daysInput.value = '';
    } else {
        durationFields.style.display = 'block';
        // Make duration fields required (or handle validation differently)
        yearsInput.required = false; // Let backend handle combined validation
        monthsInput.required = false;
        daysInput.required = false;
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
    if (manualFileName) manualFileName.textContent = '';
    if (otherDocumentFileName) otherDocumentFileName.textContent = ''; 

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
    if (manualFileName) manualFileName.textContent = '';
    if (otherDocumentFileName) otherDocumentFileName.textContent = ''; 

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
                    // *** ADD CHECK: Do NOT close addWarrantyModal or editModal via this general listener for backdrop clicks ***
                    if ((modalToClose.id === 'addWarrantyModal' || modalToClose.id === 'editModal') && e.target === modalToClose) {
                        return; // Ignore backdrop clicks for the add and edit modals here
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

            // Add a small delay to ensure backend has processed the data
            await new Promise(resolve => setTimeout(resolve, 500));
            
            // Await the warranties load to ensure UI is updated
            await loadWarranties();
            
            // Force a UI refresh by reapplying filters
            applyFilters();
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

    // Check for view preference changes
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

    // --- Added: Check for date format changes ---
    if (event.key === 'dateFormat' && event.newValue) {
        console.log(`Storage event detected for dateFormat. New value: ${event.newValue}`);
        // Re-apply filters to re-render warranties with the new date format
        if (warrantiesList) { // Only apply if the warranty list exists on the page
             applyFilters();
             showToast('Date format updated.', 'info'); // Optional: Notify user
        }
    }
    // --- End Added Check ---

    // --- Added: Check for currency symbol changes ---
    if (event.key === `${prefix}currencySymbol` && event.newValue) {
        console.log(`Storage event detected for ${prefix}currencySymbol. New value: ${event.newValue}`);
        if (warrantiesList) { // Only apply if on the main page
            updateCurrencySymbols(); // Update symbols outside cards (e.g., in forms if they exist)
            applyFilters(); // Re-render cards to update symbols inside them
            showToast('Currency symbol updated.', 'info'); // Optional: Notify user
        }
    }
    // --- End Added Check ---
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

        // Frontend check for invalid duration before attempting to save notes
        if (!notesModalWarrantyObj.is_lifetime &&
            (parseInt(notesModalWarrantyObj.warranty_duration_years) || 0) === 0 &&
            (parseInt(notesModalWarrantyObj.warranty_duration_months) || 0) === 0 &&
            (parseInt(notesModalWarrantyObj.warranty_duration_days) || 0) === 0) {
            showToast('Cannot save notes: The warranty has an invalid duration. Please edit the full warranty details to set a valid duration first.', 'error', 7000); // Longer toast duration
            return; // Prevent API call
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
                // Append duration components instead of warranty_years
                formData.append('warranty_duration_years', notesModalWarrantyObj.warranty_duration_years || 0);
                formData.append('warranty_duration_months', notesModalWarrantyObj.warranty_duration_months || 0);
                formData.append('warranty_duration_days', notesModalWarrantyObj.warranty_duration_days || 0);
            }
            if (notesModalWarrantyObj.product_url) {
                formData.append('product_url', notesModalWarrantyObj.product_url);
            }
            if (notesModalWarrantyObj.purchase_price !== null && notesModalWarrantyObj.purchase_price !== undefined) { // Check for null/undefined
                formData.append('purchase_price', notesModalWarrantyObj.purchase_price);
            }
            // Correctly append serial numbers
            if (notesModalWarrantyObj.serial_numbers && Array.isArray(notesModalWarrantyObj.serial_numbers)) {
                notesModalWarrantyObj.serial_numbers.forEach(sn => {
                    // Ensure sn is treated as a string before trim, and append with [] for array
                    if (sn && String(sn).trim() !== '') {
                        formData.append('serial_numbers[]', String(sn).trim());
                    }
                });
            }
            // If notesModalWarrantyObj.serial_numbers is empty or not an array, 
            // no 'serial_numbers[]' fields will be appended, which is typically interpreted as an empty list by backends.

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

            // Add vendor/retailer to form data
            const editVendorOrRetailer = document.getElementById('editVendorOrRetailer');
            formData.append('vendor', editVendorOrRetailer ? editVendorOrRetailer.value.trim() : '');

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

            // Refresh warranties list and THEN update UI
            await loadWarranties(); // Wait for data refresh
            applyFilters(); // Re-render the list with updated data

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
    // Use the global prefix determined after auth ready
    let prefix = userPreferencePrefix; // Use let to allow default override
     if (!prefix) {
         console.warn('[getCurrencySymbol] User preference prefix not set yet, defaulting prefix to user_');
         prefix = 'user_'; // Default prefix if called too early
    }
    console.log(`[getCurrencySymbol] Using determined prefix: ${prefix}`);
    let symbol = '$'; // Default value

    const rawValue = localStorage.getItem(`${prefix}currencySymbol`);
    console.log(`[getCurrencySymbol Debug] Raw value read from localStorage key '${prefix}currencySymbol':`, rawValue);
    // +++ END ADDED LOG +++

    // --- Priority 1: Load from individual key --- (Saved by settings-new.js)
    const individualSymbol = rawValue; // Use the already read value
    if (individualSymbol) { // Check uses the already read value
        symbol = individualSymbol;
        console.log(`[getCurrencySymbol] Loaded symbol from individual key (${prefix}currencySymbol): ${symbol}`);
        return symbol;
    }

    // --- Priority 2: Load from preferences object (Legacy/Fallback) ---
    try {
        const prefsString = localStorage.getItem(`${prefix}preferences`);
        console.log(`[getCurrencySymbol] Read prefsString for ${prefix}preferences:`, prefsString);
        if (prefsString) {
            const prefs = JSON.parse(prefsString);
            if (prefs && prefs.currency_symbol) {
                symbol = prefs.currency_symbol;
                console.log(`[getCurrencySymbol] Loaded symbol from object key (${prefix}preferences): ${symbol}`);
            }
        }
    } catch (e) {
        console.error(`Error reading ${prefix}preferences from localStorage:`, e);
        // Keep the default '$' symbol in case of error parsing the object
    }

    console.log(`[getCurrencySymbol] Returning symbol (default or from object): ${symbol}`);
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

// +++ NEW FUNCTION TO LOAD PREFS AND SAVE TO LOCALSTORAGE +++
async function loadAndApplyUserPreferences() {
    // Use the global prefix determined after auth ready
    let prefix = userPreferencePrefix; // <<< CHANGED const to let
    if (!prefix) {
         console.error('[Prefs Loader] Cannot load preferences: User preference prefix not set yet. Defaulting to user_');
         // Setting a default might be risky if the user *is* admin but prefix wasn't set in time.
         // Consider how authStateReady ensures prefix is set before this runs.
         // For now, let's try defaulting, but this might need review.
         prefix = 'user_'; 
    }
    console.log(`[Prefs Loader] Attempting to load preferences using prefix: ${prefix}`);
    
    if (window.auth && window.auth.isAuthenticated()) {
        const token = window.auth.getToken();
        if (!token) {
            console.error('[Prefs Loader] Cannot load preferences: No auth token found.');
            return; // Exit if no token
        }
        
        try {
            const response = await fetch('/api/auth/preferences', {
                headers: {
                    'Authorization': `Bearer ${token}`
                }
            });

            if (response.ok) {
                const apiPrefs = await response.json();
                console.log('[Prefs Loader] Preferences loaded from API:', apiPrefs);

                // Save relevant prefs to localStorage
                if (apiPrefs.currency_symbol) {
                    localStorage.setItem(`${prefix}currencySymbol`, apiPrefs.currency_symbol);
                    console.log(`[Prefs Loader] Saved ${prefix}currencySymbol: ${apiPrefs.currency_symbol}`);
                }
                if (apiPrefs.default_view) {
                    localStorage.setItem(`${prefix}defaultView`, apiPrefs.default_view);
                     console.log(`[Prefs Loader] Saved ${prefix}defaultView: ${apiPrefs.default_view}`);
                }
                if (apiPrefs.expiring_soon_days !== undefined) {
                    localStorage.setItem(`${prefix}expiringSoonDays`, apiPrefs.expiring_soon_days);
                    // Also update the global variable used by processWarrantyData
                    expiringSoonDays = apiPrefs.expiring_soon_days;
                    console.log(`[Prefs Loader] Saved ${prefix}expiringSoonDays: ${apiPrefs.expiring_soon_days}`);
                    console.log(`[Prefs Loader] Updated global expiringSoonDays variable to: ${expiringSoonDays}`);
                }
                if (apiPrefs.date_format) {
                    localStorage.setItem('dateFormat', apiPrefs.date_format);
                    console.log(`[Prefs Loader] Saved dateFormat: ${apiPrefs.date_format}`);
                }
                
                // Optionally trigger immediate UI updates if needed, although renderWarranties will use these new values
                // updateCurrencySymbols(); 

            } else {
                const errorData = await response.json().catch(() => ({}));
                console.warn(`[Prefs Loader] Failed to load preferences from API: ${response.status}`, errorData.message || '');
                // Set defaults in localStorage maybe?
                if (!localStorage.getItem('dateFormat')) localStorage.setItem('dateFormat', 'MDY');
                if (!localStorage.getItem(`${prefix}currencySymbol`)) localStorage.setItem(`${prefix}currencySymbol`, '$');
                // etc.
            }
        } catch (error) {
            console.error('[Prefs Loader] Error fetching/applying preferences from API:', error);
            // Set defaults in localStorage on error?
            if (!localStorage.getItem('dateFormat')) localStorage.setItem('dateFormat', 'MDY');
            if (!localStorage.getItem(`${prefix}currencySymbol`)) localStorage.setItem(`${prefix}currencySymbol`, '$');
            // etc.
        }
    } else {
        console.warn('[Prefs Loader] Cannot load preferences: User not authenticated or auth module not available.');
        // Apply defaults if not authenticated?
         if (!localStorage.getItem('dateFormat')) localStorage.setItem('dateFormat', 'MDY');
         if (!localStorage.getItem(`${prefix}currencySymbol`)) localStorage.setItem(`${prefix}currencySymbol`, '$');
         // etc.
    }
}
// +++ END NEW FUNCTION +++
