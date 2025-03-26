/**
 * Authentication functionality for Warracker
 * Handles user login, logout, and authentication state management
 */

// DOM Elements
const authContainer = document.getElementById('authContainer');
const userMenu = document.getElementById('userMenu');
const userBtn = document.getElementById('userBtn');
const userMenuDropdown = document.getElementById('userMenuDropdown');
const userDisplayName = document.getElementById('userDisplayName');
const userName = document.getElementById('userName');
const userEmail = document.getElementById('userEmail');
const logoutMenuItem = document.getElementById('logoutMenuItem');
const profileMenuItem = document.getElementById('profileMenuItem');

// New UI Elements (from screenshot)
const loginButton = document.querySelector('a[href="login.html"]');
const registerButton = document.querySelector('a[href="register.html"]');
const usernameDisplay = document.querySelector('.user-name');

// Authentication state
let currentUser = null;
let authToken = null;

// Initialize authentication
document.addEventListener('DOMContentLoaded', () => {
    // Initial check of authentication state
    checkAuthState();
    
    // Set up periodic check of auth state (every 30 seconds)
    setInterval(checkAuthState, 30000);
    
    // User menu toggle
    if (userBtn) {
        userBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            userMenuDropdown.classList.toggle('active');
        });
    }
    
    // Close user menu when clicking outside
    document.addEventListener('click', (e) => {
        if (userMenuDropdown && userBtn && !userMenuDropdown.contains(e.target) && !userBtn.contains(e.target)) {
            userMenuDropdown.classList.remove('active');
        }
    });
    
    // Logout functionality
    if (logoutMenuItem) {
        logoutMenuItem.addEventListener('click', logout);
    }
    
    // Profile menu item
    if (profileMenuItem) {
        profileMenuItem.addEventListener('click', () => {
            // Redirect to profile page when implemented
            // For now, just show a message
            showToast('Profile page coming soon!', 'info');
        });
    }
});

/**
 * Check if user is authenticated and update UI accordingly
 */
function checkAuthState() {
    // Get latest token from localStorage
    authToken = localStorage.getItem('auth_token');
    const userInfo = localStorage.getItem('user_info');
    
    if (authToken && userInfo) {
        try {
            currentUser = JSON.parse(userInfo);
            updateUIForAuthenticatedUser();
            validateToken();
        } catch (error) {
            console.error('Error parsing user info:', error);
            clearAuthData();
            updateUIForUnauthenticatedUser();
        }
    } else {
        updateUIForUnauthenticatedUser();
    }
}

/**
 * Update UI elements for authenticated user
 */
function updateUIForAuthenticatedUser() {
    console.log('auth.js: Updating UI for authenticated user');
    
    // Hide login/register buttons
    if (authContainer) {
        console.log('auth.js: Hiding authContainer');
        authContainer.style.display = 'none';
        authContainer.style.visibility = 'hidden';
    }
    
    // Show user menu
    if (userMenu) {
        console.log('auth.js: Showing userMenu');
        userMenu.style.display = 'block';
        userMenu.style.visibility = 'visible';
    }
    
    // Update user info
    if (currentUser) {
        const displayName = currentUser.first_name || currentUser.username;
        if (userDisplayName) userDisplayName.textContent = displayName;
        if (userName) userName.textContent = `${currentUser.first_name || ''} ${currentUser.last_name || ''}`.trim() || currentUser.username;
        if (userEmail) userEmail.textContent = currentUser.email;
    }
    
    // Hide all login and register buttons
    const loginButtons = document.querySelectorAll('a[href="login.html"], .login-btn, .auth-btn.login-btn');
    const registerButtons = document.querySelectorAll('a[href="register.html"], .register-btn, .auth-btn.register-btn');
    
    console.log('auth.js: Found login buttons:', loginButtons.length);
    console.log('auth.js: Found register buttons:', registerButtons.length);
    
    loginButtons.forEach(button => {
        console.log('auth.js: Hiding login button');
        button.style.display = 'none';
        button.style.visibility = 'hidden';
    });
    
    registerButtons.forEach(button => {
        console.log('auth.js: Hiding register button');
        button.style.display = 'none';
        button.style.visibility = 'hidden';
    });
    
    // Hide any containers with the auth-buttons class
    const authButtonsContainers = document.querySelectorAll('.auth-buttons');
    authButtonsContainers.forEach(container => {
        console.log('auth.js: Hiding auth buttons container');
        container.style.display = 'none';
        container.style.visibility = 'hidden';
    });
}

/**
 * Update UI elements for unauthenticated user
 */
function updateUIForUnauthenticatedUser() {
    console.log('auth.js: Updating UI for unauthenticated user');
    
    // Show login/register buttons
    if (authContainer) {
        console.log('auth.js: Showing authContainer');
        authContainer.style.display = 'flex';
        authContainer.style.visibility = 'visible';
    }
    
    // Hide user menu
    if (userMenu) {
        console.log('auth.js: Hiding userMenu');
        userMenu.style.display = 'none';
        userMenu.style.visibility = 'hidden';
    }
    
    // Clear user info
    if (userDisplayName) userDisplayName.textContent = 'User';
    if (userName) userName.textContent = 'User Name';
    if (userEmail) userEmail.textContent = 'user@example.com';
    
    // Show all login and register buttons
    const loginButtons = document.querySelectorAll('a[href="login.html"], .login-btn, .auth-btn.login-btn');
    const registerButtons = document.querySelectorAll('a[href="register.html"], .register-btn, .auth-btn.register-btn');
    
    loginButtons.forEach(button => {
        button.style.display = 'inline-block';
        button.style.visibility = 'visible';
    });
    
    registerButtons.forEach(button => {
        button.style.display = 'inline-block';
        button.style.visibility = 'visible';
    });
    
    // Show any containers with the auth-buttons class
    const authButtonsContainers = document.querySelectorAll('.auth-buttons');
    authButtonsContainers.forEach(container => {
        container.style.display = 'flex';
        container.style.visibility = 'visible';
    });
}

/**
 * Logout user
 */
async function logout() {
    try {
        showLoading();
        
        // Call logout API
        const response = await fetch('/api/auth/logout', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${authToken}`,
                'Content-Type': 'application/json'
            }
        });
        
        // Clear auth data regardless of API response
        clearAuthData();
        updateUIForUnauthenticatedUser();
        
        // Show success message
        showToast('Logged out successfully', 'success');
        
        // Redirect to login page
        window.location.href = 'login.html';
        
    } catch (error) {
        console.error('Logout error:', error);
        
        // Still clear auth data even if API call fails
        clearAuthData();
        updateUIForUnauthenticatedUser();
        
        showToast('Logged out', 'info');
        
        // Redirect to login page even if there was an error
        window.location.href = 'login.html';
    } finally {
        hideLoading();
    }
}

/**
 * Clear authentication data from localStorage
 */
function clearAuthData() {
    // Clear both localStorage and global variables
    localStorage.removeItem('auth_token');
    localStorage.removeItem('user_info');
    authToken = null;
    currentUser = null;
}

/**
 * Validate token with the server
 */
async function validateToken() {
    if (!authToken) {
        clearAuthData();
        updateUIForUnauthenticatedUser();
        return;
    }
    
    try {
        // Use the full URL to avoid path issues
        const apiUrl = window.location.origin + '/api/auth/validate-token';
        
        const response = await fetch(apiUrl, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${authToken}`
            }
        });
        
        if (!response.ok) {
            const errorData = await response.json();
            console.error('Token validation failed:', errorData.message);
            throw new Error(errorData.message || 'Invalid token');
        }
        
        // Token is valid, update last active time
        const data = await response.json();
        if (data.user) {
            currentUser = data.user;
            localStorage.setItem('user_info', JSON.stringify(currentUser));
            updateUIForAuthenticatedUser();
        }
        
        return true;
    } catch (error) {
        console.error('Token validation error:', error);
        clearAuthData();
        updateUIForUnauthenticatedUser();
        
        // Only show toast if we're on a page that requires authentication
        if (window.location.pathname !== '/login.html' && 
            window.location.pathname !== '/register.html' &&
            window.location.pathname !== '/reset-password.html' &&
            window.location.pathname !== '/reset-password-request.html') {
            showToast('Your session has expired. Please login again.', 'warning');
        }
        
        return false;
    }
}

/**
 * Add authorization header to fetch requests
 * @param {Object} options - Fetch options
 * @returns {Object} - Updated fetch options with auth header
 */
function addAuthHeader(options = {}) {
    if (!authToken) return options;
    
    const headers = options.headers || {};
    
    return {
        ...options,
        headers: {
            ...headers,
            'Authorization': `Bearer ${authToken}`
        }
    };
}

/**
 * Get the authentication token
 * @returns {string} - The authentication token
 */
function getToken() {
    // Always get the latest token from localStorage and update global variable
    authToken = localStorage.getItem('auth_token');
    return authToken;
}

// Export authentication functions for use in other scripts
window.auth = {
    isAuthenticated: () => !!localStorage.getItem('auth_token'),
    getCurrentUser: () => {
        const userInfo = localStorage.getItem('user_info');
        return userInfo ? JSON.parse(userInfo) : null;
    },
    getToken: getToken,
    addAuthHeader,
    checkAuthState,
    logout
};
