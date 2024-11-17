from fastapi import FastAPI, HTTPException, Security, Depends, Request
from fastapi.security.api_key import APIKeyHeader
from starlette.status import HTTP_403_FORBIDDEN
import os
from dotenv import load_dotenv
import requests
import tempfile
import ocrmypdf
from pathlib import Path
import shutil
from pdfminer.high_level import extract_text
import pytesseract
from PIL import Image
import io
import imghdr

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

def is_image_content(content: bytes) -> bool:
    """Detect if content is an image by trying to open it with PIL"""
    try:
        image = Image.open(io.BytesIO(content))
        return True
    except:
        return False

def is_pdf_content(content: bytes) -> bool:
    """Detect if content is a PDF by checking magic numbers"""
    return content.startswith(b'%PDF')

@app.get("/process-document")
async def process_document(request: Request, url: str = None, api_key: str = Depends(get_api_key)):
    # Debug information
    print("Query Params:", dict(request.query_params))
    print("Headers:", dict(request.headers))

    if not url:
        raise HTTPException(status_code=422, detail="URL parameter is required")

    try:
        # Download the file
        response = requests.get(url)
        response.raise_for_status()
        content = response.content

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "input_file"

            # Save downloaded file
            with open(input_file, "wb") as f:
                f.write(content)

            # Detect file type from content
            if is_pdf_content(content):
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
                text = extract_text(str(output_file))
                try:
                    print("PDF TEXT:")
                    print(text[:1000])
                except UnicodeEncodeError:
                    print("PDF TEXT: (unable to display due to encoding issues)")
                return {"text": text}

            elif is_image_content(content):
                # Process image with Tesseract
                try:
                    # Open image using PIL
                    image = Image.open(io.BytesIO(content))

                    # Convert image to text using Tesseract
                    text = pytesseract.image_to_string(image)

                    # Generate PDF if needed
                    pdf_path = temp_path / "output.pdf"
                    pytesseract.image_to_pdf_or_hocr(image, extension='pdf', out_file=str(pdf_path))

                    try:
                        print("IMAGE TEXT:")
                        print(text[:1000])
                    except UnicodeEncodeError:
                        print("IMAGE TEXT: (unable to display due to encoding issues)")

                    return {"text": text}
                except Exception as e:
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error processing image with Tesseract: {str(e)}"
                    )
            else:
                # For non-PDF, non-image files, try to decode as text
                try:
                    text = content.decode('utf-8')
                    print("FILE TEXT:")
                    print(text[:1000])
                    return {"text": text}
                except UnicodeDecodeError:
                    raise HTTPException(
                        status_code=400,
                        detail="File appears to be neither an image, PDF, nor text file"
                    )

    except requests.RequestException as e:
        raise HTTPException(status_code=400, detail=f"Error downloading file: {str(e)}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "healthy"}
