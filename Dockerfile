FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Exposed Flask port
EXPOSE 5000

# Environment variables. Declared here so that they are listed, with these
# defaults, wherever a container is set up from the image (Synology Container
# Manager shows them), and are not forgotten.
# IMMICH API KEY
ENV IMMICH_API_KEY="your-api-key"
# The server's port: "auto" takes 5000, the port Docker maps on a bridge
# network, or the first free one from 15001 when something already listens on
# 5000 (host networking on a Synology, whose DSM uses it). A number fixes it.
ENV EPF_PORT=auto
# Quiet hours and the wake-up schedule run on local time: set your own zone,
# e.g. Asia/Taipei
ENV TZ=Etc/UTC
ENV PATH=/home/app/.local/bin:$PATH

# Default command
CMD ["python", "app.py"]