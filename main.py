from fastapi import FastAPI, HTTPException, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import os
from dotenv import load_dotenv
import requests
import tempfile
import ocrmypdf
from pathlib import Path
import shutil

load_dotenv()

app = FastAPI(title="Document OCR API")

API_KEY = os.getenv("API_KEY")
API_KEY_NAME = "X-API-Key"

api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

async def get_api_key(api_key_header: str = Security(api_key_header)):
    if not api_key_header or api_key_header != API_KEY:
        raise HTTPException(
            status_code=HTTP_403_FORBIDDEN, detail="Could not validate API key"
        )
    return api_key_header

@app.get("/process-document")
async def process_document(url: str, api_key: str = Depends(get_api_key)):
    try:
        # Download the file
        response = requests.get(url)
        response.raise_for_status()

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Save downloaded file
            input_file = temp_path / "input_file"
            with open(input_file, "wb") as f:
                f.write(response.content)

            # Determine if file is PDF
            if response.headers.get('content-type') == 'application/pdf':
                output_file = temp_path / "output.pdf"

                # Process PDF with OCR
                ocrmypdf.ocr(
                    input_file,
                    output_file,
                    force_ocr=True,
                    skip_text=False,
                    output_type='pdf'
                )

                # Extract text from processed PDF
                with open(output_file, 'rb') as f:
                    # Here you would extract text from the PDF
                    # For now, returning a placeholder
                    return {"text": "PDF text extracted successfully"}
            else:
                # For non-PDF files, return the content directly
                return {"text": response.text}

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error downloading file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
