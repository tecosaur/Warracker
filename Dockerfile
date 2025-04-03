# Start with Python base image
FROM python:3.9-slim-buster

# Install nginx, postgresql-client, supervisor and dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        nginx \
        curl \
        postgresql-client \
        supervisor \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Ensure nginx runs in the foreground for Supervisor
RUN sed -i '1i daemon off;' /etc/nginx/nginx.conf

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend code
COPY backend/app.py .
COPY backend/gunicorn_config.py .
COPY backend/fix_permissions.py .
COPY backend/fix_permissions.sql .
COPY backend/migrations/ /app/migrations/

# Copy frontend files
COPY frontend/*.html /var/www/html/
COPY frontend/*.js /var/www/html/
COPY frontend/*.css /var/www/html/

# Configure nginx site
RUN rm /etc/nginx/sites-enabled/default
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Create startup script with database initialization
RUN echo '#!/bin/bash\n\
set -e # Exit immediately if a command exits with a non-zero status.\n\
echo "Running database migrations..."\n\
python /app/migrations/apply_migrations.py\n\
echo "Ensuring admin role has proper permissions..."\n\
# Retry logic for granting superuser privileges\n\
max_attempts=5\n\
attempt=0\n\
while [ $attempt -lt $max_attempts ]; do\n\
  echo "Attempt $((attempt+1)) to grant superuser privileges..."\n\
  # Ensure DB variables are set (you might pass these at runtime)\n\
  if [ -z "$DB_PASSWORD" ] || [ -z "$DB_HOST" ] || [ -z "$DB_USER" ] || [ -z "$DB_NAME" ]; then\n\
    echo "Error: Database connection variables (DB_PASSWORD, DB_HOST, DB_USER, DB_NAME) are not set."\n\
    exit 1\n\
  fi\n\
  # Use timeout to prevent indefinite hanging if DB is not ready\n\
  if PGPASSWORD=$DB_PASSWORD psql -w -h $DB_HOST -U $DB_USER -d $DB_NAME -c "ALTER ROLE warranty_user WITH SUPERUSER;" 2>/dev/null; then\n\
    echo "Successfully granted superuser privileges to warranty_user"\n\
    break\n\
  else\n\
    echo "Failed to grant privileges (attempt $((attempt+1))), retrying in 5 seconds..."\n\
    sleep 5\n\
    attempt=$((attempt+1))\n\
  fi\n\
done\n\
if [ $attempt -eq $max_attempts ]; then\n\
  echo "Error: Failed to grant superuser privileges after $max_attempts attempts."\n\
  exit 1 # Exit if granting fails after retries\n\
fi\n\
echo "Running fix permissions script..."\n\
python /app/fix_permissions.py\n\
echo "Setup script finished successfully."\n\
# The actual services (gunicorn, nginx) will be started by Supervisor below\n\
exit 0 # Exit successfully, Supervisor takes over\n\
' > /app/start.sh && chmod +x /app/start.sh

# This is just a fallback Nginx config echo, the copied nginx.conf is primary
# Note: Removed the /uploads/ location block from here.
# Ensure your actual nginx.conf doesn't reference it if not needed.
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
    client_max_body_size 32M;\n\
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
        client_max_body_size 32M;\n\
    }\n\
    \n\
}' > /etc/nginx/conf.d/default.conf

# Expose port
EXPOSE 80

# Define health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost/ || exit 1

# Set environment variables
ENV PYTHONUNBUFFERED=1

# Create supervisor log directory
RUN mkdir -p /var/log/supervisor

# Create supervisor configuration
# Using Heredoc for cleaner multiline config
COPY <<EOF /etc/supervisor/conf.d/supervisord.conf
[supervisord]
nodaemon=true                 ; Run Supervisor in the foreground
user=root                     ; Run Supervisor as root
logfile=/dev/stdout           ; Log Supervisor messages to stdout
logfile_maxbytes=0            ; Disable log rotation for stdout
pidfile=/var/run/supervisord.pid

; Program for initial setup (migrations, permissions)
; Runs once at the start
[program:setup]
command=/app/start.sh         ; Execute the setup script
directory=/app
autostart=true
autorestart=false             ; Do not restart if it finishes
startsecs=0                   ; Start immediately
startretries=1                ; Only retry once if it fails immediately
exitcodes=0                   ; Expected exit code is 0
stdout_logfile=/dev/stdout    ; Log stdout to container stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr    ; Log stderr to container stderr
stderr_logfile_maxbytes=0
priority=5                    ; Run before nginx and gunicorn

[program:nginx]
command=/usr/sbin/nginx       ; Run nginx reading default config (with 'daemon off;' added)
autostart=true
autorestart=true              ; Restart nginx if it crashes
startsecs=5                   ; Give setup some time before starting nginx
startretries=5
stdout_logfile=/dev/stdout    ; Log stdout to container stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr    ; Log stderr to container stderr
stderr_logfile_maxbytes=0
priority=10                   ; Start after setup

[program:gunicorn]
command=gunicorn --config /app/gunicorn_config.py app:app ; Start Gunicorn
directory=/app
autostart=true
autorestart=true              ; Restart Gunicorn if it crashes
startsecs=5                   ; Give setup some time before starting gunicorn
startretries=5
stdout_logfile=/dev/stdout    ; Log stdout to container stdout
stdout_logfile_maxbytes=0
stderr_logfile=/dev/stderr    ; Log stderr to container stderr
stderr_logfile_maxbytes=0
priority=20                   ; Start after setup
stopsignal=QUIT               ; Graceful shutdown signal for Gunicorn
stopwaitsecs=10               ; Wait up to 10 seconds for graceful shutdown
killasgroup=true              ; Ensure all gunicorn processes are killed
stopasgroup=true              ; Ensure all gunicorn processes receive the stop signal
EOF

# Start supervisor which will manage the setup, nginx, and gunicorn processes
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
