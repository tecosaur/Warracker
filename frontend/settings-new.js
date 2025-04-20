// DOM Elements
const darkModeToggle = document.getElementById('darkModeToggle');
const darkModeToggleSetting = document.getElementById('darkModeToggleSetting');
const defaultViewSelect = document.getElementById('defaultView');
const emailNotificationsToggle = document.getElementById('emailNotifications');
const expiringSoonDaysInput = document.getElementById('expiringSoonDays');
const notificationFrequencySelect = document.getElementById('notificationFrequency');
const notificationTimeInput = document.getElementById('notificationTime');
const timezoneSelect = document.getElementById('timezone');
const saveProfileBtn = document.getElementById('saveProfileBtn');
const savePreferencesBtn = document.getElementById('savePreferencesBtn');
const saveEmailSettingsBtn = document.getElementById('saveEmailSettingsBtn');
const changePasswordBtn = document.getElementById('changePasswordBtn');
const passwordChangeForm = document.getElementById('passwordChangeForm');
const savePasswordBtn = document.getElementById('savePasswordBtn');
const cancelPasswordBtn = document.getElementById('cancelPasswordBtn');
const deleteAccountBtn = document.getElementById('deleteAccountBtn');
const deleteAccountModal = document.getElementById('deleteAccountModal');
const deleteConfirmInput = document.getElementById('deleteConfirmInput');
const confirmDeleteAccountBtn = document.getElementById('confirmDeleteAccountBtn');
const passwordSuccessModal = document.getElementById('passwordSuccessModal');
const loadingContainer = document.getElementById('loadingContainer');
const toastContainer = document.getElementById('toastContainer');
const settingsBtn = document.getElementById('settingsBtn');
const settingsMenu = document.getElementById('settingsMenu');
const usersTableBody = document.getElementById('usersTableBody');

// Form fields
const firstNameInput = document.getElementById('firstName');
const lastNameInput = document.getElementById('lastName');
const emailInput = document.getElementById('email');
const currentPasswordInput = document.getElementById('currentPassword');
const newPasswordInput = document.getElementById('newPassword');
const confirmPasswordInput = document.getElementById('confirmPassword');

// DOM Elements for admin section
const adminSection = document.getElementById('adminSection');
const refreshUsersBtn = document.getElementById('refreshUsersBtn');
const checkAdminBtn = document.getElementById('checkAdminBtn');
const showUsersBtn = document.getElementById('showUsersBtn');
const testApiBtn = document.getElementById('testApiBtn');
const triggerNotificationsBtn = document.getElementById('triggerNotificationsBtn');
const registrationEnabled = document.getElementById('registrationEnabled');
const saveSiteSettingsBtn = document.getElementById('saveSiteSettingsBtn');
const emailBaseUrlInput = document.getElementById('emailBaseUrl'); // Added for email base URL

/**
 * Set theme (dark/light) - Unified and persistent
 * @param {boolean} isDark - Whether to use dark mode
 */
function setTheme(isDark) {
    const theme = isDark ? 'dark' : 'light';
    // Apply theme to document
    document.documentElement.setAttribute('data-theme', theme);
    if (isDark) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    // Save to localStorage (single source of truth)
    localStorage.setItem('darkMode', isDark);
    // Sync both toggles if present
    if (typeof darkModeToggle !== 'undefined' && darkModeToggle) {
        darkModeToggle.checked = isDark;
    }
    if (typeof darkModeToggleSetting !== 'undefined' && darkModeToggleSetting) {
        darkModeToggleSetting.checked = isDark;
    }
    // Also update user_preferences.theme for backward compatibility
    try {
        let userPrefs = {};
        const storedPrefs = localStorage.getItem('user_preferences');
        if (storedPrefs) {
            userPrefs = JSON.parse(storedPrefs);
        }
        userPrefs.theme = theme;
        localStorage.setItem('user_preferences', JSON.stringify(userPrefs));
    } catch (e) {
        console.error('Error updating theme in user_preferences:', e);
    }
}

/**
 * Initialize dark mode toggle and synchronize state
 */
function initDarkModeToggle() {
    // Always check the single source of truth in localStorage
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    // Apply theme to DOM if not already set
    document.documentElement.setAttribute('data-theme', isDarkMode ? 'dark' : 'light');
    document.body.classList.toggle('dark-mode', isDarkMode);
    // Sync both toggles
    if (typeof darkModeToggle !== 'undefined' && darkModeToggle) {
        darkModeToggle.checked = isDarkMode;
        darkModeToggle.addEventListener('change', function() {
            setTheme(this.checked);
        });
    }
    if (typeof darkModeToggleSetting !== 'undefined' && darkModeToggleSetting) {
        darkModeToggleSetting.checked = isDarkMode;
        darkModeToggleSetting.addEventListener('change', function() {
            setTheme(this.checked);
        });
    }
}

// Initialize settings page
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing settings page');
    
    // Set up event listeners
    setupEventListeners(); // Ensure this doesn't also try to init settings menu
    
    // Set up direct event listeners for critical elements
    setupCriticalEventListeners();
    
    // Make functions globally accessible if needed
    window.deleteUser = deleteUser;
    window.directDeleteUserAPI = directDeleteUserAPI;
    
    // Add global click handlers if needed
    // ... (existing delete button handler logic) ...

    // Initialize dark mode toggle
    initDarkModeToggle();
    
    // REMOVED initSettingsMenu() call - Handled by auth.js

    // Load initial data for the settings page
    loadUserData();
    loadTimezones().then(() => loadPreferences()).catch(err => {
        console.error('Error loading timezones/prefs:', err);
        loadPreferences(); // Try loading prefs anyway
    });
});

/**
 * Initialize the settings page
 */
function initPage() {
    console.log('Initializing settings page');
    
    // Check authentication
    if (window.auth) {
        window.auth.checkAuthState();
        
        // Redirect to login if not authenticated
        if (!window.auth.isAuthenticated()) {
            console.log('User not authenticated, redirecting to login');
            window.location.href = 'login.html';
            return;
        }
    } else {
        // Auth module not loaded
        console.error('Auth module not loaded');
        window.location.href = 'login.html';
        return;
    }
    
    // Load user data and preferences with error handling
    try {
        // First load timezones, then load preferences to ensure correct order
        loadTimezones().then(() => {
            console.log('Timezones loaded, now loading preferences');
            loadPreferences();
        }).catch(err => {
            console.error('Error loading timezones:', err);
            // Still try to load preferences even if timezones fail
            loadPreferences();
        });
        
        loadUserData().catch(err => {
            console.error('Error loading user data:', err);
            // Continue with page initialization even if user data fails
        });
    } catch (err) {
        console.error('Error during page initialization:', err);
        // Continue despite errors to allow basic functionality
    }
    
    // Fix for settings button - not needed anymore as we've removed it
    if (settingsBtn) {
        console.log('Settings button found, adding event listener');
        settingsBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            settingsMenu.classList.toggle('active');
            console.log('Settings button clicked, menu toggled');
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
        console.log('Settings button not found - this is expected after UI update');
    }
    
    console.log('Settings page initialization complete');
}

/**
 * Setup critical event listeners that must work for core functionality
 */
function setupCriticalEventListeners() {
    console.log('Setting up critical event listeners');
    
    // Set up delete user modal close buttons
    const closeModalButtons = document.querySelectorAll('.close-modal');
    closeModalButtons.forEach(button => {
        button.addEventListener('click', function() {
            closeAllModals();
        });
    });
    
    // Set up delete user button in the modal
    const confirmDeleteUserBtn = document.getElementById('confirmDeleteUserBtn');
    if (confirmDeleteUserBtn) {
        console.log('Setting up confirmDeleteUserBtn');
        
        // Add multiple event handlers for redundancy
        confirmDeleteUserBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Delete button clicked via addEventListener in setupCriticalEventListeners');
            deleteUser();
            return false;
        });
        
        confirmDeleteUserBtn.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Delete button clicked via onclick in setupCriticalEventListeners');
            deleteUser();
            return false;
        };
    }
    
    // Set up direct delete link
    const directDeleteLink = document.getElementById('directDeleteLink');
    if (directDeleteLink) {
        directDeleteLink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Direct delete link clicked in setupCriticalEventListeners');
            deleteUser();
            return false;
        });
    }
    
    // Set up direct API link
    const directAPILink = document.getElementById('directAPILink');
    if (directAPILink) {
        directAPILink.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Direct API link clicked in setupCriticalEventListeners');
            const userId = window.currentDeleteUserId || 
                          (document.getElementById('deleteUserId') ? document.getElementById('deleteUserId').value : null);
            directDeleteUserAPI(userId);
            return false;
        });
    }
    
    // Set up delete user form
    const deleteUserForm = document.getElementById('deleteUserForm');
    if (deleteUserForm) {
        deleteUserForm.addEventListener('submit', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Delete user form submitted in setupCriticalEventListeners');
            deleteUser();
            return false;
        });
    }
}

/**
 * Load user data from localStorage and API
 */
async function loadUserData() {
    showLoading();
    // Get the new display elements
    const userNameDisplay = document.getElementById('currentUserNameDisplay');
    const userEmailDisplay = document.getElementById('currentUserEmailDisplay');

    try {
        // Get user from localStorage first
        const currentUser = window.auth.getCurrentUser();

        if (currentUser) {
            // Populate form fields
            if (firstNameInput) firstNameInput.value = currentUser.first_name || ''; // Add null checks
            if (lastNameInput) lastNameInput.value = currentUser.last_name || ''; // Add null checks
            if (emailInput) emailInput.value = currentUser.email || ''; // Add null checks

            // --- UPDATE DISPLAY ELEMENT (Initial Load) ---
            const displayName = `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim() || currentUser.username || 'User';
            if (userNameDisplay) userNameDisplay.textContent = displayName;
            if (userEmailDisplay) userEmailDisplay.textContent = currentUser.email || 'N/A';
            // --- END UPDATE ---

            // Check if user is admin and show admin section
            if (currentUser.is_admin) {
                if (adminSection) adminSection.style.display = 'block';
                if (adminSection && adminSection.style.display === 'block') {
                     if (usersTableBody) loadUsers();
                     if (registrationEnabled) loadSiteSettings();
                }
            }
        }

        // Fetch fresh user data from API
        try {
            const response = await fetch('/api/auth/user', {
                method: 'GET',
                headers: {
                    'Authorization': `Bearer ${window.auth.getToken()}`
                }
            });

            if (response.ok) {
                const userData = await response.json();

                // Update form fields with fresh data
                if (firstNameInput) firstNameInput.value = userData.first_name || ''; // Add null checks
                if (lastNameInput) lastNameInput.value = userData.last_name || ''; // Add null checks
                if (emailInput) emailInput.value = userData.email || ''; // Add null checks

                // --- UPDATE DISPLAY ELEMENT (After API Load) ---
                const displayName = `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || userData.username || 'User';
                 if (userNameDisplay) userNameDisplay.textContent = displayName;
                 if (userEmailDisplay) userEmailDisplay.textContent = userData.email || 'N/A';
                // --- END UPDATE ---

                // Show admin section if user is admin
                if (userData.is_admin) {
                     if (adminSection) adminSection.style.display = 'block';
                     if (adminSection && adminSection.style.display === 'block') {
                         if (usersTableBody) loadUsers();
                         if (registrationEnabled) loadSiteSettings();
                     }
                }

                // Update localStorage
                localStorage.setItem('user_info', JSON.stringify(userData));
            } else {
                const errorData = await response.json().catch(() => ({ message: 'Failed to parse error response' }));
                console.warn('API error fetching user data:', errorData.message);
                 if (!currentUser) {
                    showToast(errorData.message || 'Failed to load fresh user data', 'warning');
                 }
            }
        } catch (apiError) {
            console.warn('API error, using localStorage data:', apiError);
             if (!currentUser) {
                 showToast('Could not connect to fetch user data. Displaying cached info.', 'warning');
             }
        }
    } catch (error) {
        console.error('Error loading user data:', error);
        showToast('Failed to load user data. Please try again.', 'error');
        if (userNameDisplay) userNameDisplay.textContent = 'Error';
        if (userEmailDisplay) userEmailDisplay.textContent = 'Error';
    } finally {
        hideLoading();
    }
}

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

/**
 * Load user preferences
 */
function loadPreferences() {
    console.log('Loading preferences...');
    showLoading();
    
    // Get the appropriate key prefix based on user type
    const prefix = getPreferenceKeyPrefix();
    console.log(`Loading preferences with prefix: ${prefix}`);
    
    // First check if we're in dark mode by checking the body class
    const isDarkMode = document.body.classList.contains('dark-mode');
    
    // Set the toggle state based on the current theme
    if (darkModeToggle) {
        darkModeToggle.checked = isDarkMode;
    }
    
    if (darkModeToggleSetting) {
        darkModeToggleSetting.checked = isDarkMode;
    }
    
    // --- BEGIN EDIT: Load Default View with Priority ---
    let defaultViewLoaded = false;
    if (defaultViewSelect) {
        const userSpecificView = localStorage.getItem(`${prefix}defaultView`);
        const generalView = localStorage.getItem('viewPreference');
        const legacyWarrantyView = localStorage.getItem(`${prefix}warrantyView`); // Check legacy key

        if (userSpecificView) {
            defaultViewSelect.value = userSpecificView;
            defaultViewLoaded = true;
            console.log(`Loaded default view from ${prefix}defaultView:`, userSpecificView);
        } else if (generalView) {
            defaultViewSelect.value = generalView;
            defaultViewLoaded = true;
            console.log('Loaded default view from viewPreference:', generalView);
        } else if (legacyWarrantyView) {
            defaultViewSelect.value = legacyWarrantyView;
            defaultViewLoaded = true;
            console.log(`Loaded default view from legacy ${prefix}warrantyView:`, legacyWarrantyView);
        }
    }
    // --- END EDIT ---

    // Load other preferences from localStorage using the appropriate prefix (only if default view not loaded yet)
    if (!defaultViewLoaded) {
        try {
            const userPrefs = localStorage.getItem(`${prefix}preferences`);
            if (userPrefs) {
                const preferences = JSON.parse(userPrefs);

                // Default view preference (load only if not loaded above)
                if (defaultViewSelect && preferences.default_view && !defaultViewLoaded) {
                    defaultViewSelect.value = preferences.default_view;
                    defaultViewLoaded = true; // Mark as loaded
                    console.log(`Loaded default view from ${prefix}preferences object:`, preferences.default_view);
                }

                // Email notifications preference
                if (emailNotificationsToggle && typeof preferences.email_notifications !== 'undefined') { // Check for undefined
                    emailNotificationsToggle.checked = preferences.email_notifications;
                }

                // Expiring soon days preference
                if (expiringSoonDaysInput && preferences.expiring_soon_days) {
                    expiringSoonDaysInput.value = preferences.expiring_soon_days;
                }

                // Notification frequency preference
                if (notificationFrequencySelect && preferences.notification_frequency) {
                    notificationFrequencySelect.value = preferences.notification_frequency;
                }

                // Notification time preference
                if (notificationTimeInput && preferences.notification_time) {
                    notificationTimeInput.value = preferences.notification_time;
                }

                // Timezone preference
                if (timezoneSelect && preferences.timezone) {
                    timezoneSelect.value = preferences.timezone;
                }
            }
        } catch (e) {
            console.error('Error loading preferences from localStorage:', e);
        }
    }

    // Load preferences from API (API data should override if available, except maybe for default view if already loaded)
    fetch('/api/auth/preferences', {
        method: 'GET',
        headers: {
            'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Failed to load preferences from API');
        }
        return response.json();
    })
    .then(data => {
        console.log('Preferences loaded from API:', data);
        
        // API returns preferences directly, not nested under a 'preferences' key
        const apiPrefs = data;
        
        // Update UI with API preferences
        // Default View: Only update if not already loaded from higher priority localStorage keys
        if (defaultViewSelect && apiPrefs.default_view && !defaultViewLoaded) {
            defaultViewSelect.value = apiPrefs.default_view;
            console.log('Loaded default view from API:', apiPrefs.default_view);
        }
        
        // Other preferences always updated from API if available
        if (emailNotificationsToggle && typeof apiPrefs.email_notifications !== 'undefined') { // Check for undefined
            emailNotificationsToggle.checked = apiPrefs.email_notifications;
        }
        
        if (expiringSoonDaysInput && apiPrefs.expiring_soon_days) {
            expiringSoonDaysInput.value = apiPrefs.expiring_soon_days;
        }
        
        if (notificationFrequencySelect && apiPrefs.notification_frequency) {
            notificationFrequencySelect.value = apiPrefs.notification_frequency;
        }
        
        if (notificationTimeInput && apiPrefs.notification_time) {
            notificationTimeInput.value = apiPrefs.notification_time;
        }
        
        if (timezoneSelect && apiPrefs.timezone) {
            console.log('API provided timezone:', apiPrefs.timezone);
            // Will be populated once timezones are loaded
            setTimeout(() => {
                if (timezoneSelect.options.length > 1) {
                    timezoneSelect.value = apiPrefs.timezone;
                    console.log('Applied timezone from API:', apiPrefs.timezone, 'Current select value:', timezoneSelect.value);
                }
            }, 500);
        }
        
        // Store in localStorage with the appropriate prefix
        localStorage.setItem(`${prefix}preferences`, JSON.stringify(apiPrefs));
    })
    .catch(error => {
        console.error('Error loading preferences from API:', error);
    })
    .finally(() => {
        hideLoading();
    });
}

/**
 * Setup event listeners for the settings page
 */
function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // Set up user menu button click handler
    const userMenuBtn = document.getElementById('userMenuBtn');
    const userMenuDropdown = document.getElementById('userMenuDropdown');
    
    if (userMenuBtn && userMenuDropdown) {
        console.log('Setting up user menu button click handler');
        
        // Toggle dropdown when user button is clicked
        userMenuBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            userMenuDropdown.classList.toggle('active');
        });
        
        // Close dropdown when clicking outside
        document.addEventListener('click', function(e) {
            if (userMenuDropdown.classList.contains('active') && 
                !userMenuDropdown.contains(e.target) && 
                !userMenuBtn.contains(e.target)) {
                userMenuDropdown.classList.remove('active');
            }
        });
    }
    
    // Dark mode toggle in header (no longer exists)
    if (darkModeToggle) {
        darkModeToggle.addEventListener('change', function() {
            setTheme(this.checked);
            
            // Also update the settings page toggle
            if (darkModeToggleSetting) {
                darkModeToggleSetting.checked = this.checked;
            }
        });
    }
    
    // Dark mode toggle in settings
    if (darkModeToggleSetting) {
        darkModeToggleSetting.addEventListener('change', function() {
            setTheme(this.checked);
            
            // Also update the header toggle if it exists
            if (darkModeToggle) {
                darkModeToggle.checked = this.checked;
            }
        });
    }
    
    // Save profile button
    if (saveProfileBtn) {
        saveProfileBtn.addEventListener('click', saveProfile);
    }
    
    // Save preferences button
    if (savePreferencesBtn) {
        savePreferencesBtn.addEventListener('click', savePreferences);
    }
    
    // Change password button
    if (changePasswordBtn) {
        changePasswordBtn.addEventListener('click', function() {
            passwordChangeForm.style.display = 'block';
            this.style.display = 'none';
        });
    }
    
    // Save password button
    if (savePasswordBtn) {
        savePasswordBtn.addEventListener('click', changePassword);
    }
    
    // Cancel password button
    if (cancelPasswordBtn) {
        cancelPasswordBtn.addEventListener('click', function() {
            resetPasswordForm();
            passwordChangeForm.style.display = 'none';
            changePasswordBtn.style.display = 'block';
        });
    }
    
    // Delete account button
    if (deleteAccountBtn) {
        deleteAccountBtn.addEventListener('click', function() {
            openModal(deleteAccountModal);
        });
    }
    
    // Delete confirm input
    if (deleteConfirmInput) {
        deleteConfirmInput.addEventListener('input', function() {
            confirmDeleteAccountBtn.disabled = this.value !== 'DELETE';
        });
    }
    
    // Confirm delete account button
    if (confirmDeleteAccountBtn) {
        confirmDeleteAccountBtn.addEventListener('click', deleteAccount);
    }
    
    // Add event listener for logout menu item
    const logoutMenuItem = document.getElementById('logoutMenuItem');
    if (logoutMenuItem) {
        logoutMenuItem.addEventListener('click', function() {
            if (window.auth && window.auth.logout) {
                window.auth.logout();
            }
        });
    }
    
    // Admin section buttons
    if (refreshUsersBtn) {
        refreshUsersBtn.addEventListener('click', function() {
            loadUsers();
        });
    }
    
    if (checkAdminBtn) {
        checkAdminBtn.addEventListener('click', function() {
            checkAdminPermissions();
        });
    }
    
    if (showUsersBtn) {
        showUsersBtn.addEventListener('click', function() {
            showUsersList();
        });
    }
    
    if (testApiBtn) {
        testApiBtn.addEventListener('click', function() {
            checkApiEndpoint();
        });
    }
    
    if (triggerNotificationsBtn) {
        triggerNotificationsBtn.addEventListener('click', function() {
            triggerWarrantyNotifications();
        });
    }
    
    // Site settings save button
    if (saveSiteSettingsBtn) {
        saveSiteSettingsBtn.addEventListener('click', function() {
            saveSiteSettings();
        });
    }
    
    // Save email settings button
    if (saveEmailSettingsBtn) {
        saveEmailSettingsBtn.addEventListener('click', saveEmailSettings);
    }
    
    console.log('Event listeners setup complete');
}

/**
 * Initialize modals
 */
function initModals() {
    // Close modal when clicking on X or outside
    document.querySelectorAll('.close-btn, [data-dismiss="modal"]').forEach(closeBtn => {
        closeBtn.addEventListener('click', () => {
            document.querySelectorAll('.modal-backdrop').forEach(modal => {
                modal.style.display = 'none';
            });
            
            // Reset delete confirm input
            if (deleteConfirmInput) {
                deleteConfirmInput.value = '';
                confirmDeleteAccountBtn.disabled = true;
            }
            
            // Reset password form
            resetPasswordForm();
        });
    });
    
    // Close modal when clicking outside
    window.addEventListener('click', (event) => {
        document.querySelectorAll('.modal-backdrop').forEach(modal => {
            if (event.target === modal) {
                modal.style.display = 'none';
                
                // Reset delete confirm input
                if (deleteConfirmInput) {
                    deleteConfirmInput.value = '';
                    confirmDeleteAccountBtn.disabled = true;
                }
                
                // Reset password form
                resetPasswordForm();
            }
        });
    });
    
    // Add direct click handler to delete user modal
    if (deleteUserModal) {
        console.log('Adding click handler to deleteUserModal');
        deleteUserModal.addEventListener('click', function(event) {
            // Check if the click was on the confirm delete button
            if (event.target && event.target.id === 'confirmDeleteUserBtn') {
                event.preventDefault();
                console.log('Confirm delete button clicked through modal event delegation');
                deleteUser();
            }
        });
    } else {
        console.error('deleteUserModal not found in initModals');
    }
}

/**
 * Open a modal
 * @param {HTMLElement} modal - The modal to open
 */
function openModal(modal) {
    console.log('Opening modal:', modal.id, 'Current display:', modal.style.display);
    
    // First close all modals
    closeAllModals();
    
    // Then open this modal
    modal.style.display = 'flex';
    console.log('Modal display after opening:', modal.style.display);
    
    // If this is the delete user modal, set up the delete button
    if (modal.id === 'deleteUserModal') {
        console.log('This is the delete user modal, setting up delete button');
        // Use setTimeout to ensure the DOM is fully updated
        setTimeout(() => {
            setupDeleteButton();
        }, 100);
    }
}

/**
 * Reset password form
 */
function resetPasswordForm() {
    currentPasswordInput.value = '';
    newPasswordInput.value = '';
    confirmPasswordInput.value = '';
}

/**
 * Save user profile
 */
async function saveProfile() {
    // Validate form
    if (!firstNameInput || !lastNameInput || !firstNameInput.value.trim() || !lastNameInput.value.trim()) { // Add null checks for inputs
        showToast('Please fill in First Name and Last Name', 'error');
        return;
    }

    showLoading();
    // Get the display element
    const userNameDisplay = document.getElementById('currentUserNameDisplay');

    try {
        const response = await fetch('/api/auth/profile', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                first_name: firstNameInput.value.trim(),
                last_name: lastNameInput.value.trim()
            })
        });

        if (response.ok) {
            const userData = await response.json();

            // Update localStorage
            const currentUser = window.auth.getCurrentUser();
            const updatedUser = {
                ...(currentUser || {}), // Handle case where currentUser might be null
                first_name: userData.first_name,
                last_name: userData.last_name,
                // Ensure email and username are preserved if they existed
                email: currentUser ? currentUser.email : userData.email,
                username: currentUser ? currentUser.username : userData.username,
                is_admin: currentUser ? currentUser.is_admin : userData.is_admin,
                id: currentUser ? currentUser.id : userData.id
            };
            localStorage.setItem('user_info', JSON.stringify(updatedUser));

            // --- UPDATE DISPLAY ELEMENT IMMEDIATELY ---
            const displayName = `${userData.first_name || ''} ${userData.last_name || ''}`.trim() || updatedUser.username || 'User'; // Use updatedUser for username fallback
            if (userNameDisplay) userNameDisplay.textContent = displayName;
            // --- END UPDATE ---

            // Update UI (Header, etc.) - Ensure auth module is loaded
            if (window.auth && window.auth.checkAuthState) {
                window.auth.checkAuthState(); // This should update the header menu
            } else {
                 console.warn("Auth module or checkAuthState not found, header might not update immediately.");
            }

            showToast('Profile updated successfully', 'success');
        } else {
            const errorData = await response.json().catch(() => ({ message: 'Failed to parse error response' }));

    throw new Error(errorData.message || 'Failed to update profile');
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showToast(`Failed to update profile: ${error.message}`, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Save user preferences
 */
function savePreferences() {
    showLoading();
    
    try {
        // Get the appropriate key prefix based on user type
        const prefix = getPreferenceKeyPrefix();
        console.log(`Saving preferences with prefix: ${prefix}`);
        
        // Get values
        const isDarkMode = darkModeToggleSetting.checked;
        const defaultView = defaultViewSelect.value;
        const emailNotifications = emailNotificationsToggle.checked;
        const expiringSoonDays = parseInt(expiringSoonDaysInput.value);
        const notificationFrequency = notificationFrequencySelect.value;
        const notificationTime = notificationTimeInput.value;
        const timezone = timezoneSelect.value;
        
        // Validate inputs
        if (isNaN(expiringSoonDays) || expiringSoonDays < 1 || expiringSoonDays > 365) {
            showToast('Expiring soon days must be between 1 and 365', 'error');
            hideLoading();
            return;
        }
        
        if (!timezone) {
            showToast('Please select a timezone', 'error');
            hideLoading();
            return;
        }
        
        // Create preferences object
        const preferences = {
            theme: isDarkMode ? 'dark' : 'light',
            default_view: defaultView,
            email_notifications: emailNotifications,
            expiring_soon_days: expiringSoonDays,
            notification_frequency: notificationFrequency,
            notification_time: notificationTime,
            timezone: timezone
        };
        
        // Save to API
        fetch('/api/auth/preferences', {
            method: 'PUT',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to save preferences');
            }
            return response.json();
        })
        .then(data => {
            // Save to localStorage with the appropriate prefix
            localStorage.setItem(`${prefix}preferences`, JSON.stringify(data));
            
            // Also save individual preferences for backward compatibility and general preference
            localStorage.setItem(`${prefix}defaultView`, defaultView);
            localStorage.setItem(`${prefix}warrantyView`, defaultView); // Keep saving legacy key for now
            localStorage.setItem(`${prefix}emailNotifications`, emailNotifications);
            localStorage.setItem('viewPreference', defaultView); // --- EDIT: Save general key ---
            
            // Save the dark mode setting for the current user type
            localStorage.setItem(`${prefix}darkMode`, isDarkMode);
            
            // Apply theme immediately
            document.body.classList.toggle('dark-mode', isDarkMode);
            
            showToast('Preferences saved successfully', 'success');
        })
        .catch(error => {
            console.error('Error saving preferences:', error);
            showToast('Error saving preferences', 'error');
            
            // Save to localStorage as fallback with the appropriate prefix
            localStorage.setItem(`${prefix}theme`, isDarkMode ? 'dark' : 'light');
            localStorage.setItem(`${prefix}defaultView`, defaultView);
            localStorage.setItem(`${prefix}warrantyView`, defaultView); // Keep saving legacy key for now
            localStorage.setItem(`${prefix}emailNotifications`, emailNotifications);
            localStorage.setItem(`${prefix}darkMode`, isDarkMode);
            localStorage.setItem('viewPreference', defaultView); // --- EDIT: Save general key ---
            
            // Apply theme even if API save fails
            document.body.classList.toggle('dark-mode', isDarkMode);
        })
        .finally(() => {
            hideLoading();
        });
    } catch (error) {
        console.error('Error in savePreferences:', error);
        showToast('Error saving preferences', 'error');
        hideLoading();
    }
}

/**
 * Change user password
 */
async function changePassword() {
    // Validate form
    if (!currentPasswordInput.value || !newPasswordInput.value || !confirmPasswordInput.value) {
        showToast('Please fill in all password fields', 'error');
        return;
    }
    
    if (newPasswordInput.value !== confirmPasswordInput.value) {
        showToast('New passwords do not match', 'error');
        return;
    }
    
    // Validate password strength
    if (newPasswordInput.value.length < 8) {
        showToast('Password must be at least 8 characters long', 'error');
        return;
    }
    
    showLoading();
    
    try {
        try {
            const response = await fetch('/api/auth/password/change', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${window.auth.getToken()}`,
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    current_password: currentPasswordInput.value,
                    new_password: newPasswordInput.value
                })
            });
            
            if (response.ok) {
                // Reset form and hide it
                resetPasswordForm();
                passwordChangeForm.style.display = 'none';
                changePasswordBtn.style.display = 'block';
                
                // Show success modal
                openModal(passwordSuccessModal);
            } else {
                // Handle error
                const errorData = await response.json();
                throw new Error(errorData.message || 'Failed to change password');
            }
        } catch (apiError) {
            console.warn('API error, showing offline message:', apiError);
            showToast('Password cannot be changed in offline mode', 'warning');
        }
    } catch (error) {
        console.error('Error changing password:', error);
        showToast('Failed to change password. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Delete user account
 */
async function deleteAccount() {
    if (deleteConfirmInput.value !== 'DELETE') {
        showToast('Please type DELETE to confirm', 'error');
        return;
    }
    
    showLoading();
    
    try {
        try {
            const response = await fetch('/api/auth/account', {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${window.auth.getToken()}`
                }
            });
            
            if (response.ok) {
                // Clear auth data
                if (window.auth.logout) {
                    window.auth.logout();
                } else {
                    localStorage.removeItem('auth_token');
                    localStorage.removeItem('user_info');
                }
                
                // Show success message
                showToast('Account deleted successfully', 'success');
                
                // Redirect to home page after a short delay
                setTimeout(() => {
                    window.location.href = 'index.html';
                }, 2000);
            } else {
                // Handle error
                const errorData = await response.json();
                throw new Error(errorData.message || 'Failed to delete account');
            }
        } catch (apiError) {
            console.warn('API error, showing offline message:', apiError);
            showToast('Account cannot be deleted in offline mode', 'warning');
        }
    } catch (error) {
        console.error('Error deleting account:', error);
        showToast('Failed to delete account. Please try again.', 'error');
    } finally {
        hideLoading();
        
        // Close modal
        deleteAccountModal.style.display = 'none';
        
        // Reset delete confirm input
        deleteConfirmInput.value = '';
        confirmDeleteAccountBtn.disabled = true;
    }
}

/**
 * Show loading spinner
 */
function showLoading() {
    loadingContainer.style.display = 'flex';
}

/**
 * Hide loading spinner
 */
function hideLoading() {
    loadingContainer.style.display = 'none';
}

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - The type of toast (info, success, error, warning)
 * @param {number} duration - Duration in milliseconds, 0 for no auto-hide
 * @returns {HTMLElement} - The toast element
 */
function showToast(message, type = 'info', duration = 5000) {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    
    const icon = document.createElement('i');
    switch (type) {
        case 'success':
            icon.className = 'fas fa-check-circle';
            break;
        case 'error':
            icon.className = 'fas fa-exclamation-circle';
            break;
        case 'warning':
            icon.className = 'fas fa-exclamation-triangle';
            break;
        default:
            icon.className = 'fas fa-info-circle';
    }
    
    const messageSpan = document.createElement('span');
    messageSpan.textContent = message;
    
    toast.appendChild(icon);
    toast.appendChild(messageSpan);
    
    toastContainer.appendChild(toast);
    
    // Add a method to remove the toast
    toast.remove = function() {
        toast.classList.add('toast-fade-out');
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    };
    
    // Auto-hide toast after specified duration (if not 0)
    if (duration > 0) {
        setTimeout(() => {
            toast.remove();
        }, duration);
    }
    
    return toast;
}

/**
 * Load users for admin
 */
async function loadUsers() {
    // Exit if usersTableBody doesn't exist
    if (!usersTableBody) {
        console.log('usersTableBody element not found, skipping loadUsers');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch('/api/admin/users', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });
        
        if (response.ok) {
            const users = await response.json();
            
            // Clear table
            usersTableBody.innerHTML = '';
            
            // Add users to table
            users.forEach(user => {
                const row = document.createElement('tr');
                
                // Username
                const usernameCell = document.createElement('td');
                usernameCell.textContent = user.username;
                row.appendChild(usernameCell);
                
                // Email
                const emailCell = document.createElement('td');
                emailCell.textContent = user.email;
                row.appendChild(emailCell);
                
                // Name
                const nameCell = document.createElement('td');
                const fullName = `${user.first_name || ''} ${user.last_name || ''}`.trim();
                nameCell.textContent = fullName || '-';
                row.appendChild(nameCell);
                
                // Status
                const statusCell = document.createElement('td');
                const statusBadge = document.createElement('span');
                statusBadge.className = `badge ${user.is_active ? 'badge-success' : 'badge-danger'}`;
                statusBadge.textContent = user.is_active ? 'Active' : 'Inactive';
                statusCell.appendChild(statusBadge);
                row.appendChild(statusCell);
                
                // Admin
                const adminCell = document.createElement('td');
                const adminBadge = document.createElement('span');
                adminBadge.className = `badge ${user.is_admin ? 'badge-primary' : 'badge-secondary'}`;
                adminBadge.textContent = user.is_admin ? 'Admin' : 'User';
                adminCell.appendChild(adminBadge);
                row.appendChild(adminCell);
                
                // Actions
                const actionsCell = document.createElement('td');
                
                // Edit button
                const editBtn = document.createElement('button');
                editBtn.className = 'btn btn-sm btn-outline-primary mr-2';
                editBtn.innerHTML = '<i class="fas fa-edit"></i>';
                editBtn.title = 'Edit User';
                editBtn.addEventListener('click', () => openEditUserModal(user));
                
                // Delete button
                const deleteBtn = document.createElement('button');
                deleteBtn.className = 'btn btn-sm btn-outline-danger';
                deleteBtn.innerHTML = '<i class="fas fa-trash-alt"></i>';
                deleteBtn.title = 'Delete User';
                
                // Add multiple event handlers for redundancy
                deleteBtn.addEventListener('click', (event) => {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('Delete button clicked for user:', user);
                    openDeleteUserModal(user);
                });
                
                // Also set onclick property
                deleteBtn.onclick = function(event) {
                    event.preventDefault();
                    event.stopPropagation();
                    console.log('Delete button onclick property triggered for user:', user);
                    openDeleteUserModal(user);
                    return false;
                };
                
                // Don't allow editing or deleting self
                const currentUser = window.auth.getCurrentUser();
                if (user.id === currentUser.id) {
                    editBtn.disabled = true;
                    deleteBtn.disabled = true;
                    editBtn.title = 'Cannot edit yourself';
                    deleteBtn.title = 'Cannot delete yourself';
                    console.log('Disabled edit/delete for current user:', currentUser.id);
                }
                
                actionsCell.appendChild(editBtn);
                actionsCell.appendChild(deleteBtn);
                row.appendChild(actionsCell);
                
                usersTableBody.appendChild(row);
            });
            
            console.log('Users loaded successfully:', users.length);
        } else {
            console.error('Failed to load users:', response.status);
            showToast('Failed to load users', 'error');
        }
    } catch (error) {
        console.error('Error loading users:', error);
        showToast('Error loading users', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Open edit user modal
 * @param {Object} user - The user to edit
 */
function openEditUserModal(user) {
    editUserId.value = user.id;
    editUsername.value = user.username;
    editEmail.value = user.email;
    editUserActive.checked = user.is_active;
    editUserAdmin.checked = user.is_admin;
    
    openModal(editUserModal);
}

/**
 * Save user changes
 */
async function saveUserChanges() {
    const userId = editUserId.value;
    
    if (!userId) {
        showToast('User ID is missing', 'error');
        return;
    }
    
    showLoading();
    
    try {
        const response = await fetch(`/api/admin/users/${userId}`, {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                is_active: editUserActive.checked,
                is_admin: editUserAdmin.checked
            })
        });
        
        if (response.ok) {
            showToast('User updated successfully', 'success');
            closeAllModals();
            loadUsers();
        } else {
            const errorData = await response.json();
            showToast(errorData.message || 'Failed to update user', 'error');
        }
    } catch (error) {
        console.error('Error updating user:', error);
        showToast('Failed to update user. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Open delete user modal
 * @param {Object} user - User object
 */
function openDeleteUserModal(user) {
    console.log('Opening delete modal for user:', user);
    
    // Store the user ID in a global variable for easier access
    window.currentDeleteUserId = user.id;
    console.log('Set global currentDeleteUserId to:', user.id);
    
    // Set the user ID in the form
    const deleteUserIdField = document.getElementById('deleteUserId');
    if (deleteUserIdField) {
        deleteUserIdField.value = user.id;
        console.log('Set deleteUserId field to:', user.id);
    } else {
        console.error('deleteUserId field not found in the DOM');
    }
    
    // Display user ID for debugging
    const displayUserIdField = document.getElementById('displayUserId');
    if (displayUserIdField) {
        displayUserIdField.textContent = user.id;
        console.log('Set displayUserId field to:', user.id);
    }
    
    // Also set in editUserId for backward compatibility
    if (editUserId) {
        editUserId.value = user.id;
        console.log('Set editUserId.value to:', user.id);
    }
    
    // Set the username in the modal
    const deleteUserNameElement = document.getElementById('deleteUserName');
    if (deleteUserNameElement) {
        deleteUserNameElement.textContent = user.username;
        console.log('Set deleteUserName to:', user.username);
    } else {
        console.error('deleteUserName element not found in the DOM');
    }
    
    // Make sure the modal is visible
    const deleteUserModal = document.getElementById('deleteUserModal');
    if (deleteUserModal) {
        // First ensure all modals are closed
        closeAllModals();
        
        // Then open this modal
        deleteUserModal.style.display = 'flex';
        console.log('Delete user modal opened');
        
        // Ensure the delete button has the correct click handler
        const confirmDeleteUserBtn = document.getElementById('confirmDeleteUserBtn');
        if (confirmDeleteUserBtn) {
            // Remove existing event listeners by cloning
            const newBtn = confirmDeleteUserBtn.cloneNode(true);
            confirmDeleteUserBtn.parentNode.replaceChild(newBtn, confirmDeleteUserBtn);
            
            // Add the click event listener
            newBtn.addEventListener('click', function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Delete button clicked for user ID:', user.id);
                deleteUser();
                return false;
            });
            
            // Also set the direct onclick attribute as a simple function call
            newBtn.setAttribute('onclick', 'console.log("Direct onclick attribute clicked"); deleteUser(); return false;');
            console.log('Added click event listener to delete button');
            
            // Add a direct click handler
            newBtn.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Direct onclick property handler clicked for user ID:', user.id);
                deleteUser();
                return false;
            };
        } else {
            console.error('confirmDeleteUserBtn not found in the DOM');
        }
        
        // Set up the direct delete link
        const directDeleteLink = document.getElementById('directDeleteLink');
        if (directDeleteLink) {
            directDeleteLink.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Direct delete link clicked for user ID:', user.id);
                deleteUser();
                return false;
            };
            console.log('Added onclick handler to direct delete link');
        }
        
        // Set up the direct API link
        const directAPILink = document.getElementById('directAPILink');
        if (directAPILink) {
            directAPILink.onclick = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Direct API link clicked for user ID:', user.id);
                directDeleteUserAPI(user.id);
                return false;
            };
            console.log('Added onclick handler to direct API link');
        }
        
        // Also set up form submit handler
        const deleteUserForm = document.getElementById('deleteUserForm');
        if (deleteUserForm) {
            deleteUserForm.onsubmit = function(e) {
                e.preventDefault();
                e.stopPropagation();
                console.log('Delete user form submitted for user ID:', user.id);
                deleteUser();
                return false;
            };
            console.log('Added onsubmit handler to delete user form');
        }
        
        // Add a direct click handler to the modal for event delegation
        deleteUserModal.addEventListener('click', function(e) {
            if (e.target && e.target.id === 'confirmDeleteUserBtn') {
                e.preventDefault();
                e.stopPropagation();
                console.log('Delete button clicked through modal event delegation for user ID:', user.id);
                deleteUser();
                return false;
            }
        });
    } else {
        console.error('deleteUserModal not found in the DOM');
    }
}

/**
 * Delete user
 */
function deleteUser() {
    console.log('=== DELETE USER FUNCTION STARTED ===');
    console.log('Function caller:', arguments.callee.caller ? arguments.callee.caller.name : 'unknown');
    
    try {
        // Get the user ID from various possible sources
        const userId = window.currentDeleteUserId || 
                    (document.getElementById('deleteUserId') ? document.getElementById('deleteUserId').value : null) ||
                    (document.getElementById('editUserId') ? document.getElementById('editUserId').value : null) ||
                    (document.getElementById('displayUserId') ? document.getElementById('displayUserId').textContent : null);
        
        console.log('Final User ID to delete:', userId);
        
        if (!userId) {
            showToast('User ID is missing', 'error');
            console.error('Delete user failed: User ID is missing');
            return;
        }
        
        console.log('Starting user deletion process for ID:', userId);
        showLoading();
        
        // Use our improved deletion function
        superEmergencyDelete(userId)
            .then(success => {
                if (success) {
                    console.log('User deletion successful');
                    showToast('User deleted successfully', 'success');
                    closeAllModals();
                    loadUsers(); // Refresh the user list
                    
                    // Refresh the users list if it's currently displayed
                    const usersModal = document.querySelector('div[style*="z-index: 10000"]');
                    if (usersModal) {
                        document.body.removeChild(usersModal);
                        showUsersList();
                    }
                } else {
                    console.error('User deletion failed');
                    showToast('Failed to delete user. Check console for details.', 'error');
                }
                hideLoading();
            })
            .catch(error => {
                console.error('Error during user deletion:', error);
                showToast('Error during user deletion: ' + error.message, 'error');
                hideLoading();
                
                // Try the direct API call as a fallback
                if (confirm('Would you like to try a direct API call to delete the user?')) {
                    const directToast = showToast(`Trying direct API call for user ID ${userId}...`, 'info', 0);
                    
                    directDeleteUserAPI(userId)
                        .then(directSuccess => {
                            directToast.remove();
                            
                            if (directSuccess) {
                                showToast(`User ID ${userId} deleted successfully with direct API call!`, 'success');
                                
                                // Refresh the users list if it's currently displayed
                                const usersModal = document.querySelector('div[style*="z-index: 10000"]');
                                if (usersModal) {
                                    document.body.removeChild(usersModal);
                                    setTimeout(() => {
                                        showUsersList();
                                    }, 500);
                                }
                            } else {
                                showToast(`Failed to delete user ${user.username} with direct API call.`, 'error');
                            }
                        })
                        .catch(error => {
                            directToast.remove();
                            console.error('Error with direct API call:', error);
                            showToast('Error with direct API call: ' + error.message, 'error');
                        });
                }
            })
            .catch(error => {
                console.error('Error checking if user exists:', error);
                showToast('Error checking if user exists: ' + error.message, 'error');
            });
    } catch (error) {
        console.error('Error in deleteUser function:', error);
        console.error('Error details:', error.message, error.stack);
        showToast('Failed to delete user. Please try again.', 'error');
        hideLoading();
    }
    
    console.log('=== DELETE USER FUNCTION COMPLETED ===');
}

/**
 * Super emergency delete function for user deletion
 * @param {string|number} userId - The user ID or username to delete
 * @returns {Promise<boolean>} - Promise that resolves to true if deletion was successful, false otherwise
 */
function superEmergencyDelete(userId) {
    console.log('=== SUPER EMERGENCY DELETE STARTED ===');
    console.log('User ID or username to delete:', userId);
    
    return new Promise((resolve, reject) => {
        if (!userId) {
            console.error('No user ID provided');
            reject(new Error('No user ID provided'));
            return;
        }
        
        // Check if the input is a username rather than a numeric ID
        if (isNaN(userId)) {
            console.log('Input appears to be a username, not a numeric ID');
            // Try to find the user ID by username using the Promise-based function
            findUserIdByUsernameAsync(userId)
                .then(numericId => {
                    if (numericId) {
                        console.log(`Found numeric ID ${numericId} for username ${userId}`);
                        // Call this function again with the numeric ID
                        return superEmergencyDelete(numericId);
                    } else {
                        throw new Error(`Could not find a user with username "${userId}"`);
                    }
                })
                .then(resolve)
                .catch(reject);
            return;
        }
        
        console.log('Proceeding with numeric user ID:', userId);
        
        // Get the token
        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.error('Authentication token is missing');
            reject(new Error('Authentication token is missing'));
            return;
        }
        
        // Create a new XMLHttpRequest
        const xhr = new XMLHttpRequest();
        xhr.open('DELETE', `/api/admin/users/${userId}`, true);
        
        // Set headers
        xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.setRequestHeader('Content-Type', 'application/json');
        xhr.setRequestHeader('Accept', 'application/json');
        
        // Set up event handlers
        xhr.onload = function() {
            console.log('XHR status:', xhr.status);
            console.log('XHR response text:', xhr.responseText);
            
            if (xhr.status >= 200 && xhr.status < 300) {
                console.log('User deletion successful');
                resolve(true);
            } else {
                console.error('User deletion failed with status:', xhr.status);
                let errorMessage = 'Unknown error';
                try {
                    const response = JSON.parse(xhr.responseText);
                    errorMessage = response.message || response.error || 'Unknown error';
                } catch (e) {
                    errorMessage = xhr.responseText || 'Unknown error';
                }
                console.error('Error message:', errorMessage);
                resolve(false); // Resolve with false instead of rejecting to handle the error in a controlled way
            }
        };
        
        xhr.onerror = function() {
            console.error('Network error during user deletion');
            reject(new Error('Network error during user deletion'));
        };
        
        xhr.ontimeout = function() {
            console.error('Request timeout during user deletion');
            reject(new Error('Request timeout during user deletion'));
        };
        
        // Send the request
        xhr.send();
        console.log('Delete request sent for user ID:', userId);
    });
}

/**
 * Find a user's numeric ID by their username
 * @param {string} username - The username to look up
 * @param {function} callback - Callback function that receives the numeric ID or null if not found
 */
function findUserIdByUsername(username, callback) {
    console.log('=== FIND USER ID BY USERNAME STARTED ===');
    console.log('Looking up user ID for username:', username);
    
    // Get the token
    const token = localStorage.getItem('auth_token');
    if (!token) {
        console.error('Authentication token is missing');
        callback(null);
        return;
    }
    
    // Fetch the list of users
    fetch('/api/admin/users', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            console.error('Failed to fetch users list:', response.status);
            callback(null);
            return null;
        }
        return response.json();
    })
    .then(users => {
        if (!users) {
            callback(null);
            return;
        }
        
        console.log('Fetched users list:', users);
        
        // Find the user with the matching username
        const user = users.find(u => u.username === username);
        
        if (user) {
            console.log('Found user:', user);
            callback(user.id);
        } else {
            console.error('User not found with username:', username);
            callback(null);
        }
    })
    .catch(error => {
        console.error('Error fetching users:', error);
        callback(null);
    });
    
    console.log('=== FIND USER ID BY USERNAME COMPLETED ===');
}

/**
 * Check admin permissions
 */
function checkAdminPermissions() {
    console.log('=== CHECK ADMIN PERMISSIONS STARTED ===');
    
    // Get the token
    const token = localStorage.getItem('auth_token');
    if (!token) {
        alert('Error: Authentication token is missing');
        return;
    }
    
    // Get the current user info
    const userInfo = JSON.parse(localStorage.getItem('user_info') || '{}');
    console.log('Current user info:', userInfo);
    
    // Check if the user is an admin
    if (userInfo.is_admin) {
        console.log('User is an admin');
        alert('You are an admin user');
    } else {
        console.log('User is not an admin');
        alert('You are not an admin user');
    }
    
    // Make a request to the admin endpoint to verify permissions
    fetch('/api/admin/users', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        console.log('Admin check response status:', response.status);
        
        if (response.ok) {
            console.log('Admin endpoint access successful');
            alert('You have access to the admin endpoint');
        } else {
            console.error('Admin endpoint access failed');
            alert('You do not have access to the admin endpoint');
        }
        
        return response.text().catch(() => '');
    })
    .then(text => {
        console.log('Admin check response text:', text);
    })
    .catch(error => {
        console.error('Admin check error:', error);
        alert('Error checking admin permissions: ' + error.message);
    });
    
    console.log('=== CHECK ADMIN PERMISSIONS COMPLETED ===');
}

/**
 * Show a list of users in the system
 */
function showUsersList() {
    console.log('=== SHOW USERS LIST STARTED ===');
    
    // Get the token
    const token = localStorage.getItem('auth_token');
    if (!token) {
        alert('Error: Authentication token is missing');
        return;
    }
    
    // Fetch the list of users
    fetch('/api/admin/users', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            console.error('Failed to fetch users list:', response.status);
            alert('Failed to fetch users list. Status: ' + response.status);
            return null;
        }
        return response.json();
    })
    .then(users => {
        if (!users) return;
        
        console.log('Fetched users list:', users);
        
        // Check if dark mode is enabled
        const isDarkMode = document.body.classList.contains('dark-mode');
        
        // Set colors based on theme
        const backgroundColor = isDarkMode ? '#333' : 'white';
        const textColor = isDarkMode ? '#fff' : '#000';
        const borderColor = isDarkMode ? '#555' : '#ddd';
        
        // Create a modal to display the users
        const modal = document.createElement('div');
        modal.style.position = 'fixed';
        modal.style.top = '0';
        modal.style.left = '0';
        modal.style.width = '100%';
        modal.style.height = '100%';
        modal.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        modal.style.display = 'flex';
        modal.style.justifyContent = 'center';
        modal.style.alignItems = 'center';
        modal.style.zIndex = '10000';
        
        // Create the modal content
        const modalContent = document.createElement('div');
        modalContent.style.backgroundColor = backgroundColor;
        modalContent.style.color = textColor;
        modalContent.style.padding = '20px';
        modalContent.style.borderRadius = '5px';
        modalContent.style.maxWidth = '80%';
        modalContent.style.maxHeight = '80%';
        modalContent.style.overflow = 'auto';
        
        // Create the modal header
        const modalHeader = document.createElement('div');
        modalHeader.style.display = 'flex';
        modalHeader.style.justifyContent = 'space-between';
        modalHeader.style.alignItems = 'center';
        modalHeader.style.marginBottom = '20px';
        
        // Create the modal title
        const modalTitle = document.createElement('h3');
        modalTitle.textContent = 'Users List';
        modalTitle.style.color = textColor;
        
        // Create the close button
        const closeButton = document.createElement('button');
        closeButton.textContent = '×';
        closeButton.style.backgroundColor = 'transparent';
        closeButton.style.border = 'none';
        closeButton.style.fontSize = '24px';
        closeButton.style.cursor = 'pointer';
        closeButton.style.color = textColor;
        closeButton.addEventListener('click', function() {
            document.body.removeChild(modal);
        });
        
        // Add the title and close button to the header
        modalHeader.appendChild(modalTitle);
        modalHeader.appendChild(closeButton);
        
        // Create the table
        const table = document.createElement('table');
        table.style.width = '100%';
        table.style.borderCollapse = 'collapse';
        
        // Create the table header
        const thead = document.createElement('thead');
        const headerRow = document.createElement('tr');
        
        // Create the header cells
        const headers = ['ID', 'Username', 'Email', 'Name', 'Admin', 'Active', 'Actions'];
        headers.forEach(headerText => {
            const th = document.createElement('th');
            th.textContent = headerText;
            th.style.padding = '10px';
            th.style.textAlign = 'left';
            th.style.borderBottom = `1px solid ${borderColor}`;
            th.style.color = textColor;
            headerRow.appendChild(th);
        });
        
        thead.appendChild(headerRow);
        table.appendChild(thead);
        
        // Create the table body
        const tbody = document.createElement('tbody');
        
        // Add a row for each user
        users.forEach(user => {
            const row = document.createElement('tr');
            
            // Create cells for each property
            const idCell = document.createElement('td');
            idCell.textContent = user.id;
            idCell.style.padding = '10px';
            idCell.style.borderBottom = `1px solid ${borderColor}`;
            idCell.style.color = textColor;
            
            const usernameCell = document.createElement('td');
            usernameCell.textContent = user.username;
            usernameCell.style.padding = '10px';
            usernameCell.style.borderBottom = `1px solid ${borderColor}`;
            usernameCell.style.color = textColor;
            
            const emailCell = document.createElement('td');
            emailCell.textContent = user.email;
            emailCell.style.padding = '10px';
            emailCell.style.borderBottom = `1px solid ${borderColor}`;
            emailCell.style.color = textColor;
            
            const nameCell = document.createElement('td');
            nameCell.textContent = `${user.first_name || ''} ${user.last_name || ''}`.trim() || '-';
            nameCell.style.padding = '10px';
            nameCell.style.borderBottom = `1px solid ${borderColor}`;
            nameCell.style.color = textColor;
            
            const adminCell = document.createElement('td');
            adminCell.textContent = user.is_admin ? 'Yes' : 'No';
            adminCell.style.padding = '10px';
            adminCell.style.borderBottom = `1px solid ${borderColor}`;
            adminCell.style.color = textColor;
            
            const activeCell = document.createElement('td');
            activeCell.textContent = user.is_active ? 'Yes' : 'No';
            activeCell.style.padding = '10px';
            activeCell.style.borderBottom = `1px solid ${borderColor}`;
            activeCell.style.color = textColor;
            
            const actionsCell = document.createElement('td');
            actionsCell.style.padding = '10px';
            actionsCell.style.borderBottom = `1px solid ${borderColor}`;
            
            // Create a delete button
            const deleteButton = document.createElement('button');
            deleteButton.textContent = 'Delete';
            deleteButton.style.backgroundColor = '#dc3545';
            deleteButton.style.color = 'white';
            deleteButton.style.border = 'none';
            deleteButton.style.padding = '5px 10px';
            deleteButton.style.borderRadius = '3px';
            deleteButton.style.cursor = 'pointer';
            
            // Don't allow deleting the current user
            const currentUser = JSON.parse(localStorage.getItem('user_info') || '{}');
            if (user.id === currentUser.id) {
                deleteButton.disabled = true;
                deleteButton.style.opacity = '0.5';
                deleteButton.style.cursor = 'not-allowed';
                deleteButton.title = 'Cannot delete yourself';
            } else {
                deleteButton.addEventListener('click', function() {
                    if (confirm(`Are you sure you want to delete user ${user.username} (ID: ${user.id})?`)) {
                        document.body.removeChild(modal);
                        
                        // First check if the user still exists
                        const checkingToast = showToast(`Checking if user ${user.username} still exists...`, 'info', 0);
                        
                        checkUserExists(user.id)
                            .then(existingUser => {
                                checkingToast.remove();
                                
                                if (!existingUser) {
                                    showToast(`User ${user.username} no longer exists`, 'warning');
                                    showUsersList(); // Refresh the list
                                    return;
                                }
                                
                                // User exists, proceed with deletion
                                testUserDeletion(user.id);
                            })
                            .catch(error => {
                                checkingToast.remove();
                                console.error('Error checking if user exists:', error);
                                showToast('Error checking if user exists: ' + error.message, 'error');
                                
                                // Ask if they want to try deletion anyway
                                if (confirm(`Error checking if user ${user.username} exists. Try deletion anyway?`)) {
                                    testUserDeletion(user.id);
                                } else {
                                    showUsersList(); // Refresh the list
                                }
                            });
                    }
                });
            }
            
            actionsCell.appendChild(deleteButton);
            
            // Add all cells to the row
            row.appendChild(idCell);
            row.appendChild(usernameCell);
            row.appendChild(emailCell);
            row.appendChild(nameCell);
            row.appendChild(adminCell);
            row.appendChild(activeCell);
            row.appendChild(actionsCell);
            
            // Add the row to the table body
            tbody.appendChild(row);
        });
        
        table.appendChild(tbody);
        
        // Add the header and table to the modal content
        modalContent.appendChild(modalHeader);
        modalContent.appendChild(table);
        
        // Add the modal content to the modal
        modal.appendChild(modalContent);
        
        // Add the modal to the page
        document.body.appendChild(modal);
        
        console.log('Users list displayed');
    })
    .catch(error => {
        console.error('Error fetching users:', error);
        alert('Error fetching users: ' + error.message);
    });
    
    console.log('=== SHOW USERS LIST COMPLETED ===');
}

/**
 * Promise-based version of findUserIdByUsername
 * @param {string} username - The username to look up
 * @returns {Promise<number|null>} - Promise that resolves to the user ID or null if not found
 */
function findUserIdByUsernameAsync(username) {
    return new Promise((resolve, reject) => {
        findUserIdByUsername(username, (err, userId) => {
            if (err) reject(err);
            else resolve(userId);
        });
    });
}

/**
 * Check if a user exists by ID or username
 * @param {string|number} userIdOrUsername - The user ID or username to check
 * @returns {Promise<Object|null>} - Promise that resolves to the user object if found, null otherwise
 */
function checkUserExists(userIdOrUsername) {
    console.log('=== CHECK USER EXISTS STARTED ===');
    console.log('Checking if user exists:', userIdOrUsername);
    
    return new Promise((resolve, reject) => {
        // Get the token
        const token = localStorage.getItem('auth_token');
        if (!token) {
            console.error('Authentication token is missing');
            reject(new Error('Authentication token is missing'));
            return;
        }
        
        // Fetch the list of users
        fetch('/api/admin/users', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                console.error('Failed to fetch users list:', response.status);
                reject(new Error(`Failed to fetch users list: ${response.status}`));
                return null;
            }
            return response.json();
        })
        .then(users => {
            if (!users) {
                resolve(null);
                return;
            }
            
            console.log('Fetched users list for checking existence');
            
            // Check if the input is a numeric ID
            if (!isNaN(userIdOrUsername)) {
                // Convert to number for comparison
                const userId = Number(userIdOrUsername);
                const user = users.find(u => u.id === userId);
                
                if (user) {
                    console.log('Found user by ID:', user);
                    resolve(user);
                } else {
                    console.log('User not found with ID:', userId);
                    resolve(null);
                }
            } else {
                // Assume it's a username
                const user = users.find(u => u.username === userIdOrUsername);
                
                if (user) {
                    console.log('Found user by username:', user);
                    resolve(user);
                } else {
                    console.log('User not found with username:', userIdOrUsername);
                    resolve(null);
                }
            }
        })
        .catch(error => {
            console.error('Error checking if user exists:', error);
            reject(error);
        });
    });
}

/**
 * Test user deletion functionality
 * @param {string|number} userId - The user ID or username to delete
 */
function testUserDeletion(userId) {
    console.log('=== TEST USER DELETION STARTED ===');
    console.log('Attempting to delete user:', userId);
    
    // Check if we have a valid user ID
    if (!userId) {
        console.error('No user ID provided');
        alert('Error: No user ID provided');
        return;
    }
    
    // Show a loading indicator
    const loadingToast = showToast('Checking user...', 'info', 0); // 0 means no auto-hide
    
    // First check if the user exists
    checkUserExists(userId)
        .then(user => {
            if (!user) {
                loadingToast.remove();
                showToast(`User with ID/username "${userId}" not found`, 'error');
                return;
            }
            
            // Update the loading toast
            loadingToast.remove();
            const deletingToast = showToast(`Deleting user ${user.username} (ID: ${user.id})...`, 'info', 0);
            
            // Use our improved deletion function with the numeric ID
            return superEmergencyDelete(user.id)
                .then(success => {
                    // Hide the loading toast
                    if (deletingToast) {
                        deletingToast.remove();
                    }
                    
                    if (success) {
                        console.log('User deletion successful');
                        showToast(`User ${user.username} deleted successfully!`, 'success');
                        
                        // Refresh the users list if it's currently displayed
                        const usersModal = document.querySelector('div[style*="z-index: 10000"]');
                        if (usersModal) {
                            document.body.removeChild(usersModal);
                            setTimeout(() => {
                                showUsersList();
                            }, 500);
                        }
                    } else {
                        console.error('User deletion failed');
                        showToast(`Failed to delete user ${user.username}. Check console for details.`, 'error');
                        
                        // Offer to try direct API call
                        if (confirm(`Would you like to try a direct API call to delete user ${user.username}?`)) {
                            const directToast = showToast(`Trying direct API call for user ${user.username}...`, 'info', 0);
                            
                            directDeleteUserAPI(user.id)
                                .then(directSuccess => {
                                    directToast.remove();
                                    
                                    if (directSuccess) {
                                        showToast(`User ${user.username} deleted successfully with direct API call!`, 'success');
                                        
                                        // Refresh the users list if it's currently displayed
                                        const usersModal = document.querySelector('div[style*="z-index: 10000"]');
                                        if (usersModal) {
                                            document.body.removeChild(usersModal);
                                            setTimeout(() => {
                                                showUsersList();
                                            }, 500);
                                        }
                                    } else {
                                        showToast(`Failed to delete user ${user.username} with direct API call.`, 'error');
                                    }
                                })
                                .catch(error => {
                                    directToast.remove();
                                    console.error('Error with direct API call:', error);
                                    showToast('Error with direct API call: ' + error.message, 'error');
                                });
                        }
                    }
                })
                .catch(error => {
                    // Hide the loading toast
                    if (deletingToast) {
                        deletingToast.remove();
                    }
                    
                    console.error('Error during user deletion:', error);
                    showToast('Error during user deletion: ' + error.message, 'error');
                });
        })
        .catch(error => {
            loadingToast.remove();
            console.error('Error checking if user exists:', error);
            showToast('Error checking if user exists: ' + error.message, 'error');
        });
    
    console.log('=== TEST USER DELETION COMPLETED ===');
}

/**
 * Close all modals
 */
function closeAllModals() {
    console.log('Closing all modals');
    
    // Get all modals
    const modals = document.querySelectorAll('.modal-backdrop');
    
    // Close each modal
    modals.forEach(modal => {
        console.log('Closing modal:', modal.id);
        modal.style.display = 'none';
    });
    
    // Also reset any form fields
    if (deleteConfirmInput) {
        deleteConfirmInput.value = '';
        if (confirmDeleteAccountBtn) {
            confirmDeleteAccountBtn.disabled = true;
        }
    }
    
    // Reset password form
    resetPasswordForm();
    
    console.log('All modals closed');
}

/**
 * Load site settings
 */
async function loadSiteSettings() {
    console.log('Loading site settings...');
    const adminSection = document.getElementById('adminSection');
    const registrationToggle = document.getElementById('registrationEnabled');
    const emailBaseUrlField = document.getElementById('emailBaseUrl'); // Correct variable name

    // // Check if admin section exists
    // if (!adminSection) {
    //     console.log('Admin section not found, skipping site settings load');
    //     return;
    // }

    try { // Correct structure: try block starts
        showLoading();
        
        const response = await fetch('/api/admin/settings', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to load site settings: ${response.status} ${response.statusText}`);
        }
        
        const settings = await response.json();
        
        if (registrationToggle) {
            registrationToggle.checked = settings.registration_enabled === 'true';
        }
        
        if (emailBaseUrlField) { // Use correct variable name
            emailBaseUrlField.value = settings.email_base_url || 'http://localhost:8080'; // Set the value
        }
        
        console.log('Site settings loaded successfully', settings);
        
    } catch (error) { // Correct structure: catch block follows try
        console.error('Error loading site settings:', error);
        showToast('Failed to load site settings. Please try again.', 'error');
    } finally { // Correct structure: finally block follows catch
        hideLoading();
    }
}

/**
 * Save site settings
 */
async function saveSiteSettings() {
    console.log('Saving site settings...');
    const registrationToggle = document.getElementById('registrationEnabled');
    const emailBaseUrlField = document.getElementById('emailBaseUrl'); // Get the new field

    const settings = {};
    
    if (registrationToggle) {
        settings.registration_enabled = registrationToggle.checked; // Boolean value will be converted to string in backend
    }

    if (emailBaseUrlField) {
        let baseUrl = emailBaseUrlField.value.trim();
        // Basic validation: check if it looks somewhat like a URL
        if (baseUrl && (baseUrl.startsWith('http://') || baseUrl.startsWith('https://'))) {
             // Remove trailing slash if present
            if (baseUrl.endsWith('/')) {
                baseUrl = baseUrl.slice(0, -1);
            }
            settings.email_base_url = baseUrl;
        } else if (baseUrl) {
            showToast('Invalid Email Base URL format. It should start with http:// or https://', 'error');
            return; // Stop saving if format is invalid
        } else {
             settings.email_base_url = 'http://localhost:8080'; // Use default if empty
             emailBaseUrlField.value = settings.email_base_url; // Update field with default
        }
    }

    
    try {
        showLoading();

        const response = await fetch('/api/admin/settings', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (response.ok) {
            showToast('Site settings saved successfully', 'success');
        } else {
            const errorData = await response.json();
            showToast(errorData.message || 'Failed to save site settings', 'error');
        }
    } catch (error) {
        console.error('Error saving site settings:', error);
        showToast('Failed to save site settings. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Set up the delete button for user deletion
 */
function setupDeleteButton() {
    console.log('=== SETUP DELETE BUTTON STARTED ===');
    
    // Get the confirm delete button
    const confirmDeleteUserBtn = document.getElementById('confirmDeleteUserBtn');
    if (!confirmDeleteUserBtn) {
        console.error('confirmDeleteUserBtn not found in setupDeleteButton');
        return;
    }
    
    try {
        // Get the user ID from various possible sources
        let userId = window.currentDeleteUserId || null;
        
        if (!userId && document.getElementById('deleteUserId')) {
            userId = document.getElementById('deleteUserId').value;
        }
        
        if (!userId && document.getElementById('editUserId')) {
            userId = document.getElementById('editUserId').value;
        }
        
        if (!userId && document.getElementById('displayUserId')) {
            userId = document.getElementById('displayUserId').textContent;
        }
        
        console.log('Setting up delete button for user ID:', userId);
        
        // Remove existing event listeners by cloning
        const newBtn = confirmDeleteUserBtn.cloneNode(true);
        confirmDeleteUserBtn.parentNode.replaceChild(newBtn, confirmDeleteUserBtn);
        
        // Add new event listener
        newBtn.addEventListener('click', function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Delete button clicked in setupDeleteButton');
            deleteUser();
            return false;
        });
        
        // Also set onclick for redundancy
        newBtn.onclick = function(e) {
            e.preventDefault();
            e.stopPropagation();
            console.log('Delete button clicked via onclick in setupDeleteButton');
            deleteUser();
            return false;
        };
        
        console.log('Delete button set up successfully');
    } catch (error) {
        console.error('Error setting up delete button:', error);
    }
    
    console.log('=== SETUP DELETE BUTTON COMPLETED ===');
}

/**
 * Direct API call for user deletion
 * @param {string|number} userId - The user ID or username to delete
 * @returns {Promise<boolean>} - Promise that resolves to true if deletion was successful, false otherwise
 */
function directDeleteUserAPI(userId) {
    console.log('=== DIRECT DELETE API CALL STARTED ===');
    console.log('Function caller:', arguments.callee.caller ? arguments.callee.caller.name : 'unknown');
    
    return new Promise((resolve, reject) => {
        // Try to get the user ID from multiple sources if not provided
        if (!userId) {
            const deleteUserIdField = document.getElementById('deleteUserId');
            const editUserIdField = document.getElementById('editUserId');
            const displayUserIdField = document.getElementById('displayUserId');
            
            userId = window.currentDeleteUserId;
            
            if (!userId && deleteUserIdField && deleteUserIdField.value) {
                userId = deleteUserIdField.value;
            } else if (!userId && editUserIdField && editUserIdField.value) {
                userId = editUserIdField.value;
            } else if (!userId && displayUserIdField && displayUserIdField.textContent) {
                userId = displayUserIdField.textContent;
            }
        }
        
        console.log('User ID to delete:', userId);
        
        if (!userId) {
            console.error('Direct delete API call failed: User ID is missing');
            reject(new Error('User ID is missing'));
            return;
        }
        
        // Check if the input is a username rather than a numeric ID
        if (isNaN(userId)) {
            console.log('Input appears to be a username, not a numeric ID');
            // Try to find the user ID by username
            findUserIdByUsernameAsync(userId)
                .then(numericId => {
                    if (numericId) {
                        console.log(`Found numeric ID ${numericId} for username ${userId}`);
                        // Call this function again with the numeric ID
                        return directDeleteUserAPI(numericId);
                    } else {
                        throw new Error(`Could not find a user with username "${userId}"`);
                    }
                })
                .then(resolve)
                .catch(reject);
            return;
        }
        
        console.log('Proceeding with numeric user ID:', userId);
        
        // Get the token with detailed logging
        const token = localStorage.getItem('auth_token');
        console.log('Token exists:', !!token);
        console.log('Token length:', token ? token.length : 0);
        
        if (!token) {
            console.error('Authentication token is missing');
            reject(new Error('Authentication token is missing'));
            return;
        }
        
        // Log the API endpoint
        const apiEndpoint = `/api/admin/users/${userId}`;
        console.log('Direct API endpoint:', apiEndpoint);
        
        // Create headers with detailed logging
        const headers = {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        };
        console.log('Direct API request headers:', Object.keys(headers));
        
        // Make the fetch request with detailed logging
        console.log('Direct API fetch request configuration:', {
            method: 'DELETE',
            headers: Object.keys(headers),
            credentials: 'same-origin'
        });
        
        // Make a fetch API call
        fetch(apiEndpoint, {
            method: 'DELETE',
            headers: headers,
            credentials: 'same-origin' // Include cookies
        })
        .then(response => {
            console.log('Direct API response received');
            console.log('Direct API response status:', response.status);
            console.log('Direct API response status text:', response.statusText);
            console.log('Direct API response headers:', [...response.headers.entries()]);
            console.log('Direct API response type:', response.type);
            console.log('Direct API response URL:', response.url);
            
            // Get the raw text first
            return response.text().then(text => {
                console.log('Direct API raw response text:', text);
                try {
                    const data = text ? JSON.parse(text) : {};
                    return {
                        status: response.status,
                        data: data
                    };
                } catch (err) {
                    console.log('Error parsing Direct API JSON response:', err);
                    return {
                        status: response.status,
                        data: { message: text || 'No response data or invalid JSON' }
                    };
                }
            });
        })
        .then(result => {
            console.log('Direct API response data:', result);
            
            if (result.status >= 200 && result.status < 300) {
                console.log('Direct API call successful');
                resolve(true);
            } else {
                const errorMessage = result.data && result.data.message ? result.data.message : 'Failed to delete user';
                console.error('Direct API call failed:', errorMessage);
                resolve(false); // Resolve with false instead of rejecting
            }
        })
        .catch(error => {
            console.error('Direct API call error:', error);
            console.error('Direct API call error details:', error.message, error.stack);
            reject(error);
        });
    });
}

/**
 * Check if the API endpoint is accessible
 */
function checkApiEndpoint() {
    console.log('Checking API endpoint accessibility...');
    
    // Try to access a simple API endpoint
    fetch('/api/auth/validate-token', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${window.auth.getToken()}`
        }
    })
    .then(response => {
        console.log('API endpoint check response status:', response.status);
        if (response.ok) {
            console.log('API endpoint is accessible');
            showToast('API endpoint is accessible', 'success');
        } else {
            console.error('API endpoint is not accessible');
            showToast('API endpoint is not accessible. Status: ' + response.status, 'error');
        }
        return response.json().catch(() => ({}));
    })
    .then(data => {
        console.log('API endpoint check response data:', data);
    })
    .catch(error => {
        console.error('Error checking API endpoint:', error);
        showToast('Error checking API endpoint: ' + error.message, 'error');
    });
}

/**
 * Trigger warranty expiration notifications (admin only)
 */
async function triggerWarrantyNotifications() {
    console.log('Trigger warranty notifications requested');
    
    // Check if admin
    try {
        const response = await fetch('/api/auth/user', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            }
        });
        
        if (!response.ok) {
            throw new Error('Failed to check user status');
        }
        
        const userData = await response.json();
        
        if (!userData.is_admin) {
            showToast('Only administrators can send warranty notifications', 'error');
            return;
        }
        
        // Show confirmation dialog
        if (!confirm('Are you sure you want to send warranty expiration notifications to all eligible users? This will immediately email users with warranties expiring soon.')) {
            return;
        }
        
        showLoading();
        
        // Call the API endpoint to trigger notifications
        const notificationResponse = await fetch('/api/admin/send-notifications', {
            method: 'POST',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            }
        });
        
        if (!notificationResponse.ok) {
            const errorData = await notificationResponse.json();
            throw new Error(errorData.message || 'Failed to send notifications');
        }
        
        const result = await notificationResponse.json();
        showToast(result.message || 'Notifications triggered successfully', 'success');
        
    } catch (error) {
        console.error('Error triggering notifications:', error);
        showToast('Error: ' + error.message, 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Load available timezones from the API
 * @returns {Promise} A promise that resolves when timezones are loaded
 */
function loadTimezones() {
    console.log('Loading timezones...');
    return new Promise((resolve, reject) => {
        fetch('/api/timezones', {
            method: 'GET',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            }
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to load timezones');
            }
            return response.json();
        })
        .then(timezoneGroups => {
            // Clear loading option
            timezoneSelect.innerHTML = '';
            
            // Add timezone groups and their options
            timezoneGroups.forEach(group => {
                const optgroup = document.createElement('optgroup');
                optgroup.label = group.region;
                
                group.timezones.forEach(timezone => {
                    const option = document.createElement('option');
                    option.value = timezone.value;
                    option.textContent = timezone.label;
                    optgroup.appendChild(option);
                });
                
                timezoneSelect.appendChild(optgroup);
            });
            
            // Set the current timezone from preferences
            // Get the appropriate key prefix based on user type
            const prefix = getPreferenceKeyPrefix();
            const savedPreferences = JSON.parse(localStorage.getItem(`${prefix}preferences`) || '{}');
            
            console.log('Loading timezone preference from localStorage', {
                prefix: prefix,
                preferenceKey: `${prefix}preferences`,
                savedTimezone: savedPreferences.timezone
            });
            
            if (savedPreferences.timezone) {
                timezoneSelect.value = savedPreferences.timezone;
                console.log('Set timezone select to:', savedPreferences.timezone, 'Current value:', timezoneSelect.value);
                resolve();
            } else {
                // If no timezone preference found in localStorage, load from API as backup
                console.log('No timezone found in localStorage, fetching from API');
                fetch('/api/auth/preferences', {
                    method: 'GET',
                    headers: {
                        'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                        'Content-Type': 'application/json'
                    }
                })
                .then(response => response.json())
                .then(data => {
                    // API returns preferences directly, not nested
                    if (data && data.timezone) {
                        console.log('Received timezone from API:', data.timezone);
                        timezoneSelect.value = data.timezone;
                        console.log('Set timezone select to:', data.timezone, 'Current value:', timezoneSelect.value);
                    }
                    resolve();
                })
                .catch(error => {
                    console.error('Error loading preferences from API:', error);
                    resolve(); // Still resolve to continue the chain
                });
            }
        })
        .catch(error => {
            console.error('Error loading timezones:', error);
            timezoneSelect.innerHTML = '<option value="UTC">UTC (Coordinated Universal Time)</option>';
            reject(error);
        });
    });
}

/**
 * Save email settings
 */
function saveEmailSettings() {
    showLoading();
    
    try {
        // Get values
        const emailNotifications = emailNotificationsToggle.checked;
        const notificationFrequency = notificationFrequencySelect.value;
        const notificationTime = notificationTimeInput.value;
        const timezone = timezoneSelect.value;
        
        // Validate inputs
        if (!timezone) {
            showToast('Please select a timezone', 'error');
            hideLoading();
            return;
        }
        
        // Create preferences object
        const preferences = {
            email_notifications: emailNotifications,
            notification_frequency: notificationFrequency,
            notification_time: notificationTime,
            timezone: timezone
        };
        
        // Save to API
        fetch('/api/auth/preferences', {
            method: 'PUT',
            headers: {
                'Authorization': 'Bearer ' + localStorage.getItem('auth_token'),
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(preferences)
        })
        .then(response => {
            if (!response.ok) {
                throw new Error('Failed to save email settings');
            }
            return response.json();
        })
        .then(data => {
            // Save to localStorage
            const prefix = getPreferenceKeyPrefix();
            localStorage.setItem(`${prefix}emailNotifications`, emailNotifications);
            localStorage.setItem(`${prefix}notificationFrequency`, notificationFrequency);
            localStorage.setItem(`${prefix}notificationTime`, notificationTime);
            localStorage.setItem(`${prefix}timezone`, timezone);
            
            showToast('Email settings saved successfully', 'success');
        })
        .catch(error => {
            console.error('Error saving email settings:', error);
            showToast('Error saving email settings', 'error');
            
            // Save to localStorage as fallback
            const prefix = getPreferenceKeyPrefix();
            localStorage.setItem(`${prefix}emailNotifications`, emailNotifications);
            localStorage.setItem(`${prefix}notificationFrequency`, notificationFrequency);
            localStorage.setItem(`${prefix}notificationTime`, notificationTime);
            localStorage.setItem(`${prefix}timezone`, timezone);
        })
        .finally(() => {
            hideLoading();
        });
    } catch (error) {
        console.error('Error in saveEmailSettings:', error);
        showToast('Error saving email settings', 'error');
        hideLoading();
    }
}

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
        console.log(`Storage event detected for view preference (${event.key}) in settings. New value: ${event.newValue}`);
        // Ensure the dropdown element exists and the value is different
        if (defaultViewSelect && defaultViewSelect.value !== event.newValue) {
            // Check if the new value is a valid option in the select
            const optionExists = [...defaultViewSelect.options].some(option => option.value === event.newValue);
            if (optionExists) {
                defaultViewSelect.value = event.newValue;
                console.log('Updated settings default view dropdown.');
            } else {
                console.warn(`Storage event value (${event.newValue}) not found in dropdown options.`);
            }
        } else if (defaultViewSelect) {
             console.log('Storage event value matches current dropdown selection, ignoring.');
        }
    }
});
// --- End Storage Event Listener ---