FROM python:3.11-slim

WORKDIR /app

# Install required packages and locales
RUN apt-get update && apt-get install -y \
    cron \
    wget \
    curl \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Configure locales
RUN localedef -i en_US -c -f UTF-8 -A /usr/share/locale/locale.alias en_US.UTF-8
ENV LANG=en_US.UTF-8
ENV LC_ALL=en_US.UTF-8

# Copy requirements first to leverage Docker cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create necessary directories
RUN mkdir -p /app/data/pdfs /app/logs /app/templates /app/data/excel

# Copy templates first
COPY templates/* /app/templates/

# Copy Python files and entrypoint script
COPY *.py /app/
COPY entrypoint.sh /app/

# Create config directory for Adobe credentials
RUN mkdir -p /app/config

# Add this to your Dockerfile after copying Python files
COPY pdfservices-api-credentials.json /app/config/
COPY pdfservices-api-credentials.json /app/config/
COPY adobe_utils.py /app/
COPY excel_formatter.py /app/

# Set restrictive permissions on credentials file
RUN chmod 600 /app/config/pdfservices-api-credentials.json
# Set up cron job
RUN echo "0 */12 * * * /usr/local/bin/python /app/scraper.py >> /app/logs/scraper.log 2>&1" > /etc/cron.d/scraper-cron
RUN chmod 0644 /etc/cron.d/scraper-cron
RUN crontab /etc/cron.d/scraper-cron

# Set permissions
RUN chmod +x /app/entrypoint.sh
RUN chmod +x /app/*.py
RUN chmod -R 777 /app/data

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