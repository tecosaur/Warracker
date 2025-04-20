// theme-loader.js
(function() {
    try {
        // Function to apply the theme directly to the root element
        function applyTheme(isDark) {
            const theme = isDark ? 'dark' : 'light';
            document.documentElement.setAttribute('data-theme', theme);
            // No need for console log in production loader script
            // console.log(`Theme applied on load: ${theme}`);
        }

        // Default to light theme initially
        let isDarkMode = false;

        // Check localStorage for the standardized 'darkMode' key
        const savedTheme = localStorage.getItem('darkMode');

        if (savedTheme !== null) {
            // Use the saved theme preference
            isDarkMode = savedTheme === 'true';
        } else {
            // Fallback to system preference if no theme saved in localStorage
            const prefersDarkMode = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
            // console.log(`No saved theme found, falling back to system preference: ${prefersDarkMode ? 'dark' : 'light'}`);
            isDarkMode = prefersDarkMode;
            // Optionally, save the detected system preference as the initial setting for future loads
            // localStorage.setItem('darkMode', isDarkMode); // Consider if this is desired behavior
        }

        // Apply the determined theme
        applyTheme(isDarkMode);

    } catch (e) {
        console.error("Error applying theme from theme-loader.js:", e);
        // Fallback to light theme in case of error
        document.documentElement.setAttribute('data-theme', 'light');
    }
})();
