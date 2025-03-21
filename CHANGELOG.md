# Changelog

## [0.9.8.1] - 2025-03-21


- **UI Improvements**
  - **User Menu Refinement**
    - Removed the Profile button from the username dropdown menu
    - Simplified the user menu interface by removing unimplemented functionality
    - Improved user interface clarity by removing the "Profile page coming soon" placeholder
    - Updated all HTML templates (index.html, status.html, settings-new.html) for consistency

- **Bug Fixes**
  - **Add Warranty Form Wizard**
    - Fixed issue where clicking the "Next" button sometimes skipped the "Documents" tab
    - Removed duplicate DOMContentLoaded event listeners in script.js to prevent multiple form initializations
    - Implemented clone-and-replace technique to ensure clean event listener attachment
    - Added comprehensive logging for tab navigation to assist future debugging
    - Enhanced form validation to ensure a smoother user experience
    - Improved error handling when navigating between form tabs

  - **Warranty Filtering**
    - Fixed "ReferenceError: applyFilters is not defined" error in script.js
    - Added missing applyFilters function that was referenced but not implemented
    - Restored filter functionality for the warranty list on the main page
    - Enhanced console logging to provide better debugging information

- **Upload Size Increase**
  - Increased maximum file upload size from 16MB to 32MB for invoices and manuals
  - Updated `MAX_CONTENT_LENGTH` in Flask configuration from 16MB to 32MB
  - Added `client_max_body_size 32M` directive to Nginx configuration
  - Updated documentation in memory bank to reflect new file size limits
  - Enhanced fallback Nginx configuration in Dockerfile with upload size limits
  - Added frontend validation to prevent oversized file uploads
  - Improved error handling for 413 Request Entity Too Large errors
  - Added detailed error messages with file size information

- **UI Consistency Improvements**
  - **Settings Page Header**
    - Fixed settings page header to match the structure and appearance of the home page
    - Standardized navigation menu appearance across all application pages
    - Removed duplicate settings container from the header for cleaner UI
    - Added proper "active" class to the current page in the navigation menu
  - **JavaScript Enhancements**
    - Improved error handling in settings-new.js with proper null checking
    - Enhanced preferences saving functionality with graceful fallbacks
    - Fixed dark mode toggle to work without the header settings container
    - Prevented console errors when UI elements were changed or removed

## [0.9.8.0] - 2025-03-21

- **Feature Added**
  - **Expiring Soon Preferences:** Number of days before warranty expiration to mark as "Expiring Soon" now added to the settings page.

- **UI Improvements**
  - **Cleanup**
    - Removed test-related buttons from the settings gear menu in index.html and status.html
    - Kept only the Test API button in the Admin section of settings page
    - Removed redundant "Old Settings" link from settings page gear menu
  - **General Refinements**
    - Streamlined user interface by removing development/testing elements
    - Improved overall UI professionalism and user experience

- **Bug Fixes**
  - **Expiring Soon Preferences**
    - Fixed issue where "expiring soon" preference set in settings didn't affect warranty status on the main dashboard
    - Resolved inconsistency between token key names (`authToken` vs `auth_token`) causing authorization failures
    - Improved preferences loading in `script.js` to properly await API responses
    - Enhanced initialization sequence to ensure preferences are loaded before processing warranties
    - Implemented real-time reprocessing of warranties when preferences change
    - Added detailed logging to track preference values during warranty processing
    - Updated DOM initialization to avoid duplicate warranty loading
  - **Status Filter in Dashboard**
    - Fixed issue where status dropdown filter on status page showed "No warranties match your search criteria" when selecting specific statuses
    - Modified dashboard to fetch complete warranty data for comprehensive filtering instead of only using pre-filtered recent warranties
    - Added null checks and fallback values to prevent errors with incomplete warranty data
    - Enhanced filtering logic to properly handle all warranty status types
    - Fixed sort header click handler to use the correct data attribute
    - Improved error handling and feedback messages when no warranties match filter criteria

## [0.9.7.9] - 2025-03-21

  - **API Security Improvements**
    - Fixed "Authentication attempt without token" warnings in logs
    - Updated Dockerfile health check to use root URL instead of protected API endpoint
    - Modified test-api.js to include authentication tokens with requests

## [0.9.7.8] - 2025-03-20

- **Security Enhancements**
  - **Secure File Access System**
    - Implemented comprehensive security controls for uploaded files (invoices, manuals)
    - Added two secure file serving endpoints with authentication and authorization
    - Created client-side utility functions for secure file handling
    - Blocked direct access to the uploads directory via nginx configuration
    - Added ownership verification to ensure users can only access their own files
    - Implemented protection against path traversal attacks
    - Enhanced logging for all file access attempts
  - **Frontend Security Integration**
    - Created new file-utils.js with secureFilePath and openSecureFile functions
    - Updated all file links to use secure handling methods
    - Added proper authentication token handling for file downloads
   
## [0.9.7.7] - 2025-03-15
- **Fixes**
  - Status of warranties are now centred in list view

## [0.9.7.5] - 2025-03-14
- **Fixes**
  - Removed remember me
  - Fixed admin settings, admins can now remove users
  - Admins can now disable registrations


## [0.9.7] - 2025-03-13

- **Authentication Enhancements**
  - Added "Remember Me" functionality to the login page, allowing users to stay logged in across sessions.
  - Implemented auto-login feature that checks for a valid session cookie and automatically logs in users if they have opted for "Remember Me".
  - Updated the login endpoint to accept a `remember_me` parameter and set a persistent session cookie when checked.
  - Created a new `/api/auth/auto-login` endpoint to handle auto-login requests.

- **User Management Improvements**
  - Enhanced user registration process to validate email format and password strength.
  - Added functionality to check if registration is enabled or disabled via the `/api/auth/registration-status` endpoint.
  - Implemented user profile update functionality, allowing users to change their first and last names.
  - Added admin-only endpoints for managing user accounts, including viewing, updating, and deleting users.
  - **User Deletion Functionality**
    - Enhanced modal functionality for user deletion, including improved error checking and logging.
    - Improved `deleteUser` function with better error handling and user ID retrieval.
    - Added support for handling both numeric IDs and usernames in the deletion process.
    - Created diagnostic functions to test modal functionality and user deletion processes.
    - Improved event handling for user-related actions, ensuring proper setup of event listeners.

- **Admin Management**
  - View Users: Admins can view a list of all registered users, including their details such as usernames, email addresses, and account statuses.
  - Delete User Accounts: Admins have the ability to delete user accounts, removing them from the system entirely.
  - Monitor System Health: Admins can check the health of the application and server, ensuring that everything is running smoothly.

- **Settings Page Updates**
  - Created a settings page for users to manage their preferences, including email notifications and default view settings.
  - Implemented backend support for retrieving and updating user preferences via the `/api/auth/preferences` endpoint.
  - Added validation for user preferences to ensure only valid values are accepted.

- **Database Enhancements**
  - Updated database schema to include user sessions and password reset tokens for improved security and functionality.
  - Added indexes to improve query performance for user and warranty data.
  - Implemented error handling and logging for database operations to facilitate easier debugging and maintenance.

- **UI/UX Improvements**
  - Enhanced the login form with a "Remember Me" checkbox and improved styling for better user experience.
  - Added loading indicators and toast notifications for better feedback during authentication processes.
  - Improved the overall layout and design of the settings and authentication pages for a more cohesive look.
  - Added a "Show Users List" button to the admin controls for easy access to user management.

- **Security Enhancements**
  - Implemented secure cookie handling for session tokens to prevent XSS attacks.
  - Added validation checks for user input to prevent SQL injection and other common vulnerabilities.
  - Ensured that sensitive operations are protected by authentication and authorization checks.

- **What's not working**
  - The menu still needs work done, the gear icon is not consistent 
  - When putting in the wrong password, you will need to refresh the page and try again manually.
  - Email notification still doesn't work
  - Users can't delete their own account, but admins can


## [0.5.2] - 2025-03-09

### Changed
- Enhanced user interface consistency and dark mode support
  - Fixed alignment issues between search field and status dropdown
  - Improved empty state display in both light and dark modes
  - Standardized padding and sizing for search and filter controls
  - Better vertical alignment of form controls in table header

### Fixed
- Proper centering of "No warranties" message in the dashboard table
  - Implemented responsive overlay for empty state messages
  - Fixed background colors in dark mode for empty state displays
  - Ensured consistent text color across all themes
  - Improved mobile responsiveness for empty state messages

## [0.5.1] - 2025-03-08

### Changed
- Improved warranty status display
  - Status information now consistently displayed at the bottom of warranty cards
  - Better visual hierarchy with status as the last item before document links
  - Enhanced color-coding for different status types (active, expiring, expired)
  - Consistent status positioning across all view types (grid, list, table)

### Fixed
- Table view layout and display issues
  - Fixed product names being truncated in table view
  - Improved column width distribution for better content display
  - Prevented document links from overflowing their container
  - Enhanced mobile responsiveness for table view
  - Better alignment of table headers with content
  - Improved styling of links in table view for better readability
  - Fixed vertical stacking of document links on smaller screens


## [0.5.0] - 2025-03-07

### Added
- Enhanced filtering and sorting capabilities
  - Status filter (All, Active, Expiring Soon, Expired)
  - Multiple sorting options (Expiration Date, Purchase Date, Name)
  - Export filtered warranties as CSV
  - Improved filter controls layout
  - Mobile-responsive filter design
- Multiple view options for warranty display
  - Grid view with card layout (default)
  - List view for compact horizontal display
  - Table view for structured data presentation
  - View preference saved between sessions
  - Responsive design for all view types
- Optional purchase price tracking
  - Users can now add purchase prices to warranties
  - Price information displayed in warranty cards
  - Currency formatting with dollar sign
  - Included in warranty summary and exports

### Changed
- Completely redesigned user interface
  - Modern card-based layout for warranties
  - Enhanced filter controls with improved styling
  - Better visual hierarchy with labeled filter groups
  - Custom dropdown styling with intuitive icons
  - Improved spacing and alignment throughout
  - Consistent color scheme and visual feedback
  - Responsive grid layout for warranty cards

### Fixed
- Status indicator borders now correctly displayed for all warranty states
  - Green border for active warranties
  - Orange border for warranties expiring soon
  - Red border for expired warranties
- Consistent status styling across all warranty cards
- Form now resets to first tab after successful warranty submission
- Manual filename now properly cleared when form is reset

## [0.4.0] - 2025-03-07

### Added
- Improved warranty creation process
  - Multi-step form with intuitive navigation
  - Progress indicator showing completion status
  - Enhanced validation with clear error messages
  - Summary review step before submission
  - Expiration date preview in summary
  - Responsive design for all device sizes

### Fixed
- Progress indicator alignment issue in multi-step form
  - Contained indicator within form boundaries
  - Prevented overflow with improved CSS approach
  - Ensured consistent tab widths for better alignment
- Improved tab navigation visual feedback

## [0.3.0] - 2025-03-07

### Added
- Product manual upload support
  - Users can now upload a second document for product manuals
  - Manual documents are displayed alongside invoices in the warranty details
  - Both add and edit forms support manual uploads
- Product URL support
  - Users can now add website URLs for products
  - Links to product websites displayed in warranty cards
  - Easy access to product support and information pages

### Changed
- Improved document link styling for consistency
  - Enhanced visual appearance of document links
  - Consistent styling between invoice and manual links
  - Better hover effects for document links
  - Fixed styling inconsistencies between document links
- Improved warranty card layout
  - Document links now displayed side by side for better space utilization
  - Responsive design adapts to different screen sizes
  - More compact and organized appearance

### Fixed
- Styling inconsistency between View Invoice and View Manual buttons
- Removed unused CSS file to prevent styling conflicts

## [0.2.5-beta] - 2025-03-07

### Added
- Product manual upload support
  - Users can now upload a second document for product manuals
  - Manual documents are displayed alongside invoices in the warranty details
  - Both add and edit forms support manual uploads

### Changed
- Improved document link styling for consistency
  - Enhanced visual appearance of document links
  - Consistent styling between invoice and manual links
  - Better hover effects for document links
  - Fixed styling inconsistencies between document links

### Fixed
- Styling inconsistency between View Invoice and View Manual buttons
- Removed unused CSS file to prevent styling conflicts


## [0.2.0-beta] - 2025-03-06

### Added
- Export functionality for warranty data as CSV
- Refresh button for manual data updates
- Search and filtering options for warranty list
- Enhanced mobile responsiveness

### Changed
- Removed Debug Information panel from status page
- Improved error handling and data validation across all dashboard functions
- Enhanced chart creation with support for various data formats
- Streamlined user interface by removing development elements
- Improved data normalization for warranty information
- Added fallback mechanisms for missing or invalid data
- Updated status chart calculations for better accuracy

### Fixed
- API connection error handling
- Chart instance memory leaks
- Invalid data structure handling from API responses
- Negative value calculations in status charts

[0.2.0-beta]: [https://github.com/username/warracker/releases/tag/v0.05.2-beta](https://github.com/sassanix/Warracker/releases/tag/0.2.0)

## [0.1.0] - New Features and enhancements 

### Added
- Basic warranty tracking functionality
- Dashboard with warranty statistics
- Timeline visualization
- Status overview chart
- Recent expirations list

## [0.05.2-beta] - 2025-03-05

### Added
- Multiple serial numbers support for warranties
  - Users can now add multiple serial numbers per warranty item
  - Dynamic form fields for adding/removing serial numbers
  - Database schema updated to support multiple serial numbers

### Changed
- Enhanced warranty management interface
  - Improved form handling for serial numbers
  - Better organization of warranty details
- Optimized database queries with new indexes
  - Added index for serial numbers lookup
  - Added index for warranty ID relationships

### Technical
- Database schema improvements
  - New `serial_numbers` table with proper foreign key constraints
  - Added indexes for better query performance
  - Implemented cascading deletes for warranty-serial number relationships

### Fixed
- Form validation and handling for multiple serial numbers
- Database connection management and resource cleanup

[0.05.2-beta]: https://github.com/username/warracker/releases/tag/v0.05.2-beta
