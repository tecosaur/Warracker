# 🛡️ Warracker

Warracker is an open-source warranty tracker application designed to help you effortlessly keep track of product warranties, expiration dates, and related documentation.

## 🌟 Overview

Warracker is a web-based application that provides a centralized system for managing all your product warranties. Key features include:

*   Tracking product warranties in one central location.
*   Adding warranty details, including purchase dates and duration.
*   Uploading and storing warranty documentation and receipts.
*   Providing visual indicators for active, expiring soon (less than 30 days), and expired warranties.
*   Searching through your warranty collection.

## 📸 Screenshots

**Home Page**

![image](https://github.com/user-attachments/assets/a833ab2e-b70b-4b4c-9b1d-b22305ce73da)

![image](https://github.com/user-attachments/assets/9b3300ff-e5f2-46b9-be48-95ac782029b4)

**Status Dashboard**  

![image](https://github.com/user-attachments/assets/dc35f8ac-97d1-4db9-906a-f52c05803c2a)



## ✨ Features

*   **Warranty Management**: Add, edit, and delete warranty information.
*   **Document Storage**: Upload and securely store receipts and warranty documentation.
*   **Status Tracking**: Visual indicators for warranty status (active, expiring soon, expired).
*   **Search**: Easily find warranties by product name.
*   **Responsive Design**: A seamless experience on both desktop and mobile devices.

## 🛠️ Technology Stack

*   **Frontend**: HTML, CSS, JavaScript
*   **Backend**: Python with Flask
*   **Database**: PostgreSQL
*   **Containerization**: Docker and Docker Compose
*   **Web Server**: Nginx

## 🚀 Installation

### Prerequisites

*   Docker and Docker Compose installed on your system.
*   Git (for cloning the repository).

### Setup

1.  **Clone the Repository:**

    ```bash
    git clone https://github.com/sassanix/warracker.git
    cd warracker
    ```
2.  **Start the Application:**

    ```bash
    docker-compose up -d
    ```
3.  **Access the Application:**

    Open your browser and navigate to `http://localhost:8005`.

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

## 💻 Development

### Local Development Environment

1.  Clone the repository.
2.  Make your changes.
3.  Build and run with Docker Compose:

    ```bash
    docker-compose build
    docker-compose up -d
    ```

### Docker Compose

## Docker Compose Configuration

Use the following Docker Compose configuration to deploy the latest build of the image:

```yaml
version: '3'

services:
  warracker:
    image: ghcr.io/sassanix/warracker/main:latest
    ports:
      - "8005:80"
    volumes:
      - ./uploads:/data/uploads
    environment:
      - DB_HOST=warrackerdb
      - DB_NAME=warranty_db
      - DB_USER=warranty_user
      - DB_PASSWORD=${DB_PASSWORD:-warranty_password}
    depends_on:
      warrackerdb:
        condition: service_healthy
    restart: unless-stopped

  warrackerdb:
    image: "postgres:15-alpine"
    volumes:
      - postgres_data:/var/lib/postgresql/data
      - ./backend/init.sql:/docker-entrypoint-initdb.d/init.sql
    environment:
      - POSTGRES_DB=warranty_db
      - POSTGRES_USER=warranty_user
      - POSTGRES_PASSWORD=${DB_PASSWORD:-warranty_password}
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U warranty_user -d warranty_db"]
      interval: 10s
      timeout: 5s
      retries: 5

volumes:
  postgres_data:
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

*   User authentication.
*   Email reminders for expiring warranties.
*   Settings page.
*   Status page.

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
