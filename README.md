
<div align="center">
    
![420682616-b65106d3-2c3c-4f6c-a4b7-4ec6e010e5b8](https://github.com/user-attachments/assets/cb373fe8-b4d2-47ac-bf7b-060289e6e17c)

![warracker logo update](https://github.com/user-attachments/assets/0ebd9bc1-4b6c-44a5-9ea9-59c68e52cc6f)


</div>

<div align="center">
    
<!-- ![GitHub forks](https://img.shields.io/github/forks/sassanix/Warracker?style=social) -->
![GitHub issues](https://img.shields.io/github/issues/sassanix/Warracker)
![GitHub license](https://img.shields.io/github/license/sassanix/Warracker)
![GitHub last commit](https://img.shields.io/github/last-commit/sassanix/Warracker)
![GitHub release](https://img.shields.io/github/v/release/sassanix/Warracker)
![GitHub contributors](https://img.shields.io/github/contributors/sassanix/Warracker)
<!-- ![Downloads](https://img.shields.io/github/downloads/sassanix/Warracker/total) -->
[![Dependencies Status](https://img.shields.io/badge/dependencies-up%20to%20date-brightgreen.svg)](https://github.com/denser-org/denser-retriever/pulls?utf8=%E2%9C%93&q=is%3Apr%20author%3Aapp%2Fdependabot)
![Maintenance](https://img.shields.io/badge/Maintained-Actively-green)

#
    
</div>

# 🛡️ Warracker

Warracker is an open-source warranty tracker application designed to help you effortlessly keep track of product warranties, expiration dates, and related documentation.

## 🌟 Overview

Warracker is a web-based application that provides a centralized system for managing all your product warranties. Key features include:

* **Centralized Warranty Management:** Track all product warranties in one place.
* **Detailed Records:** Store key warranty information like purchase date and duration.
* **Document Storage:** Upload and securely store warranty documentation and receipts.
* **Proactive Alerts:** Get visual notifications for active, expiring (customizable from 1 to 365 days), and expired warranties.
* **Quick Search:** Easily find specific warranties within your collection.
* **Secure Access:**  User authentication and support for multiple users.
* **System Status:** Real-time system status page.
* **Data Export:** Export warranty data to CSV format.
* **Data Import:** Import warranty data in CSV format.
* **Email notifications:** Stay informed about expiring warranties with email reminders, based on your preference delivered daily, weekly, or monthly.
* **Tagging:** Add tags to help categorize and group warranties.


## 📸 Screenshots

**Home Page**

![image](https://github.com/user-attachments/assets/dc29f858-4f8c-4a98-b321-5bdc345eab74)

![image](https://github.com/user-attachments/assets/7348274a-9e59-40d0-865e-92e3fe5bed21)


**Status Dashboard**  

![image](https://github.com/user-attachments/assets/a9a9f9b4-2ad5-4069-91f8-96066a99658b)



## ✨ Features

*   **Warranty Management**: Add, edit, and delete warranty information.
*   **Document Storage**: Upload and securely store receipts and warranty documentation.
*   **Status Tracking**: Visual indicators for warranty status (active, expiring soon, expired).
*   **Search**: Easily find warranties by product name or tags.
*   **Tag**: Group your warranties by using multiple tags.
*   **Responsive Design**: A seamless experience on both desktop and mobile devices.

## 🛠️ Technology Stack

*   **Frontend**: HTML, CSS, JavaScript
*   **Backend**: Python with Flask
*   **Database**: PostgreSQL
*   **Containerization**: Docker and Docker Compose
*   **Web Server**: Nginx

## 🚀 Setup

### Prerequisites

*   Docker and Docker Compose installed on your system.
*   Git (for cloning the repository).

### Fresh Installation 🆕
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

### Updating from a Previous Version ⬆️
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


## 🐋 Pull Docker


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

## 📝 Usage

### Adding a Warranty

1.  Fill in the product details on the left panel.
2.  Enter the purchase date and warranty duration.
3.  Optionally upload receipt/documentation.
4.  Click the "Add Warranty" button.

### Managing Warranties

*   Use the search box to filter warranties.
*   Click the edit icon to modify warranty details.
*   Click the delete icon to remove a warranty.

## 📦 Product Information Entry Requirements for import

| Field Name     | Format / Example                          | Required?                                              | Notes                                                                 |
|----------------|-------------------------------------------|--------------------------------------------------------|-----------------------------------------------------------------------|
| **ProductName** | Text                                       | ✅ Yes                                                  | Provide the name of the product.                                     |
| **PurchaseDate** | Date (`YYYY-MM-DD`, e.g., `2024-05-21`)   | ✅ Yes                                                  | Use ISO format only.                                                 |
| **WarrantyYears** | Whole Number (`1`, `3`, `10`)             | ✅ Yes, unless `IsLifetime` is `TRUE`                   | Must be between `1` and `100` if provided.                           |
| **IsLifetime**  | `TRUE` or `FALSE` (case-insensitive)       | ❌ No (Optional)                                        | If omitted, defaults to `FALSE`.                                     |
| **PurchasePrice** | Number (`199.99`, `50`)                  | ❌ No (Optional)                                        | Cannot be negative if provided.                                      |
| **SerialNumber** | Text (`SN123`, `SN123,SN456`)             | ❌ No (Optional)                                        | For multiple values, separate with commas.                           |
| **ProductURL**   | Text (URL format)                         | ❌ No (Optional)                                        | Full URL to product page (optional field). https://producturl.com                           |
| **Tags**         | Text (`tag1,tag2`)                        | ❌ No (Optional)                                        | Use comma-separated values for multiple tags.                        |


## 💻 Development

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

## 🗺️ Roadmap

*   User Authentication - **Completed ✅**
*   Settings Page - **Completed ✅**
*   Status Page - **Completed ✅**
*   Customizing Reminders to any day needed - **Completed ✅**
*   Email Reminders for Expiring Warranties - **Completed ✅**
*   Warranty Categories/Grouping through tags - **Completed ✅**
*   Warranty Data Import (CSV) - **Completed ✅**
*   Improved Search and Filtering - **Planned**
*   Warranty claim tracking - **Planned**
*   Calendar Integration - **Planned**


## 🛠️ Troubleshooting

### Common Issues

*   **Connection Refused Error**:  Ensure all containers are running (`docker-compose ps`). Verify the backend is correctly connected to the database.
*   **Database Errors**: If schema issues arise, double-check that the database initialization script (`init.sql`) matches the expected schema in `app.py`.

## 🤝 Contributing

Contributions are welcome! We encourage you to submit a Pull Request.

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

## 📜 License

This project is licensed under the GNU Affero General Public License v3.0 - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgements

*   Flask
*   PostgreSQL
*   Docker

## ⭐ Star History
<a href="https://star-history.com/#sassanix/Warracker&Date">
 <picture>
   <source media="(prefers-color-scheme: dark)" srcset="https://api.star-history.com/svg?repos=sassanix/Warracker&type=Date&theme=dark" />
   <source media="(prefers-color-scheme: light)" srcset="https://api.star-history.com/svg?repos=sassanix/Warracker&type=Date" />
   <img alt="Star History Chart" src="https://api.star-history.com/svg?repos=sassanix/Warracker&type=Date" />
 </picture>
</a>
