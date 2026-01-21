# Use python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Cloud Run sets PORT environment variable
ENV PORT=8080
EXPOSE 8080

# Run with gunicorn for production
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 app:app
