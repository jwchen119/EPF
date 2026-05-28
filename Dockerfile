FROM python:3.9-slim

WORKDIR /app

# System dependencies:
#   gcc + python3-dev  → compile the Cython extension
#   libraw-dev         → rawpy (RAW/DNG decoding)
#   fonts-dejavu-core  → DejaVu fonts used for date overlay
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc \
        python3-dev \
        libraw-dev \
        fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies (including Cython for the build step)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt cython

# Copy source
COPY . .

# Compile the Cython extension for this platform.
# Falls back gracefully to cpy_fallback.py at runtime if this fails.
RUN cython cpy.pyx && \
    gcc -shared -fPIC -O2 \
        $(python3-config --includes) \
        -I$(python3 -c "import numpy; print(numpy.get_include())") \
        cpy.c -o cpy.so && \
    rm cpy.c || echo "Cython build failed — pure-Python fallback will be used"

# Runtime data directories (overridable via env / volumes)
RUN mkdir -p /data/photos /data/local_photos /data/config

ENV IMMICH_PHOTO_DEST=/data/photos \
    LOCAL_PHOTO_DIR=/data/local_photos \
    CONFIG_FILE=/data/config/config.yaml

EXPOSE 5000

CMD ["python", "app.py"]
