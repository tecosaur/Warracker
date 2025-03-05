# Changelog

## [0.05.2-beta] - 2024-03-05

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