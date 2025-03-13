/**
 * Script to fix the login and register buttons in the new UI
 * This script specifically targets the buttons shown in the screenshot
 */

// Log execution
console.log('fix-auth-buttons.js loaded and executing');

// Function to check if user is authenticated
function isAuthenticated() {
    const token = localStorage.getItem('auth_token');
    console.log('Auth token check:', !!token);
    return !!token;
}

// Function to find elements by text content
function getElementsByText(selector, text) {
    const elements = document.querySelectorAll(selector);
    return Array.prototype.filter.call(elements, element => element.textContent.trim() === text);
}

// Function to hide login and register buttons if user is authenticated
function updateAuthButtons() {
    console.log('updateAuthButtons executing...');
    
    // Check if user is authenticated
    if (isAuthenticated()) {
        console.log('User is authenticated, hiding login/register buttons');
        
        // Find login and register buttons using valid selectors
        const loginButtons = document.querySelectorAll('a[href="login.html"], .login-btn, .auth-btn.login-btn');
        const registerButtons = document.querySelectorAll('a[href="register.html"], .register-btn, .auth-btn.register-btn');
        
        // Find buttons by text content
        const loginButtonsByText = getElementsByText('a, button', 'Login');
        const registerButtonsByText = getElementsByText('a, button', 'Register');
        
        const allLoginButtons = [...loginButtons, ...loginButtonsByText];
        const allRegisterButtons = [...registerButtons, ...registerButtonsByText];
        
        console.log('Found login buttons:', allLoginButtons.length);
        console.log('Found register buttons:', allRegisterButtons.length);
        
        // Hide buttons if they exist
        allLoginButtons.forEach(button => {
            console.log('Hiding login button:', button);
            button.style.display = 'none';
            button.style.visibility = 'hidden';
        });
        
        allRegisterButtons.forEach(button => {
            console.log('Hiding register button:', button);
            button.style.display = 'none';
            button.style.visibility = 'hidden';
        });
        
        // Hide auth container if it exists
        const authContainer = document.getElementById('authContainer');
        if (authContainer) {
            console.log('Hiding auth container');
            authContainer.style.display = 'none';
            authContainer.style.visibility = 'hidden';
        }
        
        // Also try to hide by class
        const authButtonsContainers = document.querySelectorAll('.auth-buttons');
        console.log('Found auth buttons containers:', authButtonsContainers.length);
        authButtonsContainers.forEach(container => {
            console.log('Hiding auth buttons container');
            container.style.display = 'none';
            container.style.visibility = 'hidden';
        });
        
        // Show user menu if it exists
        const userMenu = document.getElementById('userMenu');
        if (userMenu) {
            console.log('Showing user menu');
            userMenu.style.display = 'block';
            userMenu.style.visibility = 'visible';
        }
        
        // Show username if it exists
        const userInfo = localStorage.getItem('user_info');
        if (userInfo) {
            try {
                const user = JSON.parse(userInfo);
                const username = user.first_name || user.username || 'User';
                console.log('Setting username to:', username);
                
                // Find username display elements
                const usernameDisplays = document.querySelectorAll('.user-name, #userDisplayName, #userName');
                usernameDisplays.forEach(display => {
                    if (display) {
                        display.textContent = username;
                        display.style.display = 'inline-block';
                    }
                });
                
                // Set user email if element exists
                const userEmail = document.getElementById('userEmail');
                if (userEmail && user.email) {
                    userEmail.textContent = user.email;
                }
            } catch (error) {
                console.error('Error parsing user info:', error);
            }
        }
    } else {
        console.log('User is not authenticated, showing login/register buttons');
        
        // Find login and register buttons in the new UI
        const loginButtons = document.querySelectorAll('a[href="login.html"], .login-btn, .auth-btn.login-btn');
        const registerButtons = document.querySelectorAll('a[href="register.html"], .register-btn, .auth-btn.register-btn');
        
        // Show buttons if they exist
        loginButtons.forEach(button => {
            button.style.display = 'inline-block';
            button.style.visibility = 'visible';
        });
        
        registerButtons.forEach(button => {
            button.style.display = 'inline-block';
            button.style.visibility = 'visible';
        });
        
        // Show auth container if it exists
        const authContainer = document.getElementById('authContainer');
        if (authContainer) {
            authContainer.style.display = 'flex';
            authContainer.style.visibility = 'visible';
        }
        
        // Also try to show by class
        const authButtonsContainers = document.querySelectorAll('.auth-buttons');
        authButtonsContainers.forEach(container => {
            container.style.display = 'flex';
            container.style.visibility = 'visible';
        });
        
        // Hide user menu if it exists
        const userMenu = document.getElementById('userMenu');
        if (userMenu) {
            userMenu.style.display = 'none';
            userMenu.style.visibility = 'hidden';
        }
    }
}

// Run immediately
console.log('Running updateAuthButtons immediately');
updateAuthButtons();

// Update auth buttons when page loads
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOMContentLoaded event triggered, updating auth buttons');
    updateAuthButtons();
    
    // Set up periodic check (every 2 seconds)
    setInterval(updateAuthButtons, 2000);
});

// Update auth buttons when localStorage changes
window.addEventListener('storage', (event) => {
    if (event.key === 'auth_token' || event.key === 'user_info') {
        console.log('Auth data changed, updating auth buttons');
        updateAuthButtons();
    }
}); 