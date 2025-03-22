FROM python:3.11-slim

WORKDIR /app

# Install required packages
RUN apt-get update && apt-get install -y \
    cron \
    wget \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/data/pdfs /app/logs /app/templates

# Copy templates first
COPY templates/* /app/templates/

# Copy Python files and entrypoint script
COPY *.py /app/
COPY entrypoint.sh /app/

# Set up cron job
RUN echo "0 */12 * * * /usr/local/bin/python /app/scraper.py >> /app/logs/scraper.log 2>&1" > /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN crontab /etc/cron.d/scraper-cron

# Set permissions
RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/*.py

# Create empty database
RUN touch /app/data/database.db
RUN chmod 666 /app/data/database.db

# Volume for persistent storage
VOLUME ["/app/data", "/app/logs"]

# Expose port for web UI
EXPOSE 9734

# Add Unraid-specific labels
LABEL \
    org.opencontainers.image.title="ACEA Auto Reports Monitor" \
    org.opencontainers.image.description="Automatically collects and organizes ACEA auto industry reports" \
    org.opencontainers.image.version="1.0.0" \
    com.unraid.docker.icon="https://cdn-icons-png.flaticon.com/512/2432/2432572.png" \
    com.unraid.docker.webui="http://[IP]:[PORT:9734]/" \
    com.unraid.docker.defaultport="9734" \
    com.unraid.docker.support="https://github.com/istinmth/acea-monitor/issues" \
    com.unraid.docker.overview="ACEA Auto Reports Monitor - Automatically collects and organizes ACEA auto industry reports."

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=30s --retries=3 \
  CMD curl -f http://localhost:9734/health || exit 1

# Run entrypoint script
ENTRYPOINT ["/app/entrypoint.sh"]