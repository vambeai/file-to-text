########## Stage 1 – Ghostscript ##########
FROM minidocks/ghostscript:latest AS gs

########## Stage 2 – Python runtime ##########
FROM python:3.11-slim AS runtime

# copy Ghostscript binary (& libs) from stage 1
COPY --from=gs /usr/bin/gs /usr/bin/gs
COPY --from=gs /usr/lib /usr/lib
COPY --from=gs /usr/share/ghostscript /usr/share/ghostscript

# install remaining system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        unpaper \
        pngquant \
        qpdf \
        libmagic1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# python deps & app setup (same as above) …
WORKDIR /app
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# ---------- app code ----------
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
