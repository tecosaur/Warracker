FROM python:3.9-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directory for uploads
RUN mkdir -p /data/uploads && chmod 777 /data/uploads

# Expose port
EXPOSE 5000

# Start the application
CMD ["python", "app.py"] 