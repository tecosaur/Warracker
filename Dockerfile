# Start with Python base image
FROM python:3.9-slim-buster

# Install nginx and dependencies
RUN apt-get update && apt-get install -y \
    nginx \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app.py .

# Create directory for uploads
RUN mkdir -p /data/uploads

# Copy frontend files
COPY frontend/index.html /var/www/html/
COPY frontend/script.js /var/www/html/
COPY frontend/style.css /var/www/html/

# Configure nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create startup script
RUN echo '#!/bin/bash\n\
nginx\n\
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app\n\
' > /app/start.sh && chmod +x /app/start.sh

# Create nginx configuration
RUN echo 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    root /var/www/html;\n\
    index index.html;\n\
    \n\
    # Enable gzip compression\n\
    gzip on;\n\
    gzip_types text/plain text/css application/javascript application/json;\n\
    \n\
    location / {\n\
        try_files $uri $uri/ /index.html;\n\
    }\n\
    \n\
    # Proxy API requests to backend\n\
    location /api/ {\n\
        proxy_pass http://localhost:5000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    # Proxy uploads to backend\n\
    location /uploads/ {\n\
        proxy_pass http://localhost:5000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    # Cache static assets\n\
    location ~* \.(css|js|jpg|jpeg|png|gif|ico|svg)$ {\n\
        expires 7d;\n\
        add_header Cache-Control "public, max-age=604800";\n\
    }\n\
}' > /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Define health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost/api/warranties || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Install supervisor to manage multiple processes
RUN apt-get update && apt-get install -y supervisor && apt-get clean
RUN mkdir -p /var/log/supervisor

# Create supervisor configuration
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true
user=root

[program:nginx]
command=nginx -g "daemon off;"
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0

[program:gunicorn]
command=gunicorn --bind 0.0.0.0:5000 --workers 4 app:app
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]