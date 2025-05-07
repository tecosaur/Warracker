// Version checker for Warracker
document.addEventListener('DOMContentLoaded', () => {
    const currentVersion = '0.9.9.5'; // Current version of the application
    const updateStatus = document.getElementById('updateStatus');
    const updateLink = document.getElementById('updateLink');

    // Function to compare versions
    function compareVersions(v1, v2) {
        const v1Parts = v1.split('.').map(Number);
        const v2Parts = v2.split('.').map(Number);
        
        for (let i = 0; i < Math.max(v1Parts.length, v2Parts.length); i++) {
            const v1Part = v1Parts[i] || 0;
            const v2Part = v2Parts[i] || 0;
            
            if (v1Part > v2Part) return 1;
            if (v1Part < v2Part) return -1;
        }
        return 0;
    }

    // Function to check for updates
    async function checkForUpdates() {
        try {
            const response = await fetch('https://api.github.com/repos/sassanix/Warracker/releases/latest');
            if (!response.ok) throw new Error('Failed to fetch release information');
            
            const data = await response.json();
            const latestVersion = data.tag_name.replace('v', ''); // Remove 'v' prefix if present
            
            const comparison = compareVersions(latestVersion, currentVersion);
            
            if (comparison > 0) {
                // New version available
                updateStatus.textContent = `New version ${data.tag_name} available!`;
                updateStatus.style.color = 'var(--success-color)';
                updateLink.href = data.html_url;
                updateLink.style.display = 'inline-block';
            } else {
                // Up to date
                updateStatus.textContent = 'You are using the latest version';
                updateStatus.style.color = 'var(--success-color)';
            }
        } catch (error) {
            console.error('Error checking for updates:', error);
            updateStatus.textContent = 'Failed to check for updates';
            updateStatus.style.color = 'var(--error-color)';
        }
    }

    // Check for updates when the page loads
    checkForUpdates();
}); 