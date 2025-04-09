########## Stage 1 – build Python wheels (optional) ##########
FROM python:3.11-alpine AS build
RUN apk add --no-cache build-base && \
    pip wheel --wheel-dir=/wheels -r requirements.txt

########## Stage 2 – runtime ##########
FROM alpine:3.19
# tools
RUN apk add --no-cache \
        python3 py3-pip \
        ghostscript tesseract-ocr tesseract-ocr-data-eng \
        unpaper pngquant qpdf file

# wheels from stage 1
COPY --from=build /wheels /wheels
RUN pip install --no-cache-dir /wheels/*

# app
WORKDIR /app
COPY . .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
