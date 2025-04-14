// theme-loader.js
(function() {
    try {
        // Function to apply the theme
        function applyTheme(isDark) {
            document.documentElement.setAttribute('data-theme', isDark ? 'dark' : 'light');
            console.log(`Theme applied on load: ${isDark ? 'dark' : 'light'}`);
        }

        // Check localStorage for saved theme
        const savedTheme = localStorage.getItem('darkMode');

        if (savedTheme !== null) {
            // Apply saved theme
            applyTheme(savedTheme === 'true');
        } else {
            // Fallback to system preference if no theme saved
            const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            console.log(`No saved theme found, falling back to system preference: ${prefersDarkMode ? 'dark' : 'light'}`);
            applyTheme(prefersDarkMode);
            // Optionally, save the detected system preference as the initial setting
            // localStorage.setItem('darkMode', prefersDarkMode);
        }
    } catch (e) {
        console.error("Error applying theme from theme-loader.js:", e);
        // Fallback to light theme in case of error
        document.documentElement.setAttribute('data-theme', 'light');
    }
})();
