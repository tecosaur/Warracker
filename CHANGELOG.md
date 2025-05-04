# Changelog

## [0.9.9.4] - 2025-05-04

### Fixed
- **Theme Persistence & Consistency:**
  - Refactored dark mode logic to use only a single `localStorage` key (`darkMode`) as the source of truth for theme preference across all pages.
  - Removed all legacy and user-prefixed theme keys (e.g., `user_darkMode`, `admin_darkMode`, `${prefix}darkMode`).
  - Ensured all theme toggles and settings update only the `darkMode` key, and all pages read only this key for theme initialization.
  - Verified that `theme-loader.js` is included early in every HTML file to prevent flashes of incorrect theme.
  - Cleaned up redundant or conflicting theme logic in all frontend scripts and HTML files.
  - Theme preference now persists reliably across logins, logouts, and browser sessions (except in incognito/private mode, where localStorage is temporary by design).
  _Files: `frontend/script.js`, `frontend/settings-new.js`, `frontend/status.js`, `frontend/register.html`, `frontend/reset-password.html`, `frontend/reset-password-request.html`, `frontend/theme-loader.js`, all main HTML files._

### Added
- **Admin/User Tag Separation:**
  - Implemented distinct tags for Admins and regular Users.
  - Tags created by an Admin are only visible to other Admins.
  - Tags created by a User are only visible to other Users.
  - Added `is_admin_tag` boolean column to the `tags` table via migration (`backend/migrations/009_add_admin_flag_to_tags.sql`).
  - Backend API endpoints (`/api/tags`, `/api/warranties`, `/api/warranties/<id>/tags`) updated to filter tags based on the logged-in user's role (`is_admin`).
  - Tag creation (`POST /api/tags`) now automatically sets the `is_admin_tag` flag based on the creator's role.
  - Tag update (`PUT /api/tags/<id>`) and deletion (`DELETE /api/tags/<id>`) endpoints now prevent users/admins from modifying tags belonging to the other role.
  _Files: `backend/app.py`, `backend/migrations/009_add_admin_flag_to_tags.sql`_

  - **Version Check:**

  - Added a version checker to the About page (`frontend/about.html`) that compares the current version with the latest GitHub release and displays the update status.
    _Files: `frontend/about.html`, `frontend/version-checker.js`_

- **Mobile Home Screen Icon Support:**
  - Added support for mobile devices to display the app icon when added to the home screen.
  - Included `<link rel="apple-touch-icon" sizes="180x180">` for iOS devices, referencing a new 512x512 PNG icon.
  - Added a web app manifest (`manifest.json`) referencing the 512x512 icon for Android/Chrome home screen support.
  - Updated all main HTML files to include these tags for consistent experience across devices.
  _Files: `frontend/index.html`, `frontend/login.html`, `frontend/register.html`, `frontend/about.html`, `frontend/reset-password.html`, `frontend/reset-password-request.html`, `frontend/status.html`, `frontend/settings-new.html`, `frontend/manifest.json`, `frontend/img/favicon-512x512.png`_

- **Optional Vendor Field for Warranties:**
  - Users can now specify the vendor (e.g., Amazon, Best Buy) where a product was purchased, as an optional informational field for each warranty.
  - The field is available when adding a new warranty and when editing an existing warranty.
  - The vendor is displayed on warranty cards and in the summary tab of the add warranty wizard.
  - The vendor field is now searchable alongside product name, notes, and tags.
  - Backend API and database updated to support this field, including a migration to add the column to the warranties table.
  - Editing a warranty now correctly updates the vendor field.
  _Files: `backend/app.py`, `backend/migrations/017_add_vendor_to_warranties.sql`, `frontend/index.html`, `frontend/script.js`_

- **Serial Number Search:**
  - Enhanced search functionality to include serial numbers.
  - Updated search input placeholder text to reflect serial number search capability.
  _Files: `frontend/script.js`, `frontend/index.html`_

- **CSV Import Vendor Field:**
  - Added support for importing the `Vendor` field via CSV file upload.
  - The CSV header should be `Vendor`.
  _Files: `backend/app.py`, `frontend/script.js`_

- **Date Format Customization:**
  - Users can now choose their preferred date display format in Settings > Preferences.
  - Available formats include:
    - Month/Day/Year (e.g., 12/31/2024)
    - Day/Month/Year (e.g., 31/12/2024)
    - Year-Month-Day (e.g., 2024-12-31)
    - Mon Day, Year (e.g., Dec 31, 2024)
    - Day Mon Year (e.g., 31 Dec 2024)
    - Year Mon Day (e.g., 2024 Dec 31)
  - The selected format is applied to purchase and expiration dates on warranty cards.
  - The setting persists across sessions and is synchronized between open tabs.
  _Files: `frontend/settings-new.html`, `frontend/settings-new.js`, `frontend/script.js`_

- **IPv6 Support:** Added `listen [::]:80;` directive to the Nginx configuration (`nginx.conf`) to enable listening on IPv6 interfaces alongside IPv4.
  _Files: `nginx.conf`_

- **Cloudflare Compatibility:** Added `<script data-cfasync="false" src="/javascript.js">` to the `<head>` of the status page (`frontend/status.html`) to ensure proper loading when behind Cloudflare.
  _Files: `frontend/status.html`_

  ### Changed
  - **Migration System Overhaul:** Refactored the database migration system for improved reliability and consistency.
  - **House cleaning**: Removed redundant files such as migrations, .env, and uploads folder. 
  - **Warranty Listing:** Admins now only see their own warranties on the main warranty list (`/api/warranties`).
  - **Warranty Visibility:** Fixed issue where admins could see all users' warranties. Now both admins and regular users only see their own warranties on all pages.
  _Files: `backend/app.py`_

**Bug Fixes:**

*   **Date Handling:** Fixed issues causing warranty purchase and expiration dates to display incorrectly (off by one day) due to timezone differences:
    *   **Backend:** Corrected expiration date calculation in `backend/app.py` by removing the inaccurate `timedelta` fallback logic and ensuring the `python-dateutil` library (using `relativedelta`) is consistently used for accurate year addition.
    *   **Backend:** Added `python-dateutil` to `backend/requirements.txt` dependencies.
    *   **Frontend:** Updated date parsing in `frontend/script.js` (`processWarrantyData`) to use `Date.UTC()` when creating `Date` objects from `YYYY-MM-DD` strings, preventing local timezone interpretation.
    *   **Frontend:** Simplified and corrected date formatting in `frontend/script.js` (`formatDate`) to always use UTC date components (`getUTCFullYear`, etc.) for display, bypassing potential `toLocaleDateString` timezone issues.
    *   **Frontend:** Fixed purchase date display in the "Add Warranty" summary tab (`updateSummary` in `frontend/script.js`) by applying the same UTC-based parsing and formatting used elsewhere, resolving the off-by-one-day error during summary view.
*   **Fractional Warranty Years & Date Accuracy:** Corrected the backend expiration date calculation (`backend/app.py`) to accurately handle fractional warranty years (e.g., 1.5 years) and prevent off-by-one-day errors. 
    *   The initial fix for fractional years used an approximation (`timedelta`) which sometimes resulted in dates being a day early.
    *   The calculation now uses `dateutil.relativedelta` after decomposing the fractional years into integer years, months, and days, ensuring correct handling of leap years and month lengths.
*   **UI:** Fixed toasts overlapping header menu due to z-index conflict (`style.css`).
*   **API:** Fixed bug preventing updates to user preferences if only the timezone was changed (`app.py`).
*   **Settings:** Resolved issue where opening the settings page in multiple tabs could cause both tabs to refresh continuously and potentially log the user out. This involved:
    *   Preventing `settings-new.js` from unnecessarily updating `user_info` in `localStorage` on load.
    *   Changing the `storage` event listener in `include-auth-new.js` to update the UI directly instead of reloading the page when auth data changes.
    *   Removing redundant checks (`setInterval`) and `storage` listener from `fix-auth-buttons.js` to prevent conflicts.

**New Features & Enhancements:**

*   **API:** Added `/api/timezones` endpoint to provide a structured list of timezones grouped by region (`app.py`).

### Fixed
- **Tag Visibility:** Fixed an issue where tag visibility was incorrectly reversed between Admins and Users (Users saw Admin tags and vice-versa). Adjusted backend logic to correctly display tags based on role.
  _Files: `backend/app.py`_
- Fixed currency symbol not persisting after browser restart/re-login:
    - Prevented main warranty list from rendering before user authentication and preferences are fully loaded.
    - Ensured preferences (currency, date format, etc.) are fetched from API and saved to localStorage immediately after login.
    - Corrected inconsistent user type prefix (`user_` vs `admin_`) determination during initial page load.

## [0.9.9.3] - 2025-04-27

### Added

 - **Document Deletion in Edit Warranty:**
    - Users can now delete uploaded documents (Invoice/Receipt and Product Manual) when editing an existing warranty.
    - The edit modal now displays "Delete Invoice" and "Delete Manual" buttons if a document is present. Clicking these marks the document for deletion, which is processed when saving changes.
    - Backend and database are updated to remove the file from storage and clear the reference in the database.
  _Files: `backend/app.py`, `frontend/index.html`, `frontend/script.js`_

 - **Notes for Warranties:**
    - Users can now add, view, and edit freeform notes for each warranty.
    - Notes can be entered when adding or editing a warranty, and are accessible from the warranty card via a dedicated "Notes" link.
    - A modal dialog allows users to view and edit notes in place, with support for multi-line text and instant updates.
    - Notes are searchable and filterable alongside product names and tags.
    - Backend and database support for notes has been added, including migration and API changes.
    - UI includes clear styling for notes links and modal, with full support for both light and dark themes.
  _Files: `backend/app.py`, `backend/migrations/014_add_notes_to_warranties.sql`, `frontend/index.html`, `frontend/script.js`, `frontend/style.css`_

 - **Currency Symbol Customization:**
    - Users can now select their preferred currency symbol ($, €, £, ¥, ₹, or a custom one) in the settings page.
    - The selected symbol is now displayed next to purchase prices on warranty cards on the main page (`index.html`).
  _Files: `backend/app.py`, `backend/migrations/006_add_currency_symbol_column.py`, `frontend/settings-new.html`, `frontend/settings-new.js`, `frontend/index.html`, `frontend/script.js`, `frontend/style.css`_

 - **Password Reset Functionality:**
    - Users can now reset their password via a secure, token-based email workflow.
    - Added a "Forgot Password?" link on the login page that initiates the process.
    - Users receive an email with a unique link to set a new password.
    - Implemented frontend pages for requesting the reset and setting the new password.
    - Backend handles token generation, validation, email sending, and password updates.
  _Files: `backend/app.py`, `frontend/login.html`, `frontend/reset-password-request.html`, `frontend/reset-password.html`, `backend/migrations/003_add_users_table.sql` (or similar migration)_

### Changed
- **Status Page Table:** Removed the "Actions" column (and its buttons) from the "Recently Expired or Expiring Soon" table on `status.html` for a cleaner look.
- **Table Layout:** Updated the table and CSS to use dynamic column widths, eliminating empty space after the Status column and ensuring the table fills the available space naturally.
- **UI Polish:** Fixed awkward right-side spacing in the table and removed all flex styling and fixed-width rules for the last column, so the table now adapts responsively to its content.
- **CSS Cleanup:** Cleaned up and removed obsolete or conflicting CSS rules for the recent expirations table, resolving layout and syntax errors.
- **Status Page Table Sorting:**
    - Fixed date comparison logic in the sort function to correctly handle `Date` objects.
    - Refactored event listener attachment for sortable table headers to prevent duplicate listeners being added, resolving issues where sorting only worked once or behaved erratically.
    - Ensured all event listeners (sort, filter, search, export, refresh) are attached reliably after initial data load and rendering.
  _Files: `frontend/status.html`, `frontend/status.js`, `frontend/style.css`_

- **Mobile Export Button:** On mobile devices, the export button at the bottom of the status page now only displays the icon (no text), for a cleaner and more compact UI. The text remains visible on desktop.
- **Mobile Search Functionality:** The search box for recent expirations at the bottom of the status page now works correctly on mobile, with event listeners properly initialized to ensure filtering works as expected on all devices.
  _Files: `frontend/status.html`, `frontend/status.js`, `frontend/style.css`_

### Fixed
- **Settings Toggle Size:** Fixed inconsistent toggle switch sizing on mobile views, ensuring all toggles render at the correct dimensions (`47x24px`).
  _File: `frontend/settings-styles.css`_
- **Username Display:** Resolved an issue where user interface elements sometimes incorrectly displayed the username instead of the first name (or vice versa).
  _Files: `frontend/settings-new.js`, `frontend/auth.js` 
- **List/Table View:** Implemented updates and fixes for the warranty list and table views, improving layout and data presentation.
  _Files: `frontend/index.html`, `frontend/script.js`, `frontend/style.css`_

## [0.9.9.2] - 2025-04-20

### Added
- **Warranty Years (Fractional Support):**
  - You can now enter fractional (decimal) values for warranty periods (e.g., 1.5 years) when adding or editing warranties.
  - The backend, frontend UI, and CSV import/export all support decimal warranty years.
  - Validation and expiration date calculations have been updated to handle decimal years correctly.
  - The UI now allows decimal input for warranty years and displays fractional years in summaries and warranty lists.
  _Files: `backend/app.py`, `frontend/index.html`, `frontend/script.js`_
- **Import** button added, and functional. Must use CSV file format.
  - ## 📦 Product Information Entry Requirements

| Field Name     | Format / Example                          | Required?                                              | Notes                                                                 |
|----------------|-------------------------------------------|--------------------------------------------------------|-----------------------------------------------------------------------|
| **ProductName** | Text                                       | ✅ Yes                                                  | Provide the name of the product.                                     |
| **PurchaseDate** | Date (`YYYY-MM-DD`, e.g., `2024-05-21`)   | ✅ Yes                                                  | Use ISO format only.                                                 |
| **WarrantyYears** | Whole Number (`1`, `3`, `10`)             | ✅ Yes, unless `IsLifetime` is `TRUE`                   | Must be between `1` and `100` if provided.                           |
| **IsLifetime**  | `TRUE` or `FALSE` (case-insensitive)       | ❌ No (Optional)                                        | If omitted, defaults to `FALSE`.                                     |
| **PurchasePrice** | Number (`199.99`, `50`)                  | ❌ No (Optional)                                        | Cannot be negative if provided.                                      |
| **SerialNumber** | Text (`SN123`, `SN123,SN456`)             | ❌ No (Optional)                                        | For multiple values, separate with commas.                           |
| **ProductURL**   | Text (URL format)                         | ❌ No (Optional)                                        | Full URL to product page (optional field).                           |
| **Tags**         | Text (`tag1,tag2`)                        | ❌ No (Optional)                                        | Use comma-separated values for multiple tags.                        |


### Changed
- **Theme:** Unified theme persistence using a single `localStorage` key (`darkMode`) and centralized the loading logic in `theme-loader.js` to enhance consistency and eliminate theme-flashing on load.  
  _Files: `frontend/theme-loader.js`, `frontend/script.js`, `frontend/status.js`, `frontend/settings-new.js`, `frontend/settings-new.html`_

- **UI/UX:** Updated the "Add Warranty" modal behavior to only close when the internal 'X' button is clicked. Clicking the backdrop no longer closes the modal. This change is specific to this modal—others retain default backdrop behavior.  
  _File: `frontend/script.js`_

### Fixed
- **Wizard Navigation:** 
  - Ensured the summary tab in the "Add Warranty" wizard displays and updates correctly.  
  - Resolved JS errors (`TypeError: Assignment to constant variable`, `ReferenceError: tabs is not defined`) that affected tab functionality.  
  - Fixed scope issues with backdrop click handlers impacting modal behavior.  
  _File: `frontend/script.js`_

- **Header Layout (Desktop):** Standardized header layout across pages by wrapping elements in a `.header-right-group` container and applying consistent styles.  
  _Files: `index.html`, `status.html`, `about.html`, `settings-new.html`, `frontend/header-fix.css`_

- **Header Layout (Mobile):** Corrected alignment of header elements—title is now left-aligned, user/settings icons right-aligned, and navigation links centered below. Used `!important` to resolve conflicts with desktop styles.  
  _File: `frontend/mobile-header.css`_

- **Theme:** Fixed site-wide dark/light mode persistence. Changes made on one page now reflect consistently across all pages. Standardized use of `darkMode` and `${prefix}darkMode` keys in relevant scripts.  
  _Files: `frontend/status.js`, others using `setTheme` / `initializeTheme`_

- **User Menu:** Fixed dropdown not opening due to a variable typo. Centralized gear menu toggle logic into `auth.js` for consistent behavior, removing redundant initializations.  
  _Files: `frontend/auth.js`, `frontend/script.js`, `frontend/settings-new.js`_

- **JavaScript Errors:** Addressed multiple errors (`ReferenceError`, `TypeError`) related to function order, missing element checks, and incorrect variable usage—primarily impacting `status.html` and pages using `script.js`.  
  _Files: `frontend/script.js`, `frontend/status.js`_

- **API Integration:** Fixed parsing logic for `/api/statistics` response to correctly interpret the API structure.  
  _File: `frontend/status.js`_

### Removed
- **Settings Gear Icon:** The settings gear icon button and its menu have been removed from the header in all main pages for a cleaner and less redundant UI. 
  _Files: `frontend/index.html`, `frontend/status.html`, `frontend/about.html`_


## [0.9.9.1] - 2025-04-13

### Added
- **About Page:** Added a new "About" page accessible via `/about.html` (`frontend/about.html`).
  - Displays application version, links to GitHub repository, releases, author profile, license (AGPL-3.0), and issue tracker.
- **UI:** Added an "About" link to the user menu dropdown in the header, appearing after "Settings" (`frontend/index.html`, `frontend/status.html`, `frontend/settings-new.html`).
- **UI/UX:** Refactored the "Add New Warranty" form into a modal dialog (`#addWarrantyModal`) triggered by a button click, instead of being always visible on the main page (`frontend/index.html`, `frontend/script.js`, `frontend/style.css`).
  - The modal is initially hidden and displayed using JavaScript.
  - Added event listeners to show/hide the modal on button click, close button click, and backdrop click.
  - Implemented `resetAddWarrantyWizard` function to clear the form, reset tabs, tags, and file inputs when the modal is closed or submitted successfully.
  - Modified form submission (`submitForm`) to close and reset the modal upon success.
- **UI:** Moved the "Add New Warranty" button (`#showAddWarrantyBtn`) from the top of the main content area into the header of the "Your Warranties" panel (`.panel-header`) for better context (`frontend/index.html`).
- **Layout:** Adjusted the `.warranties-panel` CSS to span the full width (`grid-column: 1 / -1;`) after the form was moved out of the main grid flow (`frontend/style.css`).
- **Layout:** Updated `.panel-header` CSS to use Flexbox for aligning the title (`h2`) to the left and action buttons (`.panel-header-actions` containing Add Warranty and Refresh buttons) to the right (`frontend/style.css`).
- **Layout:** Removed the `border-bottom` style from the `.panel-header` / `.warranties-panel h2` for a cleaner look (`frontend/style.css`).
- **Branding:** Updated the website `<title>` to include "Warracker" (`frontend/index.html`).
- **UI:** Added an "Add New Warranty" button (`#showAddWarrantyBtn`) to trigger the new modal (`frontend/index.html`).
- **Branding:** Added a `<link>` tag to include a favicon (`/img/favicon.png`) in the website's `<head>` (`frontend/index.html`).
- Site setting for configurable Email Base URL (Admin only).
- Admins can now set the base URL used in password reset and notification emails via Settings > Admin Settings > Site Settings.

### Changed
- **UI:** Ensured header structure, styling, and interactive elements (user menu, settings/dark mode toggle) are consistent across `index.html`, `status.html`, `settings-new.html`, and the new `about.html`.
  - Refactored `about.html` to include standard header HTML and necessary CSS/JS files (`style.css`, `header-fix.css`, `auth.js`, `script.js`, `auth-new.js`, etc.).
  - Added inline script to `about.html` to explicitly initialize header JavaScript functions (`setupUIEventListeners`, `initializeTheme`) after DOM content loads.
- **UI/UX:** Refactored the "Add New Warranty" form into a modal dialog (`#addWarrantyModal`) triggered by a button click, instead of being always visible on the main page (`frontend/index.html`, `frontend/script.js`, `frontend/style.css`).
  - The modal is initially hidden and displayed using JavaScript.
  - Added event listeners to show/hide the modal on button click, close button click, and backdrop click.
  - Implemented `resetAddWarrantyWizard` function to clear the form, reset tabs, tags, and file inputs when the modal is closed or submitted successfully.
  - Modified form submission (`submitForm`) to close and reset the modal upon success.
- **UI:** Moved the "Add New Warranty" button (`#showAddWarrantyBtn`) from the top of the main content area into the header of the "Your Warranties" panel (`.panel-header`) for better context (`frontend/index.html`).
- **Layout:** Adjusted the `.warranties-panel` CSS to span the full width (`grid-column: 1 / -1;`) after the form was moved out of the main grid flow (`frontend/style.css`).
- **Layout:** Updated `.panel-header` CSS to use Flexbox for aligning the title (`h2`) to the left and action buttons (`.panel-header-actions` containing Add Warranty and Refresh buttons) to the right (`frontend/style.css`).
- **Layout:** Removed the `border-bottom` style from the `.panel-header` / `.warranties-panel h2` for a cleaner look (`frontend/style.css`).
- **Branding:** Updated the website `<title>` to include "Warracker" (`frontend/index.html`).
- Password reset and warranty expiration emails now use the configured Email Base URL setting.
- Changed "Registration Enabled" setting in Admin Settings to use a toggle switch for consistency.

### Fixed
- Fixed minor inconsistencies in settings page UI elements.
- Resolved issues with file permissions for database operations.
- Corrected CORS configuration to allow credentials.
- Fixed notification preferences saving issue.
- Ensured admin role permissions are correctly applied.
- Resolved issue where editing a warranty to 'Lifetime' was failing due to validation errors and missing database columns (`updated_at`).

### Added
- Functionality to edit existing warranties to have a lifetime duration.

# [0.9.9.0] - 2025-04-06

### Fixed
- **Tag Management:** Resolved issues with adding and deleting tags.
  - **Backend:** Added the missing `DELETE /api/tags/<tag_id>` API endpoint (`backend/app.py`) to handle tag deletion requests, including removing associations from the `warranty_tags` table.
  - **Frontend:** Corrected the `deleteTag` function (`frontend/script.js`) to use the `DELETE` method and the correct API endpoint.
  - **Frontend:** Improved UI feedback for tag operations:
    - The tag list in the "Manage Tags" modal now updates immediately after adding or deleting a tag (`renderExistingTags`).
    - The tag input fields in the modal are cleared after successfully adding a tag.
    - The tag filter dropdown on the main page updates after adding or deleting tags (`populateTagFilter`).
    - Selected tags display in the add/edit warranty forms update correctly after a tag is deleted (`renderSelectedTags`, `renderEditSelectedTags`).
    - Added loading spinners and improved toast notifications/error messages for tag creation and deletion.

### Added
- **Lifetime Warranty Support**
  - Added lifetime warranty option for both new and existing warranties
  - Implemented database migration to add `is_lifetime` column to warranties table
  - Added lifetime warranty checkbox in add/edit warranty forms
  - Modified warranty display to show "Lifetime" instead of expiration date for lifetime warranties
  - Enhanced warranty status handling to properly manage lifetime warranties
  - Updated statistics and expiring notifications to exclude lifetime warranties
  - Added dynamic form behaviour to hide warranty years input when lifetime is selected

### Changed
- **Backend API**
  - Modified warranty-related endpoints to handle lifetime warranty flag
  - Updated warranty validation to make warranty years optional for lifetime warranties
  - Enhanced warranty processing to handle lifetime warranties differently in statistics
  - Modified expiring warranty notifications to exclude lifetime warranties
  - Updated warranty retrieval to properly sort and display lifetime warranties

### UI/UX Improvements
- Added visual indicators for lifetime warranty status in all view modes (grid, list, table)
- Enhanced form validation to handle lifetime warranty scenarios
- Updated warranty summary view to clearly display lifetime warranty status
- Improved warranty filtering to properly handle lifetime warranties
- Corrected an issue where elements in Dark Mode had sharp corners instead of rounded ones like in Light Mode. Added the missing `--border-radius: 8px;` CSS variable to the `:root[data-theme="dark"]` definition in `frontend/style.css`.


## [0.9.8.9] - 2025-04-03

### Added
- **Settings Page:** Added a new display section within the "Account Settings" card (`settings-new.html`) to show the current user's First Name, Last Name, and Email.

### Changed
- **Settings Page:** The new user information display now updates instantly when the user saves changes to their profile (First/Last Name) without requiring a page refresh (`settings-new.js`).
- **Backend API:** Modified the `/api/auth/user` GET endpoint (`backend/app.py`) to query the database and return the full user profile, including `first_name` and `last_name`, instead of just the basic information available from the authentication token. This ensures the settings page can display the complete, up-to-date user details.
- **Styling:** Added optional CSS rules (`settings-styles.css`) to style the new user information display area on the settings page.

## [0.9.8.8] - 2025-04-03

### Fixed
- Resolved database error ("column updated_at does not exist") occurring when updating user profile (first/last name) or user preferences.
  - Modified SQL UPDATE statements in `backend/app.py` (within `update_profile` function and `/api/auth/preferences` endpoint) to remove references to the non-existent `updated_at` column in `users` and `user_preferences` tables.

## [0.9.8.7] - 2025-04-03

### Fixed
- **Migration System Overhaul:** Refactored the database migration system for improved reliability and consistency.
  - Standardized on `backend/migrations/apply_migrations.py` for applying migrations.
  - Removed obsolete top-level `migrations/` directory and `backend/run_migrations.py` script.
  - Simplified `backend/init.sql` to only handle initial role alterations, removing table creation logic.
  - Corrected `docker-compose.yml` volume mounts and command to use the new migration path (`backend/migrations`).
  - Cleaned up `Dockerfile` by removing redundant migration script calls and ensuring correct migration directory copying.
  - Resolved conflicting `user_preferences` table creation by removing the SQL version and relying on the Python migration.
  - Renamed and renumbered all migration files sequentially (000 to 010) in `backend/migrations/` for clear execution order.
  - Added `000_create_warranties_table.sql` migration to ensure the base table exists before other migrations reference it.
  - Verified and ensured idempotency (`CREATE/ALTER ... IF NOT EXISTS`) for all migration scripts, preventing errors on re-runs.
  - Corrected `fix_permissions.py` execution by ensuring `fix_permissions.sql` is copied into the Docker image.

## [0.9.8.6] - 2025-04-01

### Added
  - Added tags to warranties, you can create and manage them
  - Choose different colours to tags
  - Search by tags
  - Added tags to the warranty cards
  - You can also edit current warranties to add tags

### Changed
  - Removed docker and docker compose from making data/uploads

### Current bugs with this release

  - Status page recently expired or expiring soon section will only work when a warranty is expiring.  
  - Currently tags are for all users, if an admin creates a tag, it will show up for the users as well. 


## [0.9.8.5] - 2025-03-29

### Changed
- **Settings Page Improvements**
  - Separated email settings into their own section with a dedicated save button
  - Added independent saving functionality for email preferences
  - Improved user experience by making email settings management more intuitive
  - Enhanced feedback when saving email preferences

## [0.9.8.4] - 2025-03-26


- Fixed database migration system issues
  - Resolved issue with missing user_preferences table causing notification preference errors
  - Enhanced migration system to support both SQL and Python-based migrations
  - Added idempotent execution of SQL migrations with existence checks
  - Created improved migration tracking to prevent duplicate migration attempts
  - Updated Docker configuration for proper migration script execution
  - Fixed missing columns by adding timezone and expiring_soon_days columns


## [0.9.8.3] - 2025-03-26

### Added

*   **Authentication:** Users are now automatically logged in after successful registration, removing an extra step in the onboarding process.
*   **Notifications:** Introduced email notifications for warranty expiration alerts.
*   **Notifications:** Added user preferences to customize notification frequency (daily, weekly, monthly), preferred delivery time, and timezone.
*   **Admin:** Added controls for administrators to manually trigger notifications, useful for testing.

### Changed

*   **Notifications:** Improved the reliability and processing efficiency of the backend notification system.
*   **UI:** Standardized the header's appearance and layout across all pages (home, status, settings) for a consistent look and feel.

### Fixed

*   **Charts:** Resolved an issue where the status page timeline chart initially displayed incomplete data, requiring a theme toggle to show all months correctly. The chart now loads with complete data.
*   **Preferences:** Corrected an issue where preference changes made by an admin could unintentionally affect regular users' settings. Preferences are now stored separately based on user type.
*   **Preferences:** Fixed synchronization issues ensuring that view preferences set in the settings page are consistently applied throughout the application.
*   **File Access:** Resolved authentication errors ("Authentication token is missing!") that occurred when attempting to open attached invoice or manual files. Secure file access now correctly uses authentication tokens.
*   **File Uploads:** Corrected a critical bug where uploading only one document type (e.g., just an invoice) could inadvertently delete the existing document of the other type (e.g., the manual). Both documents are now preserved correctly during updates.


## [0.9.8.2] - 2025-03-22

- **Edit Warranty Modal Improvements**
  - Added tabbed interface for the edit warranty modal with three sections:
  - Product Info: Product name, URL, and serial numbers
  - Warranty Details: Purchase date, warranty period, and price
  - Documents: Invoice and manual uploads
- Visual indicators for active tabs
- Improved dark mode support for the edit modal
- Better form organization and user experience


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
