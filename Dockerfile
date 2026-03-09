# Use an official Python base image
# FROM python:3.10-slim
FROM ubuntu:22.04

# Install required system packages
RUN apt-get update && apt-get install -y \
    gcc\
    redis-server \
    ghostscript \
    wkhtmltopdf \
    supervisor \
    python3 \
    python3.10-venv \
    nano \
    && apt-get clean

# Set up working directory
WORKDIR /app

# Copy project files
COPY . /app
# RUN apt-get install -y /app/wkhtmltox_0.12.6.1-2.jammy_amd64.deb

# Ensure shell scripts are executable and have Unix line endings (handles Windows CRLF)
RUN chmod +x /app/*.sh && sed -i 's/\r$//' /app/*.sh

# Create and activate virtual environment
# RUN python -m venv /opt/venv \
#     && . /opt/venv/bin/activate \
#     && pip install --upgrade pip \
#     && pip install -r requirements.txt


# NOTE: As of now not creating virtual environment for the project (only for development)
# RUN python3 -m venv /app/ntpc_reporting_engine_venv \
#     && . /app/ntpc_reporting_engine_venv/bin/activate \
#     && pip install --upgrade pip \
#     && pip install -r requirements.txt


# Build Python extensions
# RUN . /opt/venv/bin/activate && python build.py build_ext clean

# Copy supervisor config
COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

# Expose ports if needed (e.g., for Redis or other services)
EXPOSE 6379


CMD ["/app/start_reporting_service.sh"]
# Start supervisord
# CMD ["/usr/bin/supervisord", "-n"]
# CMD ["/usr/bin/supervisord", "-c", "/etc/supervisor/conf.d/supervisord.conf"]
