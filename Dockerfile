####################  Stage 0 – build Ghostscript 10.05.0  ####################
FROM debian:stable-slim AS gs-build

ARG GS_VERSION=10.05.0

# Paquetes de compilación y dependencias que Ghostscript necesita
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential wget ca-certificates tar \
        libjpeg-dev libpng-dev libtiff-dev zlib1g-dev \
        liblcms2-dev libfreetype6-dev libfontconfig1-dev \
    && wget -q https://github.com/ArtifexSoftware/ghostpdl-downloads/releases/download/gs${GS_VERSION//./}/ghostscript-${GS_VERSION}.tar.xz \
    && tar -xf ghostscript-${GS_VERSION}.tar.xz \
    && cd ghostscript-${GS_VERSION} \
    && ./configure --prefix=/usr/local --disable-compile-inits --without-x \
    && make -j"$(nproc)" && make install \
    && strip /usr/local/bin/gs \
    && rm -rf /var/lib/apt/lists/* /ghostscript-${GS_VERSION}*

####################  Stage 1 – runtime  ####################
FROM python:3.11-slim

# Copiamos Ghostscript (binario y recursos) desde la etapa anterior
COPY --from=gs-build /usr/local/bin/gs /usr/local/bin/gs
COPY --from=gs-build /usr/local/lib/ghostscript /usr/local/lib/ghostscript
COPY --from=gs-build /usr/local/share/ghostscript /usr/local/share/ghostscript

# Dependencias del sistema que necesita tu app
RUN apt-get update && apt-get install -y --no-install-recommends \
        tesseract-ocr \
        tesseract-ocr-eng \
        unpaper \
        pngquant \
        qpdf \
        libmagic1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

####################  Python y aplicación  ####################
WORKDIR /app

# Instalar dependencias de Python primero para aprovechar la caché
COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Copiar el resto del código
COPY . .

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
