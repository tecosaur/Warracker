// DOM Elements
const darkModeToggle = document.getElementById('darkModeToggle');
const darkModeToggleSetting = document.getElementById('darkModeToggleSetting');
const defaultViewSelect = document.getElementById('defaultView');
const emailNotificationsToggle = document.getElementById('emailNotifications');
const saveProfileBtn = document.getElementById('saveProfileBtn');
const savePreferencesBtn = document.getElementById('savePreferencesBtn');
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
const registrationEnabled = document.getElementById('registrationEnabled');
const saveSiteSettingsBtn = document.getElementById('saveSiteSettingsBtn');

// Initialize settings page
document.addEventListener('DOMContentLoaded', function() {
    console.log('DOM fully loaded, initializing settings page');
    
    // Initialize the page
    initPage();
    
    // Set up event listeners
    setupEventListeners();
    
    // Initialize modals
    initModals();
    
    // Set up direct event listeners for critical elements
    setupCriticalEventListeners();
    
    // Make deleteUser function globally accessible
    window.deleteUser = deleteUser;
    window.directDeleteUserAPI = directDeleteUserAPI;
    
    // Add a global click handler for delete buttons
    document.addEventListener('click', function(event) {
        // Check if the click was on a delete button or inside the delete modal
        if (event.target && event.target.id === 'confirmDeleteUserBtn') {
            console.log('Global click handler caught delete button click');
            event.preventDefault();
            event.stopPropagation();
            deleteUser();
            return false;
        }
        
        // Check for clicks on the direct delete link
        if (event.target && event.target.id === 'directDeleteLink') {
            console.log('Global click handler caught direct delete link click');
            event.preventDefault();
            event.stopPropagation();
            deleteUser();
            return false;
        }
        
        // Check for clicks on the direct API link
        if (event.target && event.target.id === 'directAPILink') {
            console.log('Global click handler caught direct API link click');
            event.preventDefault();
            event.stopPropagation();
            const userId = window.currentDeleteUserId || 
                          (document.getElementById('deleteUserId') ? document.getElementById('deleteUserId').value : null);
            directDeleteUserAPI(userId);
            return false;
        }
        
        // Check for clicks on the emergency delete button
        if (event.target && event.target.id === 'emergencyDeleteBtn') {
            console.log('Global click handler caught emergency delete button click');
            // The button has its own inline handler, so we don't need to do anything here
        }
        
        // Check for any element with delete-user-btn class or containing "delete" in the id
        if (event.target && 
            (event.target.classList.contains('delete-user-btn') || 
             (event.target.id && event.target.id.toLowerCase().includes('delete')))) {
            console.log('Global click handler caught click on element with delete in the id:', event.target.id);
            console.log('Element:', event.target);
            
            // If this is a button inside the delete modal, try to delete the user
            if (event.target.closest('#deleteUserModal')) {
                console.log('Element is inside delete modal, attempting to delete user');
                event.preventDefault();
                event.stopPropagation();
                deleteUser();
                return false;
            }
        }
    });
    
    // Add a direct event listener to the confirmDeleteUserBtn
    const confirmDeleteUserBtn = document.getElementById('confirmDeleteUserBtn');
    if (confirmDeleteUserBtn) {
        console.log('Adding direct event listener to confirmDeleteUserBtn on page load');
        confirmDeleteUserBtn.addEventListener('click', function(e) {
            console.log('Direct event listener on confirmDeleteUserBtn triggered');
            e.preventDefault();
            e.stopPropagation();
            deleteUser();
            return false;
        });
    }
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
    
    // Load user data and preferences
    loadUserData();
    loadPreferences();
    
    // Fix for settings button
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
        console.error('Settings button not found');
    }
    
    console.log('Settings page initialization complete');
}

/**
 * Set up critical event listeners that must work for core functionality
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
    
    try {
        // Get user from localStorage first
        const currentUser = window.auth.getCurrentUser();
        
        if (currentUser) {
            // Populate form fields
            firstNameInput.value = currentUser.first_name || '';
            lastNameInput.value = currentUser.last_name || '';
            emailInput.value = currentUser.email || '';
            
            // Check if user is admin and show admin section
            if (currentUser.is_admin) {
                adminSection.style.display = 'block';
                loadUsers();
                loadSiteSettings();
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
                firstNameInput.value = userData.first_name || '';
                lastNameInput.value = userData.last_name || '';
                emailInput.value = userData.email || '';
                
                // Check if user is admin and show admin section
                if (userData.is_admin) {
                    adminSection.style.display = 'block';
                    loadUsers();
                    loadSiteSettings();
                }
                
                // Update localStorage
                localStorage.setItem('user_info', JSON.stringify(userData));
            } else {
                // Handle error
                const errorData = await response.json();
                console.warn('API error:', errorData.message);
            }
        } catch (apiError) {
            console.warn('API error, using localStorage data:', apiError);
        }
    } catch (error) {
        console.error('Error loading user data:', error);
        showToast('Failed to load user data. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Load user preferences from localStorage
 */
function loadPreferences() {
    // Load dark mode preference
    const darkMode = localStorage.getItem('darkMode') === 'true';
    darkModeToggle.checked = darkMode;
    darkModeToggleSetting.checked = darkMode;
    
    // Apply the theme immediately
    setTheme(darkMode);
    
    // Load default view preference
    const defaultView = localStorage.getItem('defaultView') || 'grid';
    defaultViewSelect.value = defaultView;
    
    // Load email notifications preference (default to true if not set)
    const emailNotifications = localStorage.getItem('emailNotifications') !== 'false';
    emailNotificationsToggle.checked = emailNotifications;
}

/**
 * Setup event listeners for the settings page
 */
function setupEventListeners() {
    console.log('Setting up event listeners');
    
    // Dark mode toggle
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
            
            // Also update the header toggle
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
    
    // Admin section buttons
    if (refreshUsersBtn) {
        refreshUsersBtn.addEventListener('click', loadUsers);
    }
    
    if (checkAdminBtn) {
        checkAdminBtn.addEventListener('click', checkAdminPermissions);
    }
    
    if (showUsersBtn) {
        showUsersBtn.addEventListener('click', showUsersList);
    }
    
    if (testApiBtn) {
        testApiBtn.addEventListener('click', checkApiEndpoint);
    }
    
    // Site settings save button
    if (saveSiteSettingsBtn) {
        saveSiteSettingsBtn.addEventListener('click', saveSiteSettings);
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
 * Set theme (dark/light)
 * @param {boolean} isDark - Whether to use dark mode
 */
function setTheme(isDark) {
    document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
    
    // Also add/remove the dark-mode class on the body for additional styling
    if (isDark) {
        document.body.classList.add('dark-mode');
    } else {
        document.body.classList.remove('dark-mode');
    }
    
    localStorage.setItem('darkMode', isDark);
}

/**
 * Save user profile
 */
async function saveProfile() {
    // Validate form
    if (!firstNameInput.value.trim() || !lastNameInput.value.trim()) {
        showToast('Please fill in all required fields', 'error');
        return;
    }
    
    showLoading();
    
    try {
        // Try to update profile via API
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
                    ...currentUser,
                    first_name: userData.first_name,
                    last_name: userData.last_name
                };
                
                localStorage.setItem('user_info', JSON.stringify(updatedUser));
                
                // Update UI
                if (window.auth.checkAuthState) {
                    window.auth.checkAuthState();
                }
                
                showToast('Profile updated successfully', 'success');
            } else {
                // Handle error from API
                const errorData = await response.json();
                throw new Error(errorData.message || 'Failed to update profile');
            }
        } catch (apiError) {
            console.warn('API error, falling back to localStorage:', apiError);
            
            // Fallback to localStorage if API is not available
            const currentUser = window.auth.getCurrentUser();
            if (currentUser) {
                const updatedUser = {
                    ...currentUser,
                    first_name: firstNameInput.value.trim(),
                    last_name: lastNameInput.value.trim()
                };
                
                localStorage.setItem('user_info', JSON.stringify(updatedUser));
                
                // Update UI
                if (window.auth.checkAuthState) {
                    window.auth.checkAuthState();
                }
                
                showToast('Profile updated successfully (offline mode)', 'success');
            } else {
                throw new Error('User not found in localStorage');
            }
        }
    } catch (error) {
        console.error('Error updating profile:', error);
        showToast('Failed to update profile. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Save user preferences
 */
function savePreferences() {
    // Save dark mode preference
    const isDark = darkModeToggleSetting.checked;
    setTheme(isDark);
    darkModeToggle.checked = isDark;
    
    // Save default view preference
    const defaultView = defaultViewSelect.value;
    localStorage.setItem('defaultView', defaultView);
    localStorage.setItem('warrantyView', defaultView);
    
    // Save email notifications preference
    const emailNotifications = emailNotificationsToggle.checked;
    localStorage.setItem('emailNotifications', emailNotifications);
    
    showToast('Preferences saved successfully', 'success');
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
    if (!usersTableBody) return;
    
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
        modalContent.style.backgroundColor = 'white';
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
        
        // Create the close button
        const closeButton = document.createElement('button');
        closeButton.textContent = '×';
        closeButton.style.backgroundColor = 'transparent';
        closeButton.style.border = 'none';
        closeButton.style.fontSize = '24px';
        closeButton.style.cursor = 'pointer';
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
            th.style.borderBottom = '1px solid #ddd';
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
            idCell.style.borderBottom = '1px solid #ddd';
            
            const usernameCell = document.createElement('td');
            usernameCell.textContent = user.username;
            usernameCell.style.padding = '10px';
            usernameCell.style.borderBottom = '1px solid #ddd';
            
            const emailCell = document.createElement('td');
            emailCell.textContent = user.email;
            emailCell.style.padding = '10px';
            emailCell.style.borderBottom = '1px solid #ddd';
            
            const nameCell = document.createElement('td');
            nameCell.textContent = `${user.first_name || ''} ${user.last_name || ''}`.trim() || '-';
            nameCell.style.padding = '10px';
            nameCell.style.borderBottom = '1px solid #ddd';
            
            const adminCell = document.createElement('td');
            adminCell.textContent = user.is_admin ? 'Yes' : 'No';
            adminCell.style.padding = '10px';
            adminCell.style.borderBottom = '1px solid #ddd';
            
            const activeCell = document.createElement('td');
            activeCell.textContent = user.is_active ? 'Yes' : 'No';
            activeCell.style.padding = '10px';
            activeCell.style.borderBottom = '1px solid #ddd';
            
            const actionsCell = document.createElement('td');
            actionsCell.style.padding = '10px';
            actionsCell.style.borderBottom = '1px solid #ddd';
            
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

// Add the test API buttons when the page loads
document.addEventListener('DOMContentLoaded', function() {
    // Add the test API buttons after a short delay to ensure the page is fully loaded
    setTimeout(addTestApiButtons, 1000);
});

/**
 * Promise-based version of findUserIdByUsername
 * @param {string} username - The username to look up
 * @returns {Promise<number|null>} - Promise that resolves to the user ID or null if not found
 */
function findUserIdByUsernameAsync(username) {
    return new Promise((resolve) => {
        findUserIdByUsername(username, resolve);
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
    showLoading();
    
    try {
        const response = await fetch('/api/admin/settings', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`
            }
        });
        
        if (response.ok) {
            const settings = await response.json();
            
            // Update form fields
            if (registrationEnabled) {
                registrationEnabled.checked = settings.registration_enabled === 'true';
            }
        } else {
            const errorData = await response.json();
            console.warn('API error:', errorData.message);
        }
    } catch (error) {
        console.error('Error loading site settings:', error);
        showToast('Failed to load site settings. Please try again.', 'error');
    } finally {
        hideLoading();
    }
}

/**
 * Save site settings
 */
async function saveSiteSettings() {
    showLoading();
    
    try {
        const response = await fetch('/api/admin/settings', {
            method: 'PUT',
            headers: {
                'Authorization': `Bearer ${window.auth.getToken()}`,
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                registration_enabled: registrationEnabled ? registrationEnabled.checked : false
            })
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
 * Add test API buttons to the page
 */
function addTestApiButtons() {
    console.log('Test API buttons function called but disabled');
    // Function disabled to prevent floating buttons from appearing
    // The functionality is now available through the admin action buttons in the Admin Settings section
    return;
    
    // Original code below is kept for reference but will not execute due to the return above
    console.log('Adding test API buttons to the page');
    
    // Create a container for the buttons
    const buttonContainer = document.createElement('div');
    buttonContainer.style.position = 'fixed';
    buttonContainer.style.bottom = '20px';
    buttonContainer.style.right = '20px';
    buttonContainer.style.zIndex = '9999';
    buttonContainer.style.display = 'flex';
    buttonContainer.style.flexDirection = 'column';
    buttonContainer.style.gap = '10px';
    
    // Create a button to check API endpoint
    const apiCheckBtn = document.createElement('button');
    apiCheckBtn.className = 'btn btn-info';
    apiCheckBtn.textContent = 'Check API Endpoint';
    apiCheckBtn.addEventListener('click', checkApiEndpoint);
    
    // Create a button to test user deletion
    const testDeleteBtn = document.createElement('button');
    testDeleteBtn.className = 'btn btn-danger';
    testDeleteBtn.textContent = 'Test User Deletion';
    testDeleteBtn.addEventListener('click', function() {
        const userId = prompt('Enter user ID to delete:');
        if (userId) {
            if (confirm(`Are you sure you want to delete user ID ${userId}?`)) {
                testUserDeletion(userId);
            }
        }
    });
    
    // Create a button to check permissions
    const checkPermissionsBtn = document.createElement('button');
    checkPermissionsBtn.className = 'btn btn-warning';
    checkPermissionsBtn.textContent = 'Check Admin Permissions';
    checkPermissionsBtn.addEventListener('click', checkAdminPermissions);
    
    // Create a button to show users
    const showUsersBtn = document.createElement('button');
    showUsersBtn.className = 'btn btn-primary';
    showUsersBtn.textContent = 'Show Users';
    showUsersBtn.addEventListener('click', showUsersList);
    
    // Add buttons to the container
    buttonContainer.appendChild(apiCheckBtn);
    buttonContainer.appendChild(testDeleteBtn);
    buttonContainer.appendChild(checkPermissionsBtn);
    buttonContainer.appendChild(showUsersBtn);
    
    // Add the container to the body
    document.body.appendChild(buttonContainer);
    
    console.log('Test API buttons added to the page');
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