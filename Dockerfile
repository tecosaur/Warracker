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
COPY backend/run_migrations.py .
COPY backend/fix_permissions.py .
COPY backend/fix_permissions.sql .
COPY backend/migrations/ ./migrations/

# Create directory for uploads with proper permissions
RUN mkdir -p /data/uploads && chmod 777 /data/uploads

# Copy frontend files
COPY frontend/*.html /var/www/html/
COPY frontend/*.js /var/www/html/
COPY frontend/*.css /var/www/html/
COPY test.html /var/www/html/

# Configure nginx
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create startup script with directory permission check and database initialization
RUN echo '#!/bin/bash\n\
echo "Checking /data/uploads directory:"\n\
ls -la /data/uploads\n\
echo "Setting permissions:"\n\
chmod -R 777 /data/uploads\n\
ls -la /data/uploads\n\
echo "Running database migrations..."\n\
python /app/run_migrations.py\n\
echo "Ensuring admin role has proper permissions..."\n\
# Retry logic for granting superuser privileges\n\
max_attempts=5\n\
attempt=0\n\
while [ $attempt -lt $max_attempts ]; do\n\
  echo "Attempt $((attempt+1)) to grant superuser privileges..."\n\
  if PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -U $DB_USER -d $DB_NAME -c "ALTER ROLE warranty_user WITH SUPERUSER;" 2>/dev/null; then\n\
    echo "Successfully granted superuser privileges to warranty_user"\n\
    break\n\
  else\n\
    echo "Failed to grant privileges, retrying in 5 seconds..."\n\
    sleep 5\n\
    attempt=$((attempt+1))\n\
  fi\n\
done\n\
echo "Running fix permissions script..."\n\
python /app/fix_permissions.py\n\
echo "Starting services..."\n\
nginx\n\
gunicorn --bind 0.0.0.0:5000 --workers 4 app:app\n\
' > /app/start.sh && chmod +x /app/start.sh

# This is just a fallback, the copied nginx.conf will be used
RUN echo 'server {\n\
    listen 80;\n\
    server_name localhost;\n\
    root /var/www/html;\n\
    index index.html;\n\
    \n\
    # Enable detailed error logging\n\
    error_log /var/log/nginx/error.log debug;\n\
    access_log /var/log/nginx/access.log;\n\
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
        proxy_pass http://127.0.0.1:5000;\n\
        proxy_set_header Host $host;\n\
        proxy_set_header X-Real-IP $remote_addr;\n\
    }\n\
    \n\
    # Direct access to uploads directory\n\
    location /uploads/ {\n\
        alias /data/uploads/;\n\
        autoindex on;\n\
        \n\
        # Set appropriate MIME types\n\
        types {\n\
            image/png png PNG;\n\
            image/jpeg jpg jpeg JPG JPEG;\n\
            application/pdf pdf PDF;\n\
            text/plain txt TXT;\n\
        }\n\
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
command=/app/start.sh
directory=/app
autostart=true
autorestart=true
stdout_logfile=/dev/stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr
stderr_logfile_maxbytes=0
EOF

# Make sure the uploads directory is writable
RUN chmod -R 777 /data/uploads

# Start supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]