#!/bin/bash
set -e

echo "Starting ACEA Monitor container..."

# List all files and directories for debugging
echo "Contents of /app directory:"
ls -la /app

echo "Contents of templates directory:"
ls -la /app/templates || echo "Templates directory not found or empty"

# Create necessary directories with proper permissions
mkdir -p /app/data/pdfs /app/logs
chmod -R 755 /app
chmod -R 777 /app/data /app/logs
chmod +x /app/*.py

# Check if templates exist
if [ ! -d "/app/templates" ] || [ -z "$(ls -A /app/templates 2>/dev/null)" ]; then
    echo "WARNING: Templates directory is missing or empty! Creating placeholder templates..."
    mkdir -p /app/templates
    
    # Create a basic template as fallback
    cat > /app/templates/base.html << 'EOL'
<!DOCTYPE html>
<html>
<head>
    <title>ACEA Monitor</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { font-family: Arial, sans-serif; margin: 0; padding: 20px; }
        h1 { color: #2c3e50; }
    </style>
</head>
<body>
    <h1>ACEA Monitor</h1>
    <div>{% block content %}{% endblock %}</div>
</body>
</html>
EOL

    cat > /app/templates/index.html << 'EOL'
{% extends "base.html" %}
{% block content %}
<h2>Dashboard</h2>
<p>Welcome to ACEA Monitor</p>
{% endblock %}
EOL
fi

# Start cron service
service cron start
echo "Started cron service"

# Initialize database if it doesn't exist
if [ ! -s /app/data/database.db ]; then
    echo "No database found or empty database, running initial scan..."
    python /app/scraper.py
else
    echo "Database exists, skipping initial scan"
fi

# Print debug info
echo "Environment variables:"
env

echo "Python packages:"
pip list

echo "Starting web application..."
# Start with debug mode for troubleshooting
exec gunicorn --bind 0.0.0.0:9734 --workers 2 --threads 4 --timeout 120 --log-level debug --access-logfile - --error-logfile - app:app