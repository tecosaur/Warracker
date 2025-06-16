# Changelog

##  0.10.1.2 - 2025-06-16

### Fixed
- **First User Registration Issue on Fresh Instances:** Fixed critical bug preventing first user registration on newly deployed applications
  - **Logger Import Fix (`backend/auth_routes.py`):** Fixed undefined logger error in registration endpoint that was causing 500 Internal Server Error during user creation
  - **Database Migration Timing Fix (`backend/app.py`):** Enhanced owner existence check to handle cases where `is_owner` column doesn't exist yet during application startup, preventing column lookup errors during migration sequence
  - **Graceful Migration Handling:** Added proper column existence verification and exception handling for migration timing edge cases
  - **Error Resolution:** Eliminates "name 'logger' is not defined" and "column 'is_owner' does not exist" errors during fresh deployment registration

##  0.10.1.1 - 2025-06-15

### Added
- **Export Debug Tools**: Comprehensive debugging system for troubleshooting warranty export issues
  - **Debug Page**: Created `frontend/debug-export.html` for interactive export testing and analysis
  - **Debug API**: Added `/api/debug/export` endpoint providing detailed warranty and association data
  - **Enhanced Logging**: Added comprehensive debug logging to export and filter functions in `frontend/script.js`
  - **Export Validation**: Real-time display of filter application and warranty count verification
  - **Interactive Testing**: Browser-based tool to test export functionality with detailed console output
  - **Filter Analysis**: Step-by-step debugging of each filter application to identify export count discrepancies
- **Currency Position Control:** Enhanced currency display system to allow users to choose whether currency symbols appear on the left or right of numbers through the settings page.
  - **Settings UI Enhancement (`frontend/settings-new.html`):** Added new "Currency Position" dropdown in Display Preferences section:
    - **Left Position:** Traditional format like "$100.00" (default to maintain existing behavior)
    - **Right Position:** European-style format like "100.00$"
    - **Visual Examples:** Dropdown options show example formatting to clarify choice impact
  - **Database Schema (`backend/migrations/034_add_currency_position_column.sql`):** Added `currency_position` column to `user_preferences` table:
    - **Default Value:** Set to 'left' for backward compatibility with existing installations
    - **Data Validation:** Check constraint ensures only 'left' or 'right' values are allowed
    - **Migration Safety:** Handles existing data by setting NULL or invalid values to 'left' before applying constraint
  - **Backend API Integration (`backend/auth_routes.py`):** Enhanced user preferences endpoints to handle currency position:
    - **GET /api/auth/preferences:** Returns saved currency position preference with 'left' fallback for missing values
    - **PUT /api/auth/preferences:** Validates and saves currency position with input validation for 'left'/'right' values
    - **Default Handling:** All default preference objects include currency_position: 'left' for consistency
  - **Frontend Dynamic Formatting (`frontend/script.js`):** Implemented responsive currency display system:
    - **New Functions:** Added `getCurrencyPosition()` and `formatCurrencyHTML()` for position-aware currency formatting
    - **Smart HTML Generation:** Currency symbols and amounts dynamically positioned based on user preference
    - **CSS Integration:** Right-positioned symbols use `.currency-right` class for proper spacing
    - **Live Updates:** Real-time updates when position preference changes without page refresh
  - **Universal Application:** Currency position setting applies across all views and features:
    - **Warranty Cards:** Grid, list, and table views all respect position preference
    - **Price Displays:** Purchase price fields show currency in chosen position throughout application
    - **Cross-Tab Sync:** Settings changes immediately reflect in all open browser tabs
  - **User Experience Features:**
    - **Immediate Preview:** Position changes apply instantly to warranty cards when settings are saved
    - **Persistent Preference:** Setting saved per user in database and persists across sessions
    - **Backward Compatible:** Existing users see no change (defaults to left position)
    - **Storage Event Handling:** Settings page and main app stay synchronized when currency position changes
  - **CSS Styling (`frontend/style.css`):** Added `.currency-right` class for proper margin spacing when symbols appear on the right
  - **Form Currency Integration:** Enhanced warranty add/edit forms to respect currency position settings:
    - **Dynamic Form Updates:** Price input fields in both add and edit warranty forms now show currency symbols in the user's preferred position
    - **CSS Form Positioning:** Added `.price-input-wrapper.currency-right` styles to properly position currency symbols on the right side of input fields
    - **Input Padding Adjustment:** Right-positioned currency symbols get appropriate padding to prevent text overlap
    - **Dynamic Currency Positioning:** JavaScript-based dynamic positioning system that places right-side currency symbols immediately after the typed content, maintaining natural spacing regardless of input length
    - **Modal Currency Positioning:** Enhanced currency positioning to work immediately when modals open, not just when users interact with input fields
    - **Modal Integration:** Currency position updates automatically when forms are opened, ensuring immediate visual consistency
    - **Summary Tab Enhancement:** Add warranty form summary tab now displays purchase price with correct currency positioning
    - **Improved Dynamic Positioning:** Enhanced JavaScript positioning system with better timing and reliability:
      - **Element Readiness Validation:** Added checks to ensure DOM elements are fully rendered before positioning calculations
      - **Multiple Timing Mechanisms:** Uses `requestAnimationFrame()` with fallback timers for robust positioning across different browsers
      - **Automatic Modal Triggers:** Currency positioning now activates immediately when modals open via simulated focus/blur events
      - **Debug Logging:** Added console logging for positioning calculations to aid in troubleshooting
      - **Retry Logic:** Automatic retry mechanism if elements aren't ready during initial positioning attempt
  - _Files: `backend/migrations/034_add_currency_position_column.sql`, `backend/auth_routes.py`, `frontend/settings-new.html`, `frontend/settings-new.js`, `frontend/script.js`, `frontend/style.css`, `frontend/index.html`_
- **OIDC-Only Login Mode:** Added administrator control to enforce OIDC-only authentication, hiding traditional username/password login forms.
  - **Database Setting:** Added `oidc_only_mode` boolean setting to `site_settings` table with default value 'false' for backward compatibility
  - **Backend API Enhancement (`backend/app.py`):** 
    - **Settings Management:** Added `oidc_only_mode` to site settings GET/PUT endpoints with proper boolean validation
    - **OIDC Status API:** Enhanced `/api/settings/oidc-status` endpoint to include `oidc_only_mode` status for frontend consumption
  - **OIDC Handler Update (`backend/oidc_handler.py`):** Updated `/api/auth/oidc-status` route to return OIDC-only mode status alongside provider information
  - **Frontend Admin Controls (`frontend/settings-new.html`, `frontend/settings-new.js`):**
    - **Settings UI:** Added "OIDC-Only Login Mode" toggle in OIDC SSO Configuration section with warning about proper configuration
    - **Settings Persistence:** OIDC-only mode preference saved to backend and loaded with other OIDC settings
    - **Element Management:** Added DOM element handling for the new toggle in both global and local scopes
  - **Login Page Enhancement (`frontend/login.html`):**
    - **Conditional UI:** Traditional username/password login form hidden when OIDC-only mode is enabled
    - **Link Management:** Register and forgot password links hidden in OIDC-only mode as they're not applicable
    - **Page Title Update:** Login page title changes to "Login with SSO" when in OIDC-only mode
    - **Clean Interface:** OR separator and auth links section hidden when not needed
  - **Security Benefits:** Enforces single sign-on authentication when enabled, preventing local account access and centralizing authentication through OIDC provider
  - **Administrator Safety:** Includes warning message about ensuring OIDC is properly configured before enabling this mode to prevent lockouts
  - _Files: `backend/app.py`, `backend/oidc_handler.py`, `frontend/settings-new.html`, `frontend/settings-new.js`, `frontend/login.html`_
- **About Page Redesign:** Complete visual overhaul of the about page with modern design, improved layout, and enhanced community links.
  - **Hero Section Enhancement:** Added gradient background hero section with prominent Warracker branding, version display, and descriptive text about the platform
  - **Modern Card Layout:** Restructured content into three themed information cards:
    - **Project Information Card:** GitHub repository and releases links with proper GitHub branding
    - **Community & Support Card:** Discord community invitation and issue reporting links
    - **Developer Information Card:** Developer profile and license information with appropriate icons
  - **Discord Community Integration:** Added prominent Discord community link (https://discord.gg/PGxVS3U2Nw) with official Discord branding:
    - **Discord Icon:** Proper `fab fa-discord` Font Awesome icon implementation
    - **Brand Colors:** Discord's signature #5865f2 color scheme with hover effects
    - **Community Focus:** Positioned prominently in Community & Support section
  - **Enhanced Social Links:** Improved all external links with proper icons and brand-appropriate styling:
    - **GitHub Links:** `fab fa-github` icons for repository and developer profile
    - **Issue Reporting:** `fas fa-bug` icon with red accent color for bug reports
    - **Releases:** `fas fa-tags` icon with blue accent color for version releases
    - **License:** `fas fa-balance-scale` icon with green accent color for AGPL-3.0 license
  - **Visual Improvements:** Modern design elements with enhanced user experience:
    - **Hover Effects:** Smooth card lift animations and social link transitions
    - **Responsive Design:** Grid layout that adapts to mobile devices with single-column layout
    - **Dark Mode Support:** Proper styling for both light and dark themes with appropriate contrast
    - **Color-Coded Interface:** Each social link uses brand-appropriate colors for visual consistency
  - **Update Status Enhancement:** Redesigned update checker section with better visual hierarchy and icon integration
  - **Support Section:** Improved "Buy me a coffee" section with better visual presentation and clear call-to-action
  - **Mobile Optimization:** Responsive design with adjusted font sizes, centered layouts, and flexible social link sizing for optimal mobile experience
  - _Files: `frontend/about.html`_
- **Global View Photo Access:** Enhanced secure file access to allow users to view product photos from other users' warranties when global view is enabled.
  - **Photo Sharing in Global View:** When global view is enabled for all users, product photo thumbnails and full-size images are now accessible across all warranties, not just user-owned ones
  - **Selective File Access:** Only product photos are granted global view access - invoices, manuals, and other sensitive documents remain restricted to warranty owners and admins
  - **Respects Global View Settings:** Photo access follows the same permission model as the global warranties feature:
    - **Global View Enabled:** Photos accessible to all authenticated users when global view is active
    - **Admin-Only Mode:** When global view is restricted to admins only, photo access is similarly restricted
    - **Disabled Mode:** When global view is disabled, photos revert to owner-only access
  - **Enhanced Security Logging:** Added comprehensive logging to secure file access endpoint for troubleshooting and security auditing of photo access requests
  - **Backend Implementation (`backend/app.py`):** Modified `/api/secure-file/<path:filename>` endpoint with additional authorization logic:
    - **Product Photo Detection:** Queries database to identify if requested file is a product photo vs other document types
    - **Permission Validation:** Checks global view settings and user permissions before granting access
    - **Maintains Existing Security:** All current access controls remain intact - admins and owners retain full access
  - **User Experience:** Product photos now display properly in global view across all viewing modes (grid, list, table), enabling visual identification of products from all users
  - _Files: `backend/app.py`_
- **Super-Admin (Owner) Role with Ownership Transfer:** Implemented a comprehensive ownership management system with immutable owner role and secure ownership transfer functionality.
  - **Database Schema Enhancement (`backend/migrations/031_add_owner_role.sql`):** Added `is_owner` boolean column to users table with automatic owner promotion for the first registered user
  - **Backend API Protection (`backend/app.py`, `backend/auth_routes.py`, `backend/auth_utils.py`):** 
    - **Owner Protection Logic:** Prevents owner account deletion, demotion, or deactivation through all admin endpoints
    - **Authentication Enhancement:** Added `is_owner` field to all authentication responses and token validation
    - **Backward Compatibility:** Implemented graceful fallback handling for systems without the owner column
    - **Transaction Rollback Handling:** Added proper PostgreSQL transaction rollback recovery for failed queries
  - **Ownership Transfer API (`backend/app.py`):** New `/api/admin/transfer-ownership` endpoint with atomic transaction processing:
    - **Security Validation:** Requires "TRANSFER" confirmation text and validates target user is an active admin
    - **Atomic Operations:** Uses database transactions to ensure ownership transfer completes fully or rolls back entirely
    - **Owner-Only Access:** Restricted to current owner with comprehensive permission checks
  - **Frontend UI Implementation (`frontend/settings-new.html`, `frontend/settings-new.js`):**
    - **Dedicated Ownership Section:** Separate "👑 Ownership Management" section in admin settings with crown icon branding
    - **Visual Owner Indicators:** Crown icons (👑) displayed next to owner username in user management lists
    - **Protected UI Elements:** Owner edit/delete buttons disabled with visual indicators and tooltips
    - **Transfer Confirmation Modal:** Secure ownership transfer interface requiring "TRANSFER" text confirmation
    - **Modern User Management:** Redesigned users list with professional styling, hover effects, and responsive design
    - **Action Button Enhancement:** Improved edit/delete buttons with smooth animations and theme compatibility
  - **Migration Safety:** Automatic owner assignment to first user during migration with comprehensive error handling
  - **Security Features:** Owner cannot be deleted, demoted, or have ownership transferred without explicit confirmation
  - _Files: `backend/migrations/031_add_owner_role.sql`, `backend/app.py`, `backend/auth_routes.py`, `backend/auth_utils.py`, `frontend/settings-new.html`, `frontend/settings-new.js`_

- **Product Age Tracking and Sorting:** Enhanced warranty cards with product age display and sorting capabilities to help users track ownership duration.
  - **Age Calculation (`frontend/script.js`):** Added `calculateProductAge()` function that computes time elapsed since purchase date with intelligent formatting:
    - **Smart Display Format:** Shows age as "2 years, 3 months", "6 months", or "15 days" depending on duration
    - **Edge Case Handling:** Gracefully handles invalid dates, future dates, and same-day purchases ("Today")
    - **Precision Logic:** Shows days only for items less than a year old to avoid clutter
  - **Visual Integration:** Product age now appears on all warranty cards across all view types:
    - **Grid View:** Age displayed between purchase date and warranty duration for logical flow
    - **List View:** Consistent placement maintaining card layout harmony
    - **Table View:** Compact age display optimized for dense information presentation
  - **Age-Based Sorting:** Added "Age" option to Sort By dropdown with dedicated sorting logic:
    - **Oldest First:** Products sorted with longest-owned items appearing first
    - **Precise Sorting:** Uses `calculateProductAgeInDays()` helper function for accurate day-level sorting
    - **Invalid Date Handling:** Items with missing purchase dates treated as newest (0 days old)
  - **User Benefits:** Enables users to track ownership duration, assess product lifecycle, and organize warranties by how long they've owned each item
  - _Files: `frontend/index.html`, `frontend/script.js`_

  - **Persistent View Scope (Global/Personal) with Auto-Loading:** The app now remembers the user's last selected view scope (global or personal) and automatically loads the correct data from the appropriate API endpoint on page load, not just updating the UI.
  - **Seamless Experience:** Users no longer need to re-select their preferred view after a refresh; the correct data and UI are loaded immediately based on their last choice.
  - **Consistent State:** Both the main warranties page and the status dashboard respect the saved preference and fetch from the correct endpoint (`/api/warranties/global` or `/api/warranties`, and `/api/statistics/global` or `/api/statistics`).
  - **User-Specific Storage:** Preferences are stored per user/admin using the same prefix system as other settings.
  - **Robustness:** The system defaults to personal view if no preference is found or on error, and always keeps the UI and data in sync.
  - _Files: `frontend/script.js`, `frontend/status.js`_

- **Authentication System Refactoring to Flask Blueprints:** Complete restructuring of authentication routes for improved code organization and maintainability.
  - **Flask Blueprint Architecture:** Migrated all authentication routes from the monolithic `app.py` file to a dedicated Flask Blueprint (`auth_routes.py`)
  - **Modular Code Organization:** Separated authentication logic into specialized modules:
    - **`auth_utils.py`:** Authentication helper functions (`generate_token`, `decode_token`, `token_required`, `admin_required`, `is_valid_email`, `is_valid_password`)
    - **`auth_routes.py`:** Authentication Blueprint containing all auth-related routes and handlers
  - **Routes Migrated:** All authentication endpoints moved to Blueprint architecture:
    - User registration and login (`/register`, `/login`, `/logout`)
    - Token validation and user management (`/validate-token`, `/user`)
    - Password management (`/password/reset-request`, `/password/reset`, `/password/change`)
    - Profile and account management (`/profile`, `/account`, `/preferences`)
    - Email management (`/change-email`, `/verify-email-change`)
    - System status endpoints (`/registration-status`)
  - **Backward Compatibility:** All API endpoints maintain identical URLs and functionality - zero breaking changes for existing clients
  - **Import Optimization:** Reduced main application file size and improved code maintainability through separation of concerns
  - **Docker Integration:** Updated Dockerfile to properly include new authentication modules in container builds
  - _Files: `backend/auth_utils.py`, `backend/auth_routes.py`, `backend/app.py`, `Dockerfile`_

- **Smart Currency Default Selection:** Enhanced add warranty form to automatically default to user's preferred currency from settings instead of always defaulting to USD.
  - **Settings Integration:** Currency dropdown in add warranty modal now reads user's preferred currency from settings and auto-selects it as the default
  - **Currency Code Storage:** Settings page now saves both currency symbol and currency code to localStorage for accurate currency identification
  - **Intelligent Fallback:** System attempts to derive currency code from symbol if not explicitly saved, with USD as ultimate fallback
  - **Form Reset Handling:** Add warranty modal properly restores user's preferred currency after form reset operations
  - **Individual Override:** Users can still change currency for individual warranties while maintaining their preferred default
  - **Seamless Experience:** Eliminates need to manually change currency from USD to preferred currency for every new warranty
  - **Debug Logging:** Added comprehensive logging to track currency code detection and default selection process
  - _Files: `frontend/script.js`, `frontend/settings-new.js`_

### Enhanced
- **Larger Product Photo Thumbnails:** Increased photo thumbnail sizes across all view modes for better product visibility and identification.
  - **Grid View Enhancement:** Photo thumbnails increased from 60px × 60px to 80px × 80px for more prominent product images
  - **List View Enhancement:** Photo thumbnails increased from 50px × 50px to 70px × 70px for improved visual clarity
  - **Table View Enhancement:** Photo thumbnails increased from 40px × 40px to 55px × 55px for better readability in compact view
  - **Mobile Responsive Updates:** Adjusted mobile photo sizes to maintain usability while providing larger images on smaller screens
  - **Consistent Styling:** Maintained existing hover effects, border radius, and visual styling while increasing overall size
  - **Better User Experience:** Larger photos make it easier to identify products at a glance across all viewing modes
  - _Files: `frontend/style.css`, `frontend/script.js`_

### Fixed
- **CSV Import Currency Selection:** Fixed CSV import functionality that was incorrectly defaulting all imported warranties to USD currency instead of using the user's preferred currency from settings.
  - **Root Cause:** CSV import function in `backend/app.py` was hardcoding `'USD'` for all imported warranties regardless of user preferences
  - **Solution:** Enhanced import function to query user's preferred currency symbol from `user_preferences` table and convert it to appropriate currency code
  - **Currency Mapping:** Implemented comprehensive symbol-to-code mapping for 30+ currencies (€→EUR, £→GBP, ¥→JPY, etc.) matching frontend logic
  - **Intelligent Fallback:** Graceful fallback to USD for users without currency preferences or with unknown custom symbols
  - **Enhanced Logging:** Added detailed logging to track currency preference detection and assignment during import process
  - **Result:** Imported warranties now automatically use user's preferred currency (Euro, Pound, Yen, etc.) instead of always defaulting to USD
  - _Files: `backend/app.py`_

- **Export Function Debugging and Verification:** Resolved user reports of incomplete warranty exports by implementing comprehensive debugging tools and verifying export functionality
  - **Root Cause Analysis:** Determined that export function was working correctly - all warranties were being exported as expected
  - **Debug Implementation:** Added detailed console logging to export process showing step-by-step filter application and final export counts
  - **Verification Tools:** Created interactive debug page (`frontend/debug-export.html`) and backend debug API (`/api/debug/export`) for troubleshooting
  - **User Education:** Identified that perceived "missing" records were due to CSV viewer display issues with similar/duplicate entries rather than export functionality problems
  - **Export Validation:** Confirmed all warranties are properly included in CSV output with correct data formatting and structure
  - **Documentation:** Enhanced export process with real-time feedback showing actual number of warranties exported

- **Critical User Preferences Persistence Bug:** Fixed date format and currency symbol settings not saving properly, causing user preferences to revert to defaults after page refresh.
  - **Root Cause:** Backend API endpoints (`GET`/`PUT` `/api/auth/preferences`) were hardcoded to always return `currency_symbol: '$'` and `date_format: 'MDY'` instead of reading from/writing to the database columns
  - **Database Verification:** Confirmed both `currency_symbol` and `date_format` columns exist in `user_preferences` table via migrations `006_add_currency_symbol_column.py` and `019_add_date_format_column.sql`
  - **Backend API Fixes (`backend/auth_routes.py`):**
    - **GET Route:** Added `currency_symbol, date_format` to SELECT queries and updated response mapping to use actual database values
    - **PUT Route:** Added validation and processing for `currency_symbol` and `date_format` from request data
    - **UPDATE Query:** Enhanced to include currency symbol and date format in SET clauses
    - **INSERT Query:** Updated to save currency symbol and date format for new user preferences
    - **Response Consistency:** All preference responses now return actual saved values instead of hardcoded defaults
  - **Validation Added:** Currency symbol limited to 8 characters, date format restricted to valid options (`MDY`, `DMY`, `YMD`, `MDY_WORDS`, `DMY_WORDS`, `YMD_WORDS`)
  - **Result:** Settings page now properly persists currency symbol (€, £, ¥, etc.) and date format preferences across page refreshes and sessions
  - _Files: `backend/auth_routes.py`_

- **Critical OIDC Login RecursionError Fix:** Resolved fatal `RecursionError: maximum recursion depth exceeded` preventing OIDC authentication with self-hosted providers like Authentik.
  - **Root Cause:** Gunicorn's `gevent` worker type needs to monkey-patch standard libraries (like `ssl`) before they're imported, but `preload_app = True` was loading Flask dependencies before patching occurred
  - **Solution:** Enhanced `gunicorn_config.py` with conditional early monkey patching that occurs at the very beginning of the configuration file, before any other imports
  - **Intelligent Patching:** Monkey patching now only applies to memory modes that use gevent workers (`optimized` and `performance`), while `ultra-light` mode with sync workers skips patching entirely
  - **Safety:** Uses try/catch block to gracefully handle environments without gevent installed, ensuring no impact on sync workers or development environments
  - **Result:** OIDC providers now work correctly with gevent workers, eliminating SSL recursion errors and enabling SSO functionality across all deployment modes
  - **Verification:** MonkeyPatchWarning no longer appears in startup logs, replaced with "✅ Early gevent monkey patch applied for SSL compatibility" confirmation
  - _Files: `backend/gunicorn_config.py`_

- **Critical OIDC HTTPS Callback URL Fix:** Resolved OIDC login failures when Warracker is accessed over HTTPS, where the application was generating incorrect `http://` callback URLs instead of `https://` URLs.
  - **Root Cause:** Flask application running behind Nginx reverse proxy was not aware of the original HTTPS protocol, causing `url_for(_external=True)` to generate HTTP callback URLs that didn't match the OIDC provider's expected HTTPS URLs
  - **Reverse Proxy Configuration:** While Nginx correctly sent `X-Forwarded-Proto: https` headers, Gunicorn and Flask were not configured to trust and use these forwarded headers
  - **Gunicorn Fix (`backend/gunicorn_config.py`):** Added `forwarded_allow_ips = '*'` configuration to trust proxy headers from the containerized Nginx reverse proxy
  - **Flask Middleware (`backend/app.py`):** Implemented `ProxyFix` middleware with `x_for=1, x_proto=1, x_host=1, x_prefix=1` to read forwarded headers and update Flask's request context
  - **Header Processing:** Flask now correctly interprets `X-Forwarded-Proto` headers and generates HTTPS URLs when accessed through the reverse proxy
  - **Result:** OIDC login flow now generates correct `https://warracker.domain.com/api/oidc/callback` URLs, eliminating provider callback mismatches and enabling successful SSO authentication over HTTPS
  - **Standard Practice:** Implements industry-standard reverse proxy configuration for Flask applications behind SSL-terminating proxies
  - _Files: `backend/gunicorn_config.py`, `backend/app.py`_

- **Global vs. Individual Apprise Notification Mode:** Implemented flexible Apprise notification system allowing administrators to choose between consolidated global notifications or personalized individual notifications.
  - **Database Migration (`backend/migrations/032_add_apprise_notification_mode.sql`):** Added `apprise_notification_mode` setting to `site_settings` table with default value 'global' for backward compatibility
  - **Backend Notification Logic (`backend/notifications.py`):** Enhanced `send_expiration_notifications` function with mode-aware branching logic:
    - **Global Mode:** Sends single consolidated notification summarizing all expiring warranties across all users to configured Apprise channels
    - **Individual Mode:** Sends separate personalized notifications for each user with expiring warranties, grouped by user with targeted messaging
    - **Smart User Filtering:** Respects user notification preferences and timing eligibility for both manual and scheduled notifications
    - **Mode Detection:** Dynamically reads `apprise_notification_mode` setting from database using imported `get_site_setting` function
  - **Apprise Handler Enhancement (`backend/apprise_handler.py`):** Added two new specialized notification methods:
    - **`send_global_expiration_notification()`:** Creates summary notification with warranties grouped by user email for administrator overview
    - **`send_individual_expiration_notification()`:** Generates personalized notifications with user-specific greeting and warranty details
    - **Error Handling:** Comprehensive exception handling and logging for both notification modes
  - **Frontend Admin Controls (`frontend/settings-new.html`, `frontend/settings-new.js`):** 
    - **Notification Mode Dropdown:** Added selection between "Global Summary" and "Per User" modes in Apprise settings section
    - **Dynamic Description:** Real-time description updates explaining current mode behavior and implications
    - **Settings Integration:** Mode preference saved to backend and persisted across sessions with proper loading and validation
    - **Event Handling:** Immediate UI feedback when switching between notification modes
  - **Backward Compatibility:** Existing installations default to 'global' mode, maintaining current notification behavior without disruption
  - **Future Enhancement Ready:** Individual mode framework prepared for future per-user Apprise channel configuration
  - _Files: `backend/migrations/032_add_apprise_notification_mode.sql`, `backend/notifications.py`, `backend/apprise_handler.py`, `frontend/settings-new.html`, `frontend/settings-new.js`_

  - **Apprise Warranty Scope Control:** Added administrator control to choose which warranties are included in Apprise notifications, enabling both multi-user and personal notification scenarios.
  - **Database Migration (`backend/migrations/033_add_apprise_warranty_scope.sql`):** Added `apprise_warranty_scope` setting to `site_settings` table with default value 'all' to maintain current behavior
  - **Backend Warranty Filtering (`backend/notifications.py`):** Implemented warranty scope filtering logic in notification processing:
    - **All Users Scope (Default):** Includes expiring warranties from all users in the system (current behavior)
    - **Admin Only Scope:** Filters to only include warranties belonging to the admin/owner user for personal notifications
    - **Smart Admin Detection:** Automatically identifies the primary admin by first checking for owner user, then falling back to first admin user
    - **Scope Logging:** Comprehensive logging shows original vs filtered warranty counts for transparency and debugging
  - **Frontend Warranty Scope Controls (`frontend/settings-new.html`, `frontend/settings-new.js`):**
    - **Warranty Scope Dropdown:** Added selection between "All Users' Warranties" and "Admin's Warranties Only" in Apprise settings
    - **Scope Description:** Real-time description updates explaining which warranties will be included in notifications
    - **Settings Persistence:** Warranty scope preference saved to backend and properly loaded with other Apprise settings
    - **Event Handling:** Immediate UI feedback when changing warranty scope selection
  - **Flexible Combinations:** Works seamlessly with notification modes for complete control:
    - **Global + All:** Single notification with all users' warranties (original behavior)
    - **Global + Admin:** Single notification with only admin's warranties
    - **Individual + All:** Separate notifications sent to each user with their warranties
    - **Individual + Admin:** Notification sent only to admin with their warranties
  - **Error Handling:** Graceful fallback to 'all' scope if admin user cannot be determined, with appropriate logging
  - _Files: `backend/migrations/033_add_apprise_warranty_scope.sql`, `backend/notifications.py`, `frontend/settings-new.html`, `frontend/settings-new.js`_

- **Enhanced Notification Settings with Apprise Integration:** Comprehensive enhancement of user notification preferences to support both email and Apprise notifications with individual timing control.
  - **Backend User Preferences Enhancement (`backend/auth_routes.py`):** Fixed and expanded user preferences API to properly handle all notification fields:
    - **Notification Channel Support:** Added proper handling for `notification_channel` field allowing users to choose between 'none', 'email', 'apprise', or 'both'
    - **Apprise Timing Fields:** Added support for `apprise_notification_time`, `apprise_notification_frequency`, and `apprise_timezone` in user preferences
    - **Database Persistence:** Fixed critical bug where notification channel and Apprise settings were hardcoded instead of being saved to/loaded from database
    - **Validation:** Added proper validation for notification channel values and timing fields
    - **API Consistency:** Both GET and PUT `/api/auth/preferences` endpoints now properly handle all notification-related fields
  - **Frontend Notification Settings Redesign (`frontend/settings-new.html`, `frontend/settings-new.js`):**
    - **Dual Notification Sections:** Separated user notification preferences from admin Apprise configuration for clarity
    - **Dynamic Settings Display:** Notification settings section shows/hides email and Apprise fields based on selected notification channel
    - **Individual Timing Control:** Users can set separate notification times and timezones for email vs Apprise notifications
    - **Smart Field Management:** Apprise-specific fields (time, timezone, frequency) appear only when notification channel includes 'apprise' or 'both'
    - **Timezone Loading:** Proper timezone dropdown population for both email and Apprise notification settings
    - **Settings Persistence:** All notification preferences properly save to user preferences and persist across sessions
  - **Scheduler Integration:** Enhanced notification scheduler to respect individual user notification channel preferences:
    - **Channel-Aware Processing:** Scheduler checks each user's `notification_channel` setting to determine which notification types to send
    - **Separate Timing:** Users can receive email notifications at one time and Apprise notifications at a different time
    - **Preference Validation:** Only users with appropriate notification channels enabled receive corresponding notification types
  - **User Experience Improvements:**
    - **Clear Separation:** Admin Apprise configuration (URLs, global settings) separated from user notification preferences (timing, channels)
    - **Intuitive Interface:** Notification channel dropdown with immediate visual feedback showing relevant settings
    - **Flexible Scheduling:** Users can choose to receive only emails, only Apprise notifications, or both at different times
  - _Files: `backend/auth_routes.py`, `frontend/settings-new.html`, `frontend/settings-new.js`_

- **Apprise Notification Message Format Standardization:** Unified notification message format between scheduled and manual Apprise notifications for consistency.
  - **Message Format Alignment (`backend/apprise_handler.py`):** Updated scheduled notification functions to match manual test notification format:
    - **Consistent Titles:** All notifications now use format `"[Warracker] Warranties Expiring in X Days"` instead of generic summary titles
    - **Urgency Indicators:** Added emoji prefixes based on expiration timeframe:
      - 🚨 URGENT: for warranties expiring in 1 day
      - ⚠️ IMPORTANT: for warranties expiring in ≤7 days  
      - 📅 REMINDER: for warranties expiring in >7 days
    - **Grouped by Days:** Separate notifications sent for different expiration timeframes (7, 30, 365 days) instead of combined summary
    - **Standardized Content:** Consistent bullet-point format, date formatting, and footer text across all notification types
  - **Enhanced Notification Functions:**
    - **`send_global_expiration_notification()`:** Now groups warranties by expiration days and sends separate notifications for each timeframe
    - **`send_individual_expiration_notification()`:** Similarly updated to match manual test format with proper grouping
    - **`_send_global_expiration_batch()` and `_send_individual_expiration_batch()`:** New helper functions that use identical formatting to manual test notifications
  - **User Benefits:** 
    - **Consistent Experience:** Manual test notifications and scheduled notifications now look identical
    - **Clear Urgency:** Emoji indicators immediately convey urgency level
    - **Better Organization:** Separate notifications for different timeframes instead of overwhelming combined messages
  - _Files: `backend/apprise_handler.py`_

- **Apprise Settings UI Cleanup:** Streamlined Apprise configuration interface by removing non-functional decorative fields.
  - **Removed Decorative Fields (`frontend/settings-new.html`, `frontend/settings-new.js`):** Eliminated unused time and timezone fields from admin Apprise configuration:
    - **Notification Time Field:** Removed time input that was not used by the notification scheduler
    - **Timezone Dropdown:** Removed timezone selection that was not used by the notification scheduler  
    - **Notification Frequency:** Renamed to "Check Frequency" with clearer description as a global system setting
  - **JavaScript Cleanup:** Removed all references to unused fields including variable definitions, event listeners, and data loading functions
  - **Status Display Cleanup:** Removed "Notification Time" from current status display since it's no longer relevant
  - **Cache-Busting:** Updated version parameters from `v=20250529005` to `v=20250529006` to force browser cache refresh
  - **Functional Clarity:** Apprise card now only contains settings that actually affect system behavior:
    - ✅ Enable/Disable toggle, Notification Mode, Warranty Scope, Notification URLs, Notification Days, Check Frequency, Message Title Prefix
    - ❌ Removed: Notification Time, Timezone (these are now properly handled in user notification preferences)
  - **User Experience:** Clear separation between admin system configuration and user personal notification timing preferences
  - _Files: `frontend/settings-new.html`, `frontend/settings-new.js`_

### Code Quality & Maintenance
- **Legacy OIDC Code Cleanup:** Removed ~290 lines of commented-out and orphaned OIDC code from main application file for improved maintainability.
  - **Removed Components:**
    - **Commented Route Definitions:** Eliminated ~150 lines of commented-out `/api/oidc/login` and `/api/oidc/callback` route definitions
    - **Orphaned Callback Logic:** Removed ~140 lines of disconnected OIDC callback handling code including user provisioning, token handling, and error redirection logic
    - **Dead Code Elimination:** Cleaned up legacy authentication code that was replaced by the Blueprint architecture
  - **OIDC Functionality Preserved:** All OIDC functionality remains fully operational through the proper Blueprint architecture in `backend/oidc_handler.py`
  - **File Size Reduction:** Reduced `backend/app.py` from ~3,477 lines to ~3,200 lines (~8% reduction)
  - **Code Organization:** Improved code readability and maintainability by removing confusing commented-out legacy implementations
  - **Blueprint Verification:** Confirmed `oidc_bp` Blueprint is properly registered and functional at `/api/oidc/*` endpoints
  - _Files: `backend/app.py`_



##  0.10.1.0 - 2025-06-10

### Added
- **Public Global Warranty View for All Users**
  - Extended global warranty view access to all authenticated users (previously admin-only)
  - **Regular Users**: Can view all warranties from all users but can only edit/delete their own
  - **Admin Users**: Can edit/delete any warranty in global view, maintaining full administrative control
  - Added read-only protection: edit/delete buttons are replaced with view-only eye icon for warranties not owned by current user (unless user is admin)
  - Updated UI labels and tooltips to reflect the new public access model
  - Maintains full admin functionality while providing transparency to all users

- **Admin Global View Control Settings**
  - Added admin setting to enable/disable the global view feature site-wide
  - New "Global View Enabled" toggle in Site Settings section of admin panel
  - New "Global View Admin Only" toggle to restrict global view access to administrators only
  - When disabled, global view switcher is hidden from all users (including non-admins)
  - When admin-only is enabled, only administrators can access global view feature
  - Real-time enforcement: users automatically redirected to personal view if global view is disabled or restricted while they're using it
  - Default enabled for backward compatibility with admin-only setting defaulted to false

- **Global View for Status Dashboard**
  - Extended global view functionality to the warranty status/analytics page
  - Eligible users can now view warranty statistics and data from all users on the status dashboard
  - Added view switcher (Personal/Global) to status page header with same permission controls as main page
  - Global statistics include total counts, charts, and warranty tables from all users
  - Owner information displayed in warranty tables when in global view mode
  - Maintains same security model: admins can see all data, regular users see all data but with read-only access to others' warranties
  - Seamless integration with existing global view settings and permissions
- **Apprise Push Notifications Integration:** Comprehensive push notification system supporting 80+ services for warranty expiration alerts.
  - **Backend Implementation:**
    - **Apprise Handler (`backend/apprise_handler.py`):** Complete notification management system with configuration loading, URL validation, and multi-service support.
    - **Database Migration (`backend/migrations/026_add_apprise_settings.sql`):** Added Apprise configuration settings to site_settings table.
    - **API Endpoints (`backend/app.py`):** Full REST API for Apprise management including test notifications, URL validation, configuration reload, and manual triggers.
    - **Scheduler Integration:** Enhanced existing notification scheduler to send both email and Apprise notifications simultaneously.
    - **Environment Support:** Full environment variable support for Docker deployments with fallback to database configuration.
  - **Frontend Implementation:**
    - **Admin Settings UI (`frontend/settings-new.html`):** Complete Apprise configuration section with real-time status, URL management, and testing capabilities.
    - **JavaScript Integration (`frontend/settings-new.js`):** Full frontend functionality for configuration management, URL validation, and notification testing.
    - **Responsive Design (`frontend/settings-styles.css`):** Modern UI components including status badges, action grids, and mobile-responsive layouts.
  - **Supported Services:** Discord, Slack, Telegram, Email (Gmail, Outlook), Microsoft Teams, Webhooks, Matrix, Pushover, Ntfy, Gotify, and 70+ more services.
  - **Configuration Options:**
    - **Multiple Notification URLs:** Support for comma-separated or line-separated notification service URLs
    - **Flexible Timing:** Configurable notification days (e.g., 7,30 days before expiration) and daily notification time
    - **Custom Branding:** Configurable title prefix for all notifications (e.g., "[Warracker]")
    - **Test Functionality:** Send test notifications to verify configuration before enabling
    - **URL Validation:** Real-time validation of Apprise notification URLs
  - **Environment Configuration (`env.example`):** Complete example configuration file with detailed Apprise setup instructions and URL format examples.
  - **Graceful Degradation:** System continues to function normally if Apprise is not installed, with appropriate admin notifications.
  - _Files: `backend/apprise_handler.py`, `backend/migrations/026_add_apprise_settings.sql`, `backend/app.py`, `backend/db_handler.py`, `backend/requirements.txt`, `frontend/settings-new.html`, `frontend/settings-new.js`, `frontend/settings-styles.css`, `docker-compose.yml`, `env.example`_
- **Warranty Type Filtering and Sorting:** Enhanced the home page with comprehensive warranty type filtering and sorting capabilities.
  - **New Warranty Type Filter Dropdown:** Added a dedicated "Warranty Type" filter dropdown in the filter section, positioned between Vendor and Sort By filters.
  - **Dynamic Filter Population:** The warranty type filter automatically populates with all unique warranty types found in existing warranties, sorted alphabetically.
  - **Case-Insensitive Filtering:** Warranty type filtering works regardless of the case of the warranty type (e.g., "Standard", "standard", "STANDARD").
  - **Sorting by Warranty Type:** Added "Warranty Type" as a sorting option in the Sort By dropdown, allowing users to sort warranties alphabetically by their warranty type.
  - **Real-time Filtering:** Filter applies immediately when warranty type selection changes, working seamlessly with existing filters (Status, Tag, Vendor, Search).
  - **Frontend Implementation:**
    - Updated `frontend/index.html` to include warranty type filter dropdown and sort option
    - Enhanced `frontend/script.js` with warranty type filtering logic, event listeners, and population function
    - Added `populateWarrantyTypeFilter()` function to dynamically populate filter options from warranty data
    - Integrated warranty type support into `currentFilters` object and `applyFilters()` function
    - Added warranty type sorting logic to `renderWarranties()` function
  - **Integration:** Works with the existing warranty type field that was previously added to add/edit forms, providing end-to-end warranty type management.
  - _Files: `frontend/index.html`, `frontend/script.js`_

- **Admin Global Warranty View:** Added a globe button for administrators to view all users' warranties alongside their own.
  - **Backend API (`backend/app.py`):** New `/api/admin/warranties` endpoint that returns all warranties from all users with user information (username, email, display name).
  - **Frontend UI (`frontend/index.html`):** Added admin-only "Scope" toggle with Personal/Global view buttons next to the existing view switcher.
  - **Frontend Logic (`frontend/script.js`):** 
    - Added `isGlobalView` state management and view switching functions
    - Enhanced warranty rendering to show owner information when in global view
    - Automatic admin detection and UI initialization
    - Dynamic title updates ("Your Warranties" vs "All Users' Warranties")
  - **Styling (`frontend/style.css`):** 
    - Admin view switcher styling with primary color theme
    - Owner information highlighting with colored border and background
    - Responsive design for mobile devices
  - **Security:** Admin-only access with proper permission checks and graceful fallbacks for non-admin users.
  - _Files: `backend/app.py`, `frontend/index.html`, `frontend/script.js`, `frontend/style.css`_

- **Product Photo Thumbnails on Warranty Cards:** Enhanced warranty cards with visual product photo thumbnails for quick identification and easy access to full-size images.
  - **Thumbnail Display:** Product photos now appear as small thumbnails in the top right corner of each warranty card, providing instant visual recognition of products.
  - **Multi-View Support:** Photo thumbnails are displayed across all warranty viewing modes:
    - **Grid View:** 60px thumbnails positioned elegantly in the card corner
    - **List View:** 50px thumbnails for compact horizontal layouts
    - **Table View:** 40px thumbnails optimized for dense data display
  - **Interactive Photo Access:** Users can click on any product photo thumbnail to open the full-size image in a new browser tab for detailed viewing.
  - **Secure Image Handling:** Product photos are served through secure authentication, ensuring only authorized users can view warranty images while maintaining fast loading performance.
  - **Real-time Updates:** When users add or update product photos through the warranty edit forms, the thumbnail images immediately appear on warranty cards without requiring a page refresh.
  - **Visual Feedback:** Photo thumbnails include hover effects and "Click to view full size image" tooltips to clearly indicate their interactive nature.
  - **Responsive Design:** Photo thumbnails automatically scale and position appropriately across different screen sizes and device types.
  - _Files: `frontend/script.js`, `frontend/style.css`_

### Fixed
- **Status Dashboard Chart.js Canvas Errors**
  - Fixed "Canvas is already in use" errors on the status page that prevented charts from rendering properly
  - **Chart Destruction**: Added proper chart destruction with error handling before creating new charts
  - **Multiple Initialization Prevention**: Added initialization flags to prevent multiple dashboard initializations
  - **DOM Event Protection**: Protected against duplicate DOM event handler attachments
  - **Improved Error Handling**: Added try-catch blocks around chart creation and destruction operations
  - **View Switching Stability**: Fixed chart recreation issues when switching between personal and global views
  - **Result**: Status page charts now render reliably without canvas conflicts, multiple view switches work smoothly
  - _Files: `frontend/status.js`_

- **CSS Cache Busting for Domain Consistency**
  - Added version parameters to CSS and JavaScript files across all major pages to prevent caching issues between local IP and domain access
  - **CSS Files Updated:** `style.css?v=20250529005`, `header-fix.css?v=20250529005`, `mobile-header.css?v=20250529005`, `settings-styles.css?v=20250529005`
  - **JavaScript Files Updated:** `script.js?v=20250529005`, `auth.js?v=20250529005`, `settings-new.js?v=20250529005`
  - Updated Service Worker cache name to `warracker-cache-v2` and included all versioned files to force cache refresh
  - Fixed styling inconsistencies where admin global warranty view and other features appeared differently between local IP and domain access
  - Ensures all users get consistent styling and functionality across all pages including index, settings, and status pages
  - _Files: `frontend/index.html`, `frontend/settings-new.html`, `frontend/status.html`, `frontend/script.js`, `frontend/sw.js`_
- **Settings Page Admin Permission Issues:** Fixed critical database connection errors and 403 permission issues preventing regular users from accessing the settings page.
  - **Backend Database Connection (`backend/app.py`):** Fixed inconsistent cursor variable usage in `delete_account()` function that was causing 500 errors when users attempted to delete their accounts (was using both `cursor` and `cur` variables inconsistently).
  - **Frontend Admin Permission Checks (`frontend/settings-new.js`):** Added comprehensive admin permission checks to prevent non-admin users from triggering 403 errors:
    - **Initial Load Protection:** Wrapped admin-only settings calls (`loadSiteSettings()`, `loadAppriseSettings()`, `loadAppriseSiteSettings()`) with user admin status checks during page initialization.
    - **Deferred Load Protection:** Added admin checks for delayed Apprise settings loading to prevent unauthorized API calls.
    - **Graceful 403 Handling:** Enhanced `loadSiteSettings()` function with proper 403 response handling that hides admin sections instead of showing error messages.
  - **Improved Error Messaging:** Fixed misleading "Account cannot be deleted in offline mode" error by removing problematic nested try-catch that was masking actual API error messages. Users now see specific backend error messages instead of generic offline warnings.
  - **Root Cause:** Settings page was unconditionally calling admin-only API endpoints for all users, causing 403 errors and confusing error messages for regular users.
  - **Result:** Regular users can now access settings page without errors, see only relevant settings sections, and get clear error messages when actual issues occur. Admin users continue to see all settings sections as expected.
  - _Files: `backend/app.py`, `frontend/settings-new.js`_

- **Settings Persistence Critical Fixes:** Resolved major settings page persistence issues where user preferences would appear to save but revert to defaults when navigating away and returning.
  - **Backend Settings UPDATE Logic (`backend/app.py`):** Fixed critical bug in `/api/auth/preferences` endpoint where Apprise notification settings weren't being properly saved to the database:
    - **Column Detection Fix:** Changed condition from `if apprise_notification_time and has_apprise_notification_time_col:` to `if apprise_notification_time is not None and has_apprise_notification_time_col:` to handle empty string values properly
    - **Complete Field Mapping:** Added missing Apprise fields (`notification_channel`, `apprise_notification_time`, `apprise_notification_frequency`, `apprise_timezone`) to SELECT query return fields
    - **Preference Response Mapping:** Enhanced preference mapping to include all Apprise settings in API responses
  - **Frontend Race Condition Fixes (`frontend/settings-new.js`):** Eliminated multiple simultaneous API calls that were causing preference loading conflicts:
    - **Duplicate Request Prevention:** Fixed `loadPreferences()` being called 4 times simultaneously, causing race conditions
    - **API Priority Logic:** Ensured API data takes precedence over localStorage when both exist
    - **UI Synchronization:** Added proper dark mode toggle sync between API and UI state
    - **Authentication Token Standardization:** Unified token usage pattern across all preference save functions
  - **Root Cause:** Backend was silently failing to save Apprise settings due to strict conditional logic, while frontend race conditions were creating inconsistent data states
  - **Result:** Settings now persist correctly across page navigations, with all notification preferences saving and loading reliably
  - _Files: `backend/app.py`, `frontend/settings-new.js`_

- **Notification System Comprehensive Overhaul:** Fixed critical timing and duplicate notification issues affecting both email and Apprise scheduled notifications.
  - **Timing Logic Precision (`backend/notifications.py`):** Completely rewrote notification timing calculation for accurate delivery:
    - **Precise Windows:** Changed from aggressive "send_window or next_miss_window" logic to exact "0 <= time_diff <= 2" minute windows
    - **Post-Target Delivery:** Notifications now only send AFTER target time (not before) within 2-minute window to prevent early delivery
    - **Enhanced Time Calculations:** Added comprehensive timezone handling with detailed debug logging showing exact time differences
  - **Duplicate Prevention System (`backend/notifications.py`):** Implemented robust duplicate prevention using in-memory tracking:
    - **Separate Tracking:** Independent tracking for `email_{user_id}_{date}` and `apprise_{user_id}_{date}` patterns
    - **Daily Reset Logic:** Automatic cleanup for day rollover handling across different timezones
    - **Collision Prevention:** Added 0.1s delay for manual triggers to prevent collision with scheduled jobs
  - **Column Mismatch Fixes (`backend/notifications.py`):** Fixed database errors causing notification failures:
    - **Error Handling:** Added try/catch around column unpacking at line 327 to handle schema mismatches
    - **Variable Consistency:** Fixed missing `apprise_timezone` variable in debug logging sections
    - **Graceful Degradation:** System continues operating even with partial database schema issues
  - **Enhanced Debug Output (`backend/notifications.py`):** Added comprehensive logging for troubleshooting:
    - **Time Difference Display:** Shows exact calculations like "email_time=08:20(diff:-61), apprise_time=23:28(diff:-976)"
    - **Eligibility Reasons:** Clear logging explaining why users are/aren't eligible for notifications
    - **Real-time Diagnostics:** Live timing calculations visible in Docker logs for debugging
  - **Root Cause:** Overly aggressive timing windows caused duplicate emails, while backend save issues prevented Apprise settings from persisting, leading to notifications not being scheduled
  - **Result:** Both email and Apprise notifications now work reliably with precise timing, no duplicates, and proper settings persistence
  - _Files: `backend/notifications.py`, `backend/app.py`_



#### Technical Implementation for Global View Features
- **Backend (app.py):** 
  - Added new `/api/warranties/global` endpoint accessible to all authenticated users (not just admins)
  - Added `global_view_enabled` setting to site settings with default value 'true'
  - Added `global_view_admin_only` setting to site settings with default value 'false'
  - Added `/api/settings/global-view-status` endpoint for checking global view availability per user
  - Enhanced `/api/warranties/global` endpoint to check both global view settings and user admin status
  - Added new `/api/statistics/global` endpoint for global warranty statistics with user information
- **Frontend (script.js):** 
  - Renamed `initAdminViewControls()` to `initViewControls()` and removed admin-only restrictions
  - Updated `switchToGlobalView()` to check global view setting before switching
  - Added ownership and admin validation logic to conditionally render edit/delete buttons vs view-only placeholder
  - Admins see edit/delete buttons for all warranties, regular users only for their own
  - Modified API endpoint from `/api/admin/warranties` to `/api/warranties/global` for public access
  - Added real-time global view status checking and automatic fallback to personal view
- **Frontend (index.html):** Updated tooltips and labels to reflect public access
- **Frontend (style.css):** Added styling for view-only placeholder button with eye icon
- **Frontend (settings-new.html):** Added Global View Enabled and Global View Admin Only toggles in Site Settings section
- **Frontend (settings-new.js):** Added loading and saving logic for both global view settings
- **Frontend (status.html):** Added view switcher controls and owner column to warranty table for global view
- **Frontend (status.js):** Added global view functionality with API switching, table column management, and permission checking

#### Security Features
- Backend endpoint still requires authentication (all users must be logged in)
- Frontend validates warranty ownership and admin status before showing edit/delete buttons
- **Regular users** can only modify warranties they own, even in global view
- **Admin users** can modify any warranty in global view, maintaining administrative privileges
- Maintains data privacy while providing transparency

#### User Experience
- Seamless view switching between personal and global views for all users
- Clear visual indication (eye icon) when viewing others' warranties
- Consistent UI patterns with existing admin functionality
- Enhanced tooltips explaining read-only access for non-owned warranties

### Enhanced  
- **Footer Links:** Updated all "Powered by Warracker" footer links across the application to point to `https://warracker.com` instead of the GitHub repository, providing users with direct access to the official website.
  - **Files Updated:** `index.html`, `login.html`, `register.html`, `reset-password.html`, `reset-password-request.html`, `settings-new.html`, `status.html`, `auth-redirect.html`, and `about.html`
  - **Result:** Consistent branding and improved user experience with direct access to the official Warracker website.

- **PostgreSQL Security Hardening:** Removed unnecessary SUPERUSER privileges from the application database user, significantly improving security posture.
  - **Security Improvement:** Eliminated SUPERUSER grants that provided excessive and unnecessary privileges to the application database user
  - **Files Modified:** 
    - `backend/fix_permissions.sql`: Removed `ALTER ROLE %(db_user)s WITH SUPERUSER;` 
    - `backend/migrations/011_ensure_admin_permissions.sql`: Commented out SUPERUSER grant
    - `Dockerfile`: Removed retry loop attempting to grant SUPERUSER privileges via psql
  - **Principle of Least Privilege:** Application now operates with only the specific database privileges required for normal operation (CREATE/DROP/ALTER on tables, sequences, functions, etc.)
  - **Testing Verified:** Full application functionality confirmed to work correctly without SUPERUSER privileges, including migrations, user management, and all admin operations
  - **Security Benefit:** Significantly reduces attack surface - if the application is compromised, an attacker no longer has complete database administrative control
  - **Result:** Maintained full application functionality while eliminating unnecessary security risks

##  0.10.0.0 - 2025-06-4

### Fixed
- **View Preference Persistence Issue:** Fixed user view preferences (Grid, List, Table) not consistently persisting across logins.
  - **Backend (`backend/app.py`):** Modified `/api/auth/login` endpoint to include `is_admin` flag in the returned user object, ensuring proper view preference key prefix calculation immediately after login.
  - **Frontend (`frontend/script.js`):** 
    - Enhanced `switchView()` function with `saveToApi` parameter to control when view preferences are saved to the API, preventing unintended overwrites during initialization.
    - Modified `loadViewPreference()` to call `switchView` with `saveToApi = false` to prevent overwriting user's actual preferences with defaults.
    - Updated storage event listener for cross-tab synchronization to prevent redundant API saves when syncing view preferences between browser tabs.
  - **Root Cause:** Missing `is_admin` flag caused incorrect localStorage prefix usage and race conditions where preferences were saved with wrong prefix then not found when correct prefix was established.
  - **Result:** View preferences now properly persist across logins and synchronize between browser tabs for both admin and regular users.
- **Password Management Issues:** Fixed critical password change and reset functionality problems.
  - **Missing Password Change Endpoint (`backend/app.py`):** Implemented `/api/auth/password/change` endpoint to allow logged-in users to change their passwords through the Settings page. The endpoint validates current password, checks new password strength, and securely updates the user's password hash.
  - **Frontend Error Handling (`frontend/settings-new.js`):** Fixed misleading "Password cannot be changed in offline mode" error by removing nested try-catch block that was masking real API error messages. Now properly displays specific backend error messages.
  - **Password Reset Link Issue (`frontend/reset-password.html`):** Fixed "Invalid or Expired Link" error by removing premature token verification that was calling a non-existent `/api/auth/password/verify-token` endpoint. Token validity is now properly checked only during form submission.
  - **Root Cause:** Backend endpoint was missing entirely, frontend had incorrect error handling, and reset page was making unnecessary token verification calls.
  - **Result:** Users can now successfully change passwords while logged in and use password reset links without encountering false error messages.
- **SMTP Port 587 (STARTTLS) Functionality:** Enhanced email sending to support both port 465 (SMTPS/SSL) and port 587 (STARTTLS) configurations.
  - **Enhanced SMTP Connection Logic (`backend/app.py`):** Updated `send_password_reset_email()`, `send_expiration_notifications()`, and `send_email_change_verification_email()` functions with robust port-based SMTP logic.
    - **Port 465:** Uses `smtplib.SMTP_SSL()` for direct SSL connection
    - **Port 587:** Uses `smtplib.SMTP()` followed by `starttls()` for STARTTLS encryption  
    - **Other Ports:** Respects `SMTP_USE_TLS` environment variable for explicit STARTTLS control
  - **Environment Variable Support:** Added intelligent defaults where `SMTP_USE_TLS` defaults to true for port 587 unless explicitly set to false, ensuring proper STARTTLS behavior.
  - **Root Cause:** Previous logic used restrictive hostname-based conditions (`if smtp_host != 'localhost'`) instead of proper port-based SMTP configuration, causing STARTTLS failures with external SMTP servers on port 587.
  - **Result:** Email sending now works reliably with both common SMTP configurations, supporting major email providers like Gmail, Office 365, and other services using port 587.
- **Header Appearance Standardization (`frontend/reset-password-request.html`, `frontend/reset-password.html`):** Standardized headers to match consistent appearance across all pages.
  - **Missing CSS Includes:** Added `header-fix.css` and `fix-auth-buttons-loader.js` to ensure consistent header styling and behavior.
  - **Clickable Title:** Made "Warracker" title a clickable link to `index.html` for consistent navigation, matching other auth pages like `login.html` and `register.html`.
  - **Registration Status Script:** Added `registration-status.js` for consistent functionality across auth pages.
  - **Root Cause:** Pages were missing key CSS files and scripts that ensure header consistency, and the title was not a link unlike other pages.
  - **Result:** Headers now have identical appearance, dimensions, and responsive behavior as other application pages, providing consistent user experience.
### Enhanced  
- **Footer Links:** Updated all "Powered by Warracker" footer links across the application to point to `https://warracker.com` instead of the GitHub repository, providing users with direct access to the official website.
  - **Files Updated:** `index.html`, `login.html`, `register.html`, `reset-password.html`, `reset-password-request.html`, `settings-new.html`, `status.html`, `auth-redirect.html`, and `about.html`
  - **Result:** Consistent branding and improved user experience with direct access to the official Warracker website.

## 0.9.9.9 - 2025-06-01

### Added
- **OIDC SSO (Single Sign-On) Integration:**
  - Implemented OpenID Connect (OIDC) authentication flow using Authlib, allowing users to log in via external OIDC providers (e.g., Google, Keycloak).
  - **Backend (`app.py`):**
    - OIDC client configuration (Client ID, Secret, Issuer URL, Scope, Provider Name) is dynamically loaded from the `site_settings` database table at application startup.
    - OIDC feature can be enabled/disabled globally via the `oidc_enabled` setting in the database.
    - Added OIDC-specific routes: `/api/oidc/login` (initiates login) and `/api/oidc/callback` (handles redirect from IdP).
    - User provisioning: If an OIDC user doesn't exist locally, a new user account is created. Existing OIDC users are logged in.
    - Updated Admin Settings API (`/api/admin/settings`) to manage these OIDC parameters.
    - Database migration `023_add_oidc_columns_to_users.sql` adds `oidc_sub`, `oidc_issuer` to `users` table and `login_method` to `user_sessions` table for linking local users to OIDC identities.
  - **Frontend:**
    - **Login Page (`login.html`, `auth.js`):** Added an "Login with SSO Provider" button that initiates the OIDC flow.
    - **Admin Settings Page (`settings-new.html`, `settings-new.js`):** New "OIDC SSO Configuration" section for admins to enable/disable OIDC and configure provider details.
    - **Auth Redirect Page (`auth-redirect.html`):** Handles the token received from the `/api/oidc/callback` and logs the user in.
  - **Dependencies (`requirements.txt`):** Added `Authlib` and `requests`.
  - _Files: `backend/app.py`, `backend/migrations/023_add_oidc_columns_to_users.sql`, `backend/requirements.txt`, `frontend/login.html`, `frontend/auth.js`, `frontend/settings-new.html`, `frontend/settings-new.js`, `frontend/auth-redirect.html`_
- **SSO Registration Control:** When the site's registration setting is disabled, new users cannot register via SSO. Only existing users who already have accounts can use SSO to log in. This provides administrators with granular control over user registration while maintaining SSO functionality for existing users.
  - **Backend:** Enhanced OIDC callback handler to check the `registration_enabled` site setting before creating new user accounts via SSO.
  - **Frontend:** Added appropriate error message for users when SSO registration is blocked due to disabled registrations.
  - First user registration via SSO is still allowed regardless of the setting (same as regular registration).
  - _Files: `backend/oidc_handler.py`, `frontend/auth-redirect.html`_
- **Provider-Specific SSO Button Branding:** Enhanced the SSO login button to show provider-specific branding and icons for well-known OIDC providers.
  - **Supported Providers:** Google, GitHub, Microsoft/Azure, Facebook, Twitter, LinkedIn, Apple, Discord, GitLab, Bitbucket, Keycloak, and Okta.
  - **Dynamic Button Text:** Shows "Login with Google", "Login with GitHub", etc., based on the configured `OIDC_PROVIDER_NAME`.
  - **Provider Icons:** Uses appropriate Font Awesome icons for each provider (e.g., Google logo for Google, GitHub logo for GitHub).
  - **Brand Colors:** Each provider button uses authentic brand colors with proper hover effects.
  - **Fallback Support:** Unknown providers display the generic "Login with SSO Provider" button with default styling.
  - **Environment Integration:** Works automatically with the `OIDC_PROVIDER_NAME` environment variable and database settings.
  - _Files: `frontend/login.html`, `backend/oidc_handler.py`_
- **Exact Expiration Date Input:** Enhanced warranty entry to support exact expiration dates as an alternative to duration-based input.
  - **New Warranty Input Method:** Users can now choose between "Warranty Duration" (years/months/days) and "Exact Expiration Date" options when adding or editing warranties.
  - **UI Enhancements:** Added radio button selection for warranty entry method with smooth form field transitions and validation.
  - **Backend Support:** Both `add_warranty` and `update_warranty` API endpoints now handle `exact_expiration_date` parameter alongside duration fields.
  - **Smart Duration Display:** Warranty cards automatically calculate and display duration text even when using exact expiration dates, eliminating "N/A" values.
  - **Form Validation:** Enhanced validation ensures either exact date or duration is provided for non-lifetime warranties, with appropriate error messages.
  - **Date Calculation:** Added robust date calculation helper function that properly handles different month lengths, leap years, and edge cases.
  - _Files: `frontend/index.html`, `frontend/script.js`, `frontend/style.css`, `backend/app.py`_
- **Complete Field Updates:** All warranty fields (product info, dates, serial numbers, tags, documents) update immediately in the interface.
  - **Fallback Safety:** Maintains fallback to server reload if local update fails, ensuring data consistency.
  - _Files: `frontend/script.js`_
- **Memory Usage Optimization:** Significantly reduced RAM consumption for better performance on resource-constrained servers.
  - **Dynamic Memory Modes:** Configurable via `WARRACKER_MEMORY_MODE` environment variable with "optimized" (default), "ultra-light", and "performance" options.
  - **Optimized Mode:** 2 gevent workers with 128MB memory limits (~60-80MB total RAM usage).
  - **Ultra-Light Mode:** 1 sync worker with 64MB memory limit (~40-50MB total RAM usage for minimal servers).
  - **Performance Mode:** 4 gevent workers with 256MB memory limits (~150-200MB total RAM usage for high-performance servers).
  - **Worker Configuration:** Added memory limits per worker, connection pooling optimization, and preload_app for memory sharing.
  - **Database Pool:** Optimized connection pool from 10 to 4 maximum connections with memory-conscious settings.
  - **Flask Configuration:** Added memory-efficient settings including disabled JSON sorting, optimized session handling, and file serving optimizations.
  - **Dependency Addition:** Added gevent for more efficient async request handling compared to sync workers.
  - **Expected Reduction:** RAM usage configurable from ~40MB (ultra-light) to ~200MB (performance) based on server specifications.
  - _Files: `backend/gunicorn_config.py`, `backend/requirements.txt`, `backend/app.py`, `backend/db_handler.py`, `docker-compose.yml`_

### Changed
- **Environment Variables for OIDC (Docker):** While OIDC configuration is primarily managed via the database through the admin UI, the `docker-compose.yml` can include placeholder environment variables for initial setup or documentation:
  - `OIDC_ENABLED` (e.g., `true` or `false`)
  - `OIDC_PROVIDER_NAME` (e.g., `google`, `keycloak`)
  - `OIDC_CLIENT_ID`
  - `OIDC_CLIENT_SECRET`
  - `OIDC_ISSUER_URL`
  - `OIDC_SCOPE` (e.g., `openid email profile`)
- **`FRONTEND_URL` Environment Variable:** Emphasized the importance of correctly setting the `FRONTEND_URL` environment variable for the backend service in `docker-compose.yml` to ensure correct OIDC callback redirects.
  - _Files: `docker-compose.yml`, `Docker/docker-compose.yml`_

### Fixed
- Resolved various startup and runtime errors related to OIDC client initialization in a multi-worker (Gunicorn) environment, particularly concerning database connection pool stability and consistent loading of OIDC settings.
- Corrected OIDC metadata fetching by ensuring the proper Issuer URL is used (e.g., `https://accounts.google.com` for Google).
- Resolved `TypeError: Cannot read properties of null (reading 'classList')` during logout on `about.html` by ensuring the `loadingContainer` element is present and accessible to `script.js`'s `showLoading()` function. Modified `showLoading()` and `hideLoading()` to dynamically find the container if not initially available.
- Fixed `SyntaxError: Identifier 'AuthManager' has already been declared` on `about.html` by removing a duplicate import of `auth.js` from the `<head>`, ensuring it is loaded only once at the end of the `<body>`.
- Standardized the user menu dropdown button ID to `userMenuBtn` across `index.html`, `status.html`, and `about.html`. Consolidated user menu JavaScript logic into `auth.js`, removing redundant code from `settings-new.js` and `fix-auth-buttons.js` to ensure consistent dropdown behavior.
  - _Files: `backend/app.py`, `frontend/about.html`, `frontend/script.js`, `frontend/index.html`, `frontend/status.html`, `frontend/auth.js`, `frontend/settings-new.js`, `frontend/fix-auth-buttons.js`_
- **SSO Warranty Display Issue:** Fixed a critical timing problem where SSO users would see a blank warranty list after login. The issue was caused by a race condition where user preferences were loaded before user authentication was fully established.
  - Enhanced `auth-redirect.html` to fetch and store user information immediately after SSO login, ensuring `user_info` is available when the main application loads.
  - Fixed preference key prefix calculation to prevent mismatched user preference keys for SSO users.
  - _Files: `frontend/auth-redirect.html`, `frontend/auth.js`, `frontend/script.js`_
- **SSO Tag Creation Issue:** Resolved an issue where SSO users could not create new tags due to authentication token handling problems.
  - Updated tag creation functions (`createTag`, `updateTag`, `deleteTag`) to use `window.auth.getToken()` instead of directly accessing localStorage.
  - Added enhanced error handling and debugging for tag creation API calls.
  - Ensured consistent token management across all tag-related operations.
  - _Files: `frontend/script.js`_
- **Database Tag Constraint Issue:** Fixed database constraint violation that prevented users from creating tags with names that already existed for other users.
  - Created migration `024_fix_tags_constraint.sql` to update the database schema.
  - Dropped the old `tags_name_key` unique constraint that only considered tag names.
  - Added new `tags_name_user_id_key` constraint allowing the same tag name for different users.
  - Added proper user_id foreign key constraint and performance index.
  - _Files: `backend/migrations/024_fix_tags_constraint.sql`_
- **About Page User Menu Issue:** Fixed user menu dropdown not functioning on the about page for SSO users.
  - Resolved script loading order conflicts that prevented user menu event listeners from being attached.
  - Moved inline authentication check from head to body to prevent timing conflicts with `auth.js`.
  - Added backup user menu handler specifically for the about page with enhanced debugging.
  - Fixed JavaScript error caused by `getEventListeners` function not being available in all browsers.
  - _Files: `frontend/about.html`, `frontend/auth.js`_
- **About Page Logout Issue:** Resolved logout functionality errors on the about page.
  - Added safe loading spinner functions specifically for the about page to prevent `TypeError: Cannot read properties of null (reading 'classList')` error.
  - Implemented backup logout handler with multiple fallback levels for reliability.
  - Ensured logout works even when main auth system encounters errors.
  - _Files: `frontend/about.html`, `frontend/script.js`_
- **Immediate Warranty Updates:** Optimized warranty editing for instant UI updates without server reloads.
  - **Performance Improvement:** Warranty changes now appear immediately in the UI instead of waiting for server data reload.
  - **Local Data Sync:** Edit modal updates local warranty data instantly upon successful save, eliminating loading delays.
  - **Robust Date Handling:** Enhanced date arithmetic for duration-based warranties with proper month/year overflow handling.
  - **Complete Field Updates:** All warranty fields (product info, dates, serial numbers, tags, documents) update immediately in the interface.
  - **Fallback Safety:** Maintains fallback to server reload if local update fails, ensuring data consistency.
  - _Files: `frontend/script.js`_
- **Warranty Entry Method Persistence:** Fixed warranty entry method selection not being remembered correctly in edit modal.
  - **Issue:** When editing warranties that were created using "Exact Expiration Date" method, the edit modal would incorrectly switch to "Warranty Duration" method.
  - **Root Cause:** Display logic was overwriting original duration values (0,0,0 for exact date method), making method detection impossible.
  - **Solution:** Added `original_input_method` tracking to preserve the user's original warranty entry method choice.
  - **Data Separation:** Implemented separate `display_duration_*` fields for warranty card display while preserving original duration values for method detection.
  - **Enhanced Detection:** Edit modal now directly checks `original_input_method` field instead of guessing from duration data.
  - **Result:** Users can now edit warranties and the modal correctly remembers whether they originally used "Warranty Duration" or "Exact Expiration Date" method.
  - _Files: `frontend/script.js`_
- **Notes Modal and Edit Modal Integration:** Fixed issues with notes editing workflow and seamless transition to warranty editing.
  - **Notes Editing for Exact Date Warranties:** Resolved issue where warranties created with exact expiration dates couldn't have their notes edited via the notes-link modal due to invalid duration validation.
  - **Stale Notes in Edit Modal:** Fixed problem where editing a warranty immediately after saving notes via the notes modal would show old note content instead of the newly saved content.
  - **Notes Modal UI Issues:** Fixed "Edit Notes" button showing outdated note content when clicked after saving new notes in the same modal session.
  - **Enhanced Notes Modal:** Added "Edit Warranty" button directly in the notes modal footer for seamless transition to full warranty editing without modal layering conflicts.
  - **Immediate Data Sync:** Enhanced notes saving to immediately update the global warranties array, ensuring edit modal always shows current data.
  - **Modal State Management:** Improved modal closing behavior when opening edit modal from notes modal to prevent UI conflicts.
  - _Files: `frontend/script.js`_
- **Status Page Edit Modal Consistency:** Fixed inconsistency between edit warranty modals on index.html and status.html pages.
  - **Missing Warranty Entry Method Selection:** Added the "Warranty Entry Method" radio button selection to the status.html edit modal, allowing users to choose between "Warranty Duration" and "Exact Expiration Date" methods.
  - **Missing Exact Expiration Field:** Added the hidden "Exact Expiration Date" input field that appears when the exact date method is selected.
  - **Feature Parity:** The edit warranty modal on status.html now has identical functionality to the one on index.html, ensuring consistent user experience across both pages.
  - **Complete Modal Structure:** All tabs (Product, Warranty, Documents, Tags), form fields, and functionality now match exactly between both pages.
  - _Files: `frontend/status.html`_

### Dependencies
- **Updated Python Dependencies:** Resolved `pkg_resources` deprecation warning by updating backend dependencies to modern versions.
  - **Gunicorn:** Updated from `20.1.0` to `23.0.0` - eliminates `pkg_resources` deprecation warning by using `importlib.metadata` instead.
  - **Flask:** Updated from `2.0.1` to `3.0.3` - includes security patches and improved compatibility.
  - **Werkzeug:** Updated from `2.0.1` to `3.0.3` - maintains compatibility with Flask 3.x.
  - **Other Dependencies:** Updated `flask-cors`, `Flask-Login`, `PyJWT`, `email-validator`, `python-dateutil`, `Authlib`, `requests`, and `gevent` to latest stable versions.
  - **Setuptools Protection:** Added `setuptools<81` pin to prevent future compatibility issues.
  - _Files: `backend/requirements.txt`_

### Frontend
- **Chart.js Compatibility Fix:** Resolved "Chart is not defined" error on status page by replacing ES module version with UMD version.
  - **Issue:** Status page charts failed to load with `ReferenceError: Chart is not defined` because the local `chart.js` file was in ES module format.
  - **Root Cause:** ES modules require `<script type="module">` tags but the HTML was using regular `<script>` tags.
  - **Solution:** Replaced ES module version with locally downloaded UMD (Universal Module Definition) version from Chart.js v4.4.9, eliminating CDN dependency.
  - **Result:** Chart.js now loads properly with regular script tags and status page charts display correctly using the local file.
  - _Files: `frontend/chart.js`_
- **Product Name Hover Tooltips:** Added hover tooltips to display full product names when they are truncated with ellipsis.
  - **Enhancement:** Long product names that get cut off with "..." now show the complete product name in a tooltip when hovered over.
  - **Coverage:** Works across all warranty display modes (grid view, list view, table view) on the main warranties page and the status page table.
  - **Implementation:** Added `title` attributes to warranty titles and product name cells using escaped HTML for security.
  - **Result:** Users can now see full product names without having to edit or expand warranty details.
  - _Files: `frontend/script.js`, `frontend/status.js`_
- **Powered by Warracker Footer:** Added branded footer to all pages with dynamic theme support and GitHub repository link.
  - **Feature:** Added "Powered by Warracker" footer to all application pages linking to the GitHub repository.
  - **Theme Support:** Implemented JavaScript-based dynamic styling that automatically adapts to light/dark mode changes.
  - **Light Mode:** Light gray background (`#f5f5f5`), dark text (`#333333`), blue links (`#3498db`) matching the logo.
  - **Dark Mode:** Dark background (`#1a1a1a`), light text (`#e0e0e0`), light blue links (`#4dabf7`).
  - **Real-time Updates:** Uses MutationObserver to detect theme changes and update footer styling automatically.
  - **Cross-domain Compatibility:** Includes fallback inline styles and direct color values to ensure consistent display across different hosting environments.
  - _Files: All frontend HTML pages, `frontend/style.css`_

## [0.9.9.8] - 2025-05-24

### Added
- **Account Email Change:** Users can now change the email address associated with their account from the Settings page.
  - The email field in Account Settings is now editable.
  - Client-side and backend validation ensure the new email is valid and not already in use by another account.
  - The backend prevents duplicate emails and returns clear error messages for conflicts or invalid formats.
  - On successful change, the new email is reflected in the UI and localStorage, and users must use the new email to log in.
  - _Files: `frontend/settings-new.html`, `frontend/settings-new.js`, `backend/app.py`_
- **Progressive Web App (PWA) Support:** Enabled the application to be installed on Android devices.
  - Added and configured `manifest.json` with necessary properties (name, short_name, icons, start_url, display, orientation, theme_color, background_color, description).
  - Implemented a basic service worker (`sw.js`) with a cache-first strategy for core assets (HTML, CSS, JS, manifest, icons) to enable offline access and faster loading.
  - Registered the service worker in `script.js`.
  - Ensured `index.html` links to the `manifest.json` file.
  - Updated icon set in `manifest.json` and `sw.js` to use 16x16, 32x32, and 512x512 favicons.
  - _Files: `frontend/manifest.json`, `frontend/sw.js`, `frontend/script.js`, `frontend/index.html`_
- **Manage Tags Button on Index Page:** Added a "Manage Tags" button to the filter controls section on the main warranties page (`index.html`).
  - Clicking this button opens the tag management modal, which is now centered on the screen.
  - _Files: `frontend/index.html`, `frontend/script.js`, `frontend/style.css`_

### Changed
- **Mobile/Tablet Responsiveness:** Updated `index.html` , `status.html`  and associated CSS to improve the layout and usability of grid and list views on mobile and tablet devices.
  - _Files: `frontend/index.html`, `frontend/status.html`, `frontend/style.css` , `frontend/mobile-header.css`_
- **Database Credential Handling (Contribution by @humrochagf):** Replaced hardcoded database credentials with environment variable references for improved security and maintainability (Commit: 20997e9).
  - Removed hardcoded `db_user`, `db_admin_user`, and `db_admin_password` values.
  - Updated Dockerfile to eliminate redundant superuser credential checks.
  - Ensured `DB_ADMIN_PASSWORD` is configurable via Docker Compose environment variables, removing manual post-deployment steps.
  - Adjusted scripts to rely on dynamic credentials set in the environment.
  - _Files: `Dockerfile`, `backend/app.py`, `backend/fix_permissions.py`, `backend/fix_permissions.sql`, `backend/migrations/010_configure_admin_roles.sql`, `backend/migrations/011_ensure_admin_permissions.sql`, `backend/migrations/apply_migrations.py`, `docker-compose.yml`_

## [0.9.9.7] - 2025-05-16

### Added
- **Status Page - Collapsible Warranty Details**: Users can now click on a warranty row in the "Recently Expired or Expiring Soon" table on the Status page to expand a details section inline. This section displays more comprehensive information about the warranty, including Product URL, Purchase Price, Vendor, links to documents (Invoice, Manual, Other Files), Serial Numbers, and Notes.
  - Clicking the same row again collapses the details view.
  - Only one warranty's details can be expanded at a time.
  _Files: `frontend/status.js`, `frontend/style.css`_
- **Edit Warranty from Status Page**: You can now edit warranty details directly from the status page by clicking the "Edit Warranty" button in the expanded details section. This opens the edit modal with all warranty information pre-filled for editing.
  _Files: `frontend/status.js`, `frontend/script.js`, `frontend/style.css`_
- Added vendor column to sort options on the main warranty list.
  _Files: `frontend/index.html`, `frontend/script.js`_
- Added vendor filter dropdown to the main warranty list.
  _Files: `frontend/index.html`, `frontend/script.js`_

### Changed
- **Status Page Table**: Modified the Status page table to no longer link product names directly to a separate details page (related to the collapsible details feature).
  _Files: `frontend/status.js`_
- Updated CSV export functionality to format dates as YYYY-MM-DD.
  _Files: `frontend/script.js`, `frontend/status.js`_

### Fixed
- Fixed a console error "An invalid form control with name='product_url' is not focusable" that occurred when entering a product URL without a scheme (e.g., "example.com") in a hidden tab.
  - Changed `productUrl` and `editProductUrl` input types from `url` to `text` in `frontend/index.html` to prevent premature browser validation conflicts with the tabbed interface.
  - Enhanced `validateTab`, `showValidationErrors`, and `validateEditTab` in `frontend/script.js` to more reliably use HTML5 `control.validity.valid` and `control.validationMessage`, ensuring that if a field is invalid, its tab is shown and JavaScript-driven error messages are displayed.
  _Files: `frontend/script.js`_
- Resolved issue where the edit modal would close on backdrop click; it now only closes via the 'X' or 'Cancel' buttons.
  _Files: `frontend/script.js`_
- Resolved an issue where database migrations could fail if a custom `DB_NAME` was used. The hardcoded database name has been removed from migration files to support custom database names. (Thanks to @humrochagf for the contribution!)
  _Files: `backend/migrations/010_configure_admin_roles.sql`, `backend/migrations/011_ensure_admin_permissions.sql`_

## [0.9.9.6] - 2025-05-11

### Added
- **Warranty Duration Input:** Replaced the single "Warranty Period (Years)" input field with separate fields for Years, Months, and Days when adding or editing warranties.
  - Allows for more precise warranty duration entry (e.g., 2 years, 6 months, 15 days).
  - Updated Add/Edit forms (`frontend/index.html`), JavaScript logic (`frontend/script.js`), CSS styling (`frontend/style.css`), backend API (`backend/app.py`), and database schema (`backend/migrations/021_change_warranty_duration_to_components.sql`).
  - Warranty display on cards and summaries now shows the formatted duration (e.g., "2 years, 6 months").
  - CSV import/export updated to use `WarrantyDurationYears`, `WarrantyDurationMonths`, `WarrantyDurationDays` columns.
  - Backend validation ensures at least one duration component is provided for non-lifetime warranties.
  - Fixed backend logic to correctly handle empty duration inputs, treating them as 0.
  _Files: `backend/app.py`, `backend/migrations/021_change_warranty_duration_to_components.sql`, `frontend/index.html`, `frontend/script.js`, `frontend/style.css`_
- **Files Upload:** Users can now upload an additional ZIP/RAR file (e.g., for extended warranty documents, photos, or other related files) when adding or editing a warranty.
  - This document is stored securely and can be accessed from the warranty card.
  - _Files: `backend/app.py`, `backend/migrations/022_add_other_document_path.sql`, `frontend/index.html`, `frontend/script.js`_
- **Configurable JWT Secret Key:**
  - The application's JWT and session secret key can now be configured via the `SECRET_KEY` environment variable.
  - It is strongly recommended to set a unique, strong secret key in production environments. Defaults to a development key if not set.
  - _Relevant File: `backend/app.py` (for usage), `docker-compose.yml` (for setting)_
- **Configurable File Upload Limits:**
  - Maximum file upload sizes for both the backend application and the Nginx reverse proxy are now configurable via environment variables.
  - **Application (Flask):** Set `MAX_UPLOAD_MB` (e.g., `MAX_UPLOAD_MB=64`) to define the limit in megabytes. Defaults to 32MB.
  - **Nginx:** Set `NGINX_MAX_BODY_SIZE_VALUE` (e.g., `NGINX_MAX_BODY_SIZE_VALUE=64M`) to define the limit for Nginx (value must include unit like M or G). Defaults to "32M".
  - The `Dockerfile` and `nginx.conf` have been updated to support this.
  - _Files: `backend/app.py`, `nginx.conf`, `Dockerfile`_
- **Security key can be used in environment:**
   - **SECRET_KEY=**  is now usuable in docker-compose for jwt secret.
   - _Files: `Docker/docker-compose.yml`_

### Fixed
- **Backend Indentation Error:** Corrected an `IndentationError` in `backend/app.py` within the CSV import logic that prevented the backend from starting correctly.
  _Files: `backend/app.py`_
- **Migration Script Error:** Fixed an error in migration `021_change_warranty_duration_to_components.sql` where it incorrectly referenced `lifetime_warranty` instead of the correct `is_lifetime` column.
  _Files: `backend/migrations/021_change_warranty_duration_to_components.sql`_
- **smtplib import duplicate:** Removed line from app.py that re-imported smtplib with a pull request.
- _Files: `backend/app.py`_

### House Cleaning
- **Old Settings files:** Removed all older settings pages , and related files.
- _Files: `frontend/settings.html`,`frontend/settings.script.js`,`frontend/settings_redirect.html`_

## [0.9.9.5] - 2025-05-07

### Changed
- **Header Branding Improvement:**
  - Made the "Warracker" text in the header of the Status, Settings, and About pages a clickable link to the home page (`index.html`) for improved navigation and consistency.
  _Files: `frontend/status.html`, `frontend/settings-new.html`, `frontend/about.html`_

- **Tag Dropdown Color Removal:**
  - Removed all background and text colours from the tags dropdown in both dark mode and light mode for a cleaner, more consistent appearance.
  _Files: `frontend/style.css`, `frontend/script.js`, and any related tag dropdown CSS/JS._

- **Docker Base Image Update:**
  - Updated the `Dockerfile` to use Python 3.12 and Debian 12 (bookworm) as the base image for the container, ensuring improved compatibility and security.
  _File: `Dockerfile`_


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
- **UI:** Added an "Add New Warranty" button (`#showAddWarrantyBtn`) to trigger the new modal (`frontend/index.html`