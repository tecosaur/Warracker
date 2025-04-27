/**
 * Immediate Authentication State Handler
 * 
 * This script runs as soon as possible to hide login/register buttons if a user is logged in
 * It should be included directly in the HTML before any other scripts
 */

console.log('include-auth-new.js: Running immediate auth check');

// Immediately check if user is logged in
if (localStorage.getItem('auth_token')) {
    console.log('include-auth-new.js: Auth token found, hiding login/register buttons immediately');
    
    // Create and inject CSS to hide auth buttons
    var style = document.createElement('style');
    style.textContent = `
        #authContainer, .auth-buttons, a[href="login.html"], a[href="register.html"], 
        .login-btn, .register-btn, .auth-btn.login-btn, .auth-btn.register-btn {
            display: none !important;
            visibility: hidden !important;
        }
        
        #userMenu, .user-menu {
            display: block !important;
            visibility: visible !important;
        }
    `;
    document.head.appendChild(style);
    
    // Set the display style as soon as DOM is ready
    window.addEventListener('DOMContentLoaded', function() {
        console.log('include-auth-new.js: DOM loaded, ensuring buttons are hidden');
        
        // Hide auth container
        var authContainer = document.getElementById('authContainer');
        if (authContainer) {
            authContainer.style.display = 'none';
            authContainer.style.visibility = 'hidden';
        }
        
        // Hide all login/register buttons
        document.querySelectorAll('a[href="login.html"], a[href="register.html"], .login-btn, .register-btn, .auth-btn').forEach(function(button) {
            button.style.display = 'none';
            button.style.visibility = 'hidden';
        });
        
        // Show user menu
        var userMenu = document.getElementById('userMenu');
        if (userMenu) {
            userMenu.style.display = 'block';
            userMenu.style.visibility = 'visible';
        }
        
        // Update user information
        try {
            var userInfoStr = localStorage.getItem('user_info');
            if (userInfoStr) {
                var userInfo = JSON.parse(userInfoStr);
                var displayName = userInfo.username || 'User';
                
                var userDisplayName = document.getElementById('userDisplayName');
                if (userDisplayName) {
                    userDisplayName.textContent = displayName;
                }
                
                var userName = document.getElementById('userName');
                if (userName) {
                    userName.textContent = (userInfo.first_name || '') + ' ' + (userInfo.last_name || '');
                    if (!userName.textContent.trim()) userName.textContent = userInfo.username || 'User';
                }
                
                var userEmail = document.getElementById('userEmail');
                if (userEmail && userInfo.email) {
                    userEmail.textContent = userInfo.email;
                }
            }
        } catch (e) {
            console.error('include-auth-new.js: Error updating user info:', e);
        }
    });
} else {
    console.log('include-auth-new.js: No auth token found, showing login/register buttons');
    
    // Create and inject CSS to show auth buttons
    var style = document.createElement('style');
    style.textContent = `
        #authContainer, .auth-buttons {
            display: flex !important;
            visibility: visible !important;
        }
        
        a[href="login.html"], a[href="register.html"], 
        .login-btn, .register-btn, .auth-btn.login-btn, .auth-btn.register-btn {
            display: inline-block !important;
            visibility: visible !important;
        }
        
        #userMenu, .user-menu {
            display: none !important;
            visibility: hidden !important;
        }
    `;
    document.head.appendChild(style);
}

// Listen for changes to localStorage
window.addEventListener('storage', function(event) {
    if (event.key === 'auth_token' || event.key === 'user_info') {
        console.log('include-auth-new.js: Auth data changed, reloading page to update UI');
        window.location.reload();
    }
});

/**
 * Script to include the new authentication script in existing HTML files
 * This script should be included at the end of the body in each HTML file
 */

// Function to load and execute the new authentication script
function loadAuthNewScript() {
    // Create a script element
    const script = document.createElement('script');
    script.src = 'auth-new.js';
    script.async = true;
    
    // Add the script to the document
    document.body.appendChild(script);
    
    console.log('Added auth-new.js script to the page');
}

// Function to check if we're using the new UI
function isNewUI() {
    // Check for elements that are specific to the new UI
    const loginButton = document.querySelector('a[href="login.html"].auth-btn, a.login');
    const registerButton = document.querySelector('a[href="register.html"].auth-btn, a.register');
    
    // If we find these elements, we're using the new UI
    return !!(loginButton || registerButton);
}

// Load the new authentication script if we're using the new UI
if (isNewUI()) {
    console.log('Detected new UI, loading auth-new.js');
    loadAuthNewScript();
} else {
    console.log('Using old UI, not loading auth-new.js');
} 