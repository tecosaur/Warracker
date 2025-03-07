# Changelog

# Changelog

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
