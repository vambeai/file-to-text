# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Install system dependencies for OCRMypdf
RUN apt-get update && apt-get install -y --no-install-recommends \
    # Build tools
    build-essential \
    # Pillow dependencies
    libjpeg-dev \
    zlib1g-dev \
    libtiff5-dev \
    libopenjp2-7-dev \
    libwebp-dev \
    # pikepdf dependency
    libqpdf-dev \
    # ocrmypdf dependencies
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    unpaper \
    pngquant \
    qpdf \
    # python-magic dependency
    libmagic1 \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Expose port
EXPOSE 8000

# Command to run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
