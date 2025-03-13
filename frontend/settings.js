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

// Form fields
const firstNameInput = document.getElementById('firstName');
const lastNameInput = document.getElementById('lastName');
const emailInput = document.getElementById('email');
const currentPasswordInput = document.getElementById('currentPassword');
const newPasswordInput = document.getElementById('newPassword');
const confirmPasswordInput = document.getElementById('confirmPassword');

// Initialize settings page
document.addEventListener('DOMContentLoaded', () => {
    // Check authentication
    if (window.auth) {
        window.auth.checkAuthState();
        
        // Redirect to login if not authenticated
        if (!window.auth.isAuthenticated()) {
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
    
    // Setup event listeners
    setupEventListeners();
    
    // Initialize modals
    initModals();
});

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
        }
        
        // Fetch fresh user data from API
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
            
            // Update localStorage
            localStorage.setItem('user_info', JSON.stringify(userData));
        } else {
            // Handle error
            const errorData = await response.json();
            showToast(errorData.message || 'Failed to load user data', 'error');
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
    // Dark mode toggle
    darkModeToggle.addEventListener('change', () => {
        const isDark = darkModeToggle.checked;
        setTheme(isDark);
        darkModeToggleSetting.checked = isDark;
    });
    
    darkModeToggleSetting.addEventListener('change', () => {
        const isDark = darkModeToggleSetting.checked;
        setTheme(isDark);
        darkModeToggle.checked = isDark;
    });
    
    // Save profile button
    saveProfileBtn.addEventListener('click', saveProfile);
    
    // Save preferences button
    savePreferencesBtn.addEventListener('click', savePreferences);
    
    // Change password button
    changePasswordBtn.addEventListener('click', () => {
        passwordChangeForm.style.display = 'block';
        changePasswordBtn.style.display = 'none';
    });
    
    // Cancel password change
    cancelPasswordBtn.addEventListener('click', () => {
        passwordChangeForm.style.display = 'none';
        changePasswordBtn.style.display = 'block';
        resetPasswordForm();
    });
    
    // Save password button
    savePasswordBtn.addEventListener('click', changePassword);
    
    // Delete account button
    deleteAccountBtn.addEventListener('click', () => {
        openModal(deleteAccountModal);
    });
    
    // Delete confirm input
    deleteConfirmInput.addEventListener('input', () => {
        confirmDeleteAccountBtn.disabled = deleteConfirmInput.value !== 'DELETE';
    });
    
    // Confirm delete account button
    confirmDeleteAccountBtn.addEventListener('click', deleteAccount);
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
}

/**
 * Open a modal
 * @param {HTMLElement} modal - The modal to open
 */
function openModal(modal) {
    modal.style.display = 'flex';
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
 * Show toast message
 * @param {string} message - Message to display
 * @param {string} type - Toast type (success, error, info, warning)
 */
function showToast(message, type = 'info') {
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
    
    // Remove toast after 5 seconds
    setTimeout(() => {
        toast.classList.add('toast-fade-out');
        setTimeout(() => {
            toastContainer.removeChild(toast);
        }, 300);
    }, 5000);
} 