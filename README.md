🛡️ Warracker 

Warracker is an open-source warranty tracker application designed to help you effortlessly keep track of product warranties, expiration dates, and related documentation. 
🌟 Overview 

Warracker is a web-based application that provides a centralized system for managing all your product warranties. Key features include: 

     Tracking product warranties in one central location.
     Adding warranty details, including purchase dates and duration.
     Uploading and storing warranty documentation and receipts.
     Providing visual indicators for active, expiring soon, and expired warranties.
     Searching through your warranty collection.
     

📸 Screenshots 

![image](https://github.com/user-attachments/assets/da2a2b2d-4ab9-4e51-bf75-d393b728c39e)

✨ Features 

     Warranty Management: Add, edit, and delete warranty information.
     Document Storage: Upload and securely store receipts and warranty documentation.
     Status Tracking: Visual indicators for warranty status (active, expiring soon, expired).
     Search: Easily find warranties by product name.
     Responsive Design: A seamless experience on both desktop and mobile devices.
     

🛠️ Technology Stack 

     Frontend: HTML, CSS, JavaScript
     Backend: Python with Flask
     Database: PostgreSQL
     Containerization: Docker and Docker Compose
     Web Server: Nginx
     

🚀 Installation 
Prerequisites 

     Docker and Docker Compose installed on your system.
     Git (for cloning the repository).
     

Setup 

     

    Clone the Repository: 
    bash
     
      

 
1
2
git clone https://github.com/yourusername/warracker.git
cd warracker
 
 
 

Start the Application: 
bash
 
  

     
    1
    docker-compose up -d
     
     
     

    Access the Application: 

    Open your browser and navigate to http://localhost:8005. 
     

📝 Usage 
Adding a Warranty 

     Fill in the product details on the left panel.
     Enter the purchase date and warranty duration.
     Optionally upload receipt/documentation.
     Click the "Add Warranty" button.
     

Managing Warranties 

     Use the search box to filter warranties.
     Click the edit icon to modify warranty details.
     Click the delete icon to remove a warranty.
     

💻 Development 
Local Development Environment 

     

    Clone the repository. 
     

    Make your changes. 
     

    Build and run with Docker Compose: 
    bash
     
      

     
    1
    2
    docker-compose build
    docker-compose up -d
     
     
     

Project Structure 
 
 
 
1
2
3
4
5
6
7
8
9
10
11
12
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
 
 
🗺️ Roadmap 

     User authentication.
     Email reminders for expiring warranties.
     Mobile app.
     Settings page.
     Status page.
     

🛠️ Troubleshooting 
Common Issues 

     Connection Refused Error:  Ensure all containers are running (docker-compose ps). Verify the backend is correctly connected to the database.
     Database Errors: If schema issues arise, double-check that the database initialization script (init.sql) matches the expected schema in app.py.
     

🤝 Contributing 

Contributions are welcome! We encourage you to submit a Pull Request. 

     Fork the repository.
     Create your feature branch (git checkout -b feature/amazing-feature).
     Commit your changes (git commit -m 'Add some amazing feature').
     Push to the branch (git push origin feature/amazing-feature).
     Open a Pull Request.
     

📜 License 

This project is licensed under the MIT License - see the LICENSE  file for details.  (Make sure you have a LICENSE file in your root directory). 
🙏 Acknowledgements 

     Flask
     PostgreSQL
     Docker
