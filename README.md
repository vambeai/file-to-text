# Document OCR API

A FastAPI-based API service that processes documents and extracts text, including OCR for images within PDFs.

## Features

- API Key authentication
- Process documents from public URLs
- OCR support for PDFs with images
- Docker support for easy deployment

## API Endpoints

### GET /process-document

Process a document and extract its text content.

**Headers:**

- X-API-Key: Your API key

**Query Parameters:**

- url: Public URL of the document to process

**Response:**

```json
{
  "text": "Extracted text content from the document"
}
```

### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy"
}
```

## Local Development

1. Install dependencies:

```bash
pip install -r requirements.txt
```

2. Set up environment variables:

```bash
cp .env.example .env
# Edit .env with your secure API key
```

3. Run the server:

```bash
uvicorn main:app --reload
```

## Docker Deployment

1. Build the Docker image:

```bash
docker build -t document-ocr-api .
```

2. Run the container:

```bash
docker run -p 8000:8000 -d --env-file .env document-ocr-api
```

The API will be available at http://localhost:8000

## Security Notes

- Keep your API key secure and never commit it to version control
- Use HTTPS in production
- Regularly update dependencies
