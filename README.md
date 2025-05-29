
<div align="center">
    
<img src="https://github.com/user-attachments/assets/2132a842-4233-4d37-8fde-b2d23353ed76" width="100"/>

<h1 <strong>Warracker</strong></h1>
<p align="center">
    <b>Open-source warranty tracker for individuals and teams.</b> <br/>
The easiest way to organize product warranties, monitor expiration dates, and store receipts or related documents.
</b>
</p>
</div>


<div align="center">
    
<!-- ![GitHub forks](https://img.shields.io/github/forks/sassanix/Warracker?style=social) -->
![GitHub issues](https://img.shields.io/github/issues/sassanix/Warracker)
![GitHub license](https://img.shields.io/github/license/sassanix/Warracker)
![GitHub last commit](https://img.shields.io/github/last-commit/sassanix/Warracker)
![GitHub release](https://img.shields.io/github/v/release/sassanix/Warracker)
![GitHub contributors](https://img.shields.io/github/contributors/sassanix/Warracker)
<!-- ![Downloads](https://img.shields.io/github/downloads/sassanix/Warracker/total) -->

<p align="center">
  <img src="images/demo.gif" alt="Warracker Demo" width="600">
</p>


#
    
</div>

## Overview

**Warracker** is a web-based application designed to simplify and centralize product warranty management.

## Key Capabilities

* **Centralized Warranty Management:** Track and manage all your product warranties in one place.
* **Detailed Records:** Save essential details like purchase dates, durations, and notes.
* **Document Storage:** Upload and securely store receipts, invoices, product manuals, and other related files (e.g., ZIP, RAR archives).
* **Proactive Alerts:** Visual notifications for active, expiring (customizable from 1 to 365 days), and expired warranties.
* **Quick Search and Filter:** Instantly find warranties by product name, serial numbers, vendor, tags, or notes.
* **Notes Support:** Add freeform notes to each warranty for extra context or reminders.
* **Secure Access with Multi-User Support:** Create multiple user accounts for shared access; admins can enable or disable new user creation.
* **System Status Dashboard:** Real-time system health and warranty summary.
* **Data Export and Import:** Export warranty data to CSV, or import warranties from CSV files.
* **Email Notifications:** Receive timely email reminders about upcoming expirations, configurable as daily, weekly, or monthly.
* **Customizable Currency Symbols:** Display prices using your preferred currency symbol (\$, €, £, ¥, ₹, or a custom symbol).
* **Customizable Dates:** Display dates based on your region.
* **Tagging:** Organize warranties with flexible, multi-tag support.
* **Password Reset:** Easily recover accounts through a secure, token-based password reset flow.


## Project Status

**Warracker is in active beta.**
The essential features are reliable and ready for everyday use. Development is ongoing, with regular updates and improvements.

* ✅ Stable core for tracking, notification , and managing warranty documents, files
* ✅ Full support for self-hosted deployments
* ⚒️ Advanced enhancements are still being worked on
* ✍️ Your feedback and bug reports help shape the future of the app

## Screenshots

**Home Page**

![image](https://github.com/user-attachments/assets/fa491480-4c75-4a1a-91d0-741141ca0183)


![image](https://github.com/user-attachments/assets/67662203-b25b-46e5-920d-082537a02d42)

**Status Dashboard**  

![image](https://github.com/user-attachments/assets/4c938b33-d6be-4787-a2d9-9153b0234ee2)

## Features

- **Warranty Management:** Add, edit, and delete warranty information easily.
- **Document Storage:** Upload and manage receipts, invoices, and product manuals securely.
- **Extended Document Storage:** Securely upload and store additional product-related documents or files in ZIP or RAR format.
- **Status Tracking:** Visual indicators for warranty status (active, expiring soon, expired).
- **Notes:** Add detailed notes for each warranty, viewable and editable via a dedicated notes modal.
- **Search and Tagging:** Find warranties quickly using product names, serial numbers, vendor, notes, or multiple tags.
- **Multi-User Management:** Support for multiple user accounts; admin users can control whether new accounts can be created.
- **Responsive Design:** Optimized for both desktop and mobile devices.
- **Secure Login:** Safe and private authentication for all users.
- **Password Reset:** Token-based secure password recovery flow.
- **Email Alerts:** Customize how and when you receive expiration notifications.
- **CSV Export/Import:** Full support for backing up and restoring warranty data.
- **Currency Customization:** Personalize displayed prices with your preferred symbol.


## Technology Stack

*   **Frontend**: HTML, CSS, JavaScript
*   **Backend**: Python with Flask
*   **Database**: PostgreSQL
*   **Containerization**: Docker and Docker Compose
*   **Web Server**: Nginx

## Roadmap

*   User Authentication - **Completed ✅**
*   Settings Page - **Completed ✅**
*   Status Page - **Completed ✅**
*   Customizing Reminders to any day needed - **Completed ✅**
*   Email Reminders for Expiring Warranties - **Completed ✅**
*   Warranty Categories/Grouping through tags - **Completed ✅**
*   Warranty Data Import (CSV) - **Completed ✅**
*   Improved Search and Filtering - **Completed ✅**
*   Warranty claim tracking - **Planned**
*   Calendar Integration - **Planned**
*   OIDC SSO Functionality - **Planned**
*   Advanced user and admin control - **Planned**
*   Localization support - **Planned**

## Setup

### Prerequisites

*   Docker and Docker Compose installed on your system.
*   Git (for cloning the repository).

### Fresh Installation 
1. Clone the repository:
   ```
   git clone https://github.com/sassanix/Warracker.git
   ```
2. Navigate to the project directory:
   ```
   cd Warracker
   ```
3. Start the application using Docker:
   ```
   docker compose up
   ```

### Updating from a Previous Version
1. Pull the latest changes:
   ```
   git pull origin main
   ```
2. Rebuild and restart the containers:
   ```
   docker compose down
   docker compose up --build
   ```
3.  **Access the Application:**

    Open your browser and navigate to `http://localhost:8005`.


## Pull Docker


```
services:
  warracker:
    image: ghcr.io/sassanix/warracker/main:latest
    ports:
      - "8005:80"
    volumes:
      - warracker_uploads:/data/uploads
    environment:
      - DB_HOST=warrackerdb
      - DB_NAME=warranty_db
      - DB_USER=warranty_user
      - DB_PASSWORD=${DB_PASSWORD:-warranty_password}
      - SMTP_HOST=smtp.email.com
      - SMTP_PORT=465
      - SMTP_USERNAME=youremail@email.com
      - SMTP_PASSWORD=password
      - SECRET_KEY=${APP_SECRET_KEY:-your_strong_default_secret_key_here} 
      - MAX_UPLOAD_MB=32 # Example: Set max upload size to 32MB 
      - NGINX_MAX_BODY_SIZE_VALUE=32M # For Nginx, ensure this matches MAX_UPLOAD_MB in concept (e.g., 32M)
    # - FLASK_DEBUG=0
    depends_on:
      warrackerdb:
        condition: service_healthy
    restart: unless-stopped
  
  warrackerdb:
    image: postgres:15-alpine
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_DB=warranty_db
      - POSTGRES_USER=warranty_user
      - POSTGRES_PASSWORD=${DB_PASSWORD:-warranty_password}
    restart: unless-stopped

    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $$POSTGRES_USER -d $$POSTGRES_DB"]
      interval: 5s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
  warracker_uploads:
```

To get the docker compose file please go [here](https://github.com/sassanix/Warracker/tree/main/Docker)

## Usage

### Adding a Warranty

1.  Fill in the product details by clicking on add warranty.
2.  Enter the purchase date and warranty duration.
3.  Optionally upload receipt/documentation.
4.  Click the "Add Warranty" button.

### Managing Warranties

*   Use the search box to filter warranties.
*   Click the edit icon to modify warranty details.
*   Click the delete icon to remove a warranty.

## 📦 Product Information Entry Requirements for CSV import

| Field Name     | Format / Example                          | Required?                                              | Notes                                                                 |
|----------------|-------------------------------------------|--------------------------------------------------------|-----------------------------------------------------------------------|
| **ProductName** | Text                                       | ✅ Yes                                                  | Provide the name of the product.                                     |
| **PurchaseDate** | Date (`YYYY-MM-DD`, e.g., `2024-05-21`)   | ✅ Yes                                                  | Use ISO format only.                                                 |
| **WarrantyDurationYears** | Whole Number (`0`, `1`, `5`)      | ✅ Yes, if `IsLifetime` is `FALSE` and Months/Days are 0/blank. At least one duration field (Years, Months, Days) must be non-zero if not lifetime. | Represents the years part of the warranty. Can be combined with Months and Days. |
| **WarrantyDurationMonths** | Whole Number (`0`, `6`, `18`)    | ✅ Yes, if `IsLifetime` is `FALSE` and Years/Days are 0/blank. At least one duration field (Years, Months, Days) must be non-zero if not lifetime. | Represents the months part of the warranty. Can be combined with Years and Days. Max 11 if Years also provided. |
| **WarrantyDurationDays** | Whole Number (`0`, `15`, `90`)     | ✅ Yes, if `IsLifetime` is `FALSE` and Years/Months are 0/blank. At least one duration field (Years, Months, Days) must be non-zero if not lifetime. | Represents the days part of the warranty. Can be combined with Years and Months. Max 29/30 if Months also provided. |
| **IsLifetime**  | `TRUE` or `FALSE` (case-insensitive)       | ❌ No (Optional)                                        | If omitted, defaults to `FALSE`. If `TRUE`, duration fields are ignored. |
| **PurchasePrice** | Number (`199.99`, `50`)                  | ❌ No (Optional)                                        | Cannot be negative if provided.                                      |
| **SerialNumber** | Text (`SN123`, `SN123,SN456`)             | ❌ No (Optional)                                        | For multiple values, separate with commas.                           |
| **ProductURL**   | Text (URL format)                         | ❌ No (Optional)                                        | Full URL to product page (optional field). https://producturl.com                           |
| **Vendor**       | Text                                      | ❌ No (Optional)                                        | Name of the vendor or seller where the product was purchased.        |
| **Tags**         | Text (`tag1,tag2`)                        | ❌ No (Optional)                                        | Use comma-separated values for multiple tags.                        |


## Development

### Local Development Environment

1.  Clone the repository.
2.  Make your changes.
3.  Build and run with Docker Compose:

    ```bash
    docker-compose build
    docker-compose up -d
    ```

### Project Structure

```
warracker/
├── backend/             # Python Flask backend
│   ├── app.py           # Main application logic
│   ├── requirements.txt # Python dependencies
│   └── init.sql         # Database initialization
├── frontend/            # Web frontend
│   ├── index.html
│   ├── script.js
│   └── style.css
├── docker-compose.yml   # Docker configuration
├── Dockerfile           # Container definition
└── nginx.conf           # Web server configuration
```

## Why I Built This

Warracker was born out of a frustrating and all-too-common experience: dealing with warranties.

My father once called me for help with his broken dishwasher. We were confident it was still under warranty, especially since we had the invoice. But after countless back-and-forth with the manufacturer, they insisted it wasn’t covered due to a mismatch in the serial number. The truth? My father had unknowingly purchased **two** dishwashers, and we were referencing the wrong one.

This wasn’t my first time running into warranty headaches, and I realized there had to be a better way. That’s when I decided to build **Warracker**, a simple tool to track purchases, receipts, and warranty periods in one place. Since then, Warracker has already saved me money by alerting me before my **car’s warranty expired**, allowing me to make necessary repairs just in time.

Inspired by [**Wallos**](https://github.com/ellite/Wallos), an app I used to track subscriptions, I thought, *why not do the same for warranties?* Now I want to make it available to anyone who has faced similar frustration.

Thank you for your support as I continue to improve Warracker.

## Contributing

We welcome contributions and appreciate your interest in improving this project! To get started, please follow these steps:


### How to Contribute

1. **Fork** the repository.
2. **Create a branch** for your changes:
   `git checkout -b feature/amazing-feature`
3. **Commit** your changes:
   `git commit -m "Add: amazing feature"`
4. **Push** to your forked repository:
   `git push origin feature/amazing-feature`
5. **Open a Pull Request** with a clear explanation of your changes.

### Contribution Guidelines

* **Start with an issue**: Before submitting a Pull Request, ensure the change has been discussed in an issue.
* **Help is welcome**: Check the [issues](../../issues) for open discussions or areas where help is needed.
* **Keep it focused**: Each Pull Request should focus on a single change or feature.
* **Follow project style**: Match the project's code style and naming conventions.
* **Be respectful**: We value inclusive and constructive collaboration.

### Contributors:  

[<img src="https://avatars.githubusercontent.com/u/39465071?s=50&v=4" width="50"/>](https://github.com/sassanix)
[<img src="https://avatars.githubusercontent.com/u/1223625?s=50&v=4" width="50"/>](https://github.com/humrochagf)
[<img src="https://avatars.githubusercontent.com/u/5875512?s=50&v=4" width="50"/>](https://github.com/clmcavaney)

### ❤️ Supporters:

[<img src="https://avatars.githubusercontent.com/u/8194208?u=7ee82feed0044f85bcfc39f001643fe81a188f66&v=4&s=50" width="50"/>](https://github.com/SirSpidey)
[<img src="https://avatars.githubusercontent.com/u/6196195?v=4&s=50" width="50"/>](https://github.com/keithellis74)



[![Support Warracker](https://img.shields.io/badge/Support-Warracker-red?style=for-the-badge&logo=github-sponsors)](https://buymeacoffee.com/sassanix)

## License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## Acknowledgements

*   Flask
*   PostgreSQL
*   Docker

## Star History
<a href="https://star-history.com/#sassanix/Warracker&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=sassanix/Warracker&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=sassanix/Warracker&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=sassanix/Warracker&type=Date" />
 </picture>
</a>
