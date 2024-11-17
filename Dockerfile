# Use Python 3.11 slim as base image
FROM python:3.11-slim

# Install system dependencies for OCRMypdf
RUN apt-get update && apt-get install -y \
    ghostscript \
    tesseract-ocr \
    tesseract-ocr-eng \
    unpaper \
    pngquant \
    qpdf \
    libmagic1 \
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
