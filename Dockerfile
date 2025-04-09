# Use Python 3.12 as base image
FROM python:3.12

# Install system dependencies needed by ocrmypdf and python-magic
# Temporarily add testing repo to force newer ghostscript (> 10.02.0)
RUN echo "deb http://deb.debian.org/debian testing main" > /etc/apt/sources.list.d/testing.list && \
    # Pin ghostscript to testing, keep others stable
    echo "Package: *\nPin: release a=stable\nPin-Priority: 900\n\nPackage: ghostscript\nPin: release a=testing\nPin-Priority: 990" > /etc/apt/preferences.d/pinning && \
    apt-get update && apt-get install -y --no-install-recommends \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    unpaper \
    pngquant \
    qpdf \
    libmagic1 \
    # Clean up testing repo config
    && rm /etc/apt/sources.list.d/testing.list && rm /etc/apt/preferences.d/pinning \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Upgrade pip and install build tools
RUN pip install --upgrade pip setuptools wheel

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
