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
from pdfminer.high_level import extract_text, extract_text_to_fp
import pytesseract
from PIL import Image
import io
import imghdr
import traceback
import logging
import magic
from pdfminer.layout import LAParams
from io import StringIO
import PyPDF2

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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

def get_mime_type(content: bytes) -> str:
    """Detect MIME type of content using python-magic"""
    try:
        mime = magic.Magic(mime=True)
        return mime.from_buffer(content)
    except Exception as e:
        logger.error(f"Error detecting MIME type: {str(e)}")
        return None

def is_image_content(content: bytes) -> bool:
    """Detect if content is an image using MIME type and PIL"""
    try:
        mime_type = get_mime_type(content)
        if mime_type and mime_type.startswith('image/'):
            # Verify we can open it with PIL
            image = Image.open(io.BytesIO(content))
            image.verify()  # Verify it's a valid image
            return True
        return False
    except Exception as e:
        logger.error(f"Error checking if content is image: {str(e)}")
        return False

def is_pdf_content(content: bytes) -> bool:
    """Detect if content is a PDF using MIME type"""
    try:
        mime_type = get_mime_type(content)
        return mime_type == 'application/pdf'
    except Exception as e:
        logger.error(f"Error checking if content is PDF: {str(e)}")
        return content.startswith(b'%PDF')  # Fallback to magic number check

@app.get("/process-document")
async def process_document(
    request: Request, 
    url: str = None, 
    max_chars: int = 1000,  # Default to processing until we get 1000 characters
    api_key: str = Depends(get_api_key)
):
    # Debug information
    logger.info(f"Processing document from URL: {url}")
    logger.info(f"Query Params: {dict(request.query_params)}")
    logger.info(f"Headers: {dict(request.headers)}")

    if not url:
        raise HTTPException(status_code=422, detail="URL parameter is required")

    try:
        # Download the file with timeout and proper headers
        logger.info(f"Downloading file from URL: {url}")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=30, stream=True)
        response.raise_for_status()

        # Read content in chunks to handle large files
        content = b''
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                content += chunk

        logger.info(f"Successfully downloaded file, size: {len(content)} bytes")

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Downloaded file is empty")

        # Create temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            input_file = temp_path / "input_file"
            logger.info(f"Created temporary directory: {temp_dir}")

            # Save downloaded file
            with open(input_file, "wb") as f:
                f.write(content)
            logger.info("Saved downloaded file")

            # Get MIME type
            mime_type = get_mime_type(content)
            logger.info(f"Detected MIME type: {mime_type}")

            # Process based on content type
            if is_pdf_content(content):
                logger.info("Processing as PDF")
                output_file = temp_path / "output.pdf"

                try:
                    # For PDFs, we'll process page by page until we get enough text
                    logger.info(f"Processing PDF until we get {max_chars} characters")
                    

                    
                    # First, get the total number of pages
                    with open(input_file, 'rb') as f:
                        pdf_reader = PyPDF2.PdfReader(f)
                        total_pages = len(pdf_reader.pages)
                    
                    logger.info(f"PDF has {total_pages} pages, processing incrementally")
                    
                    # Process pages one by one until we have enough text
                    collected_text = ""
                    pages_processed = 0
                    
                    for page_num in range(min(total_pages, 10)):  # Limit to first 10 pages max for safety
                        pages_processed += 1
                        
                        # Process just this page with OCR
                        page_output = temp_path / f"output_page_{page_num+1}.pdf"
                        
                        try:
                            # Use string format for page ranges as per ocrmypdf documentation
                            ocrmypdf.ocr(
                                input_file,
                                page_output,
                                force_ocr=True,
                                output_type='pdf',
                                progress_bar=False,
                                pages=f"{page_num+1}"  # 1-based page numbering as string
                            )
                            
                            # Extract text from just this page
                            output_string = StringIO()
                            with open(str(page_output), 'rb') as fin:
                                extract_text_to_fp(fin, output_string, laparams=LAParams())
                            page_text = output_string.getvalue()
                            
                            # Add to our collected text
                            collected_text += page_text
                            
                            logger.info(f"Processed page {page_num+1}, text length now: {len(collected_text)}")
                            
                            # If we have enough text, stop processing
                            if len(collected_text) >= max_chars:
                                logger.info(f"Reached {len(collected_text)} characters after {pages_processed} pages, stopping")
                                break
                                
                        except Exception as e:
                            logger.warning(f"Error processing page {page_num+1}: {str(e)}")
                            # Continue with next page if one fails
                    
                    # Truncate to exactly max_chars if we have more
                    if len(collected_text) > max_chars:
                        final_text = collected_text[:max_chars]
                        truncated = True
                    else:
                        final_text = collected_text
                        truncated = False
                    
                    if not final_text.strip():
                        logger.warning("No text extracted from PDF")
                        return {"text": "", "warning": "No text could be extracted from the PDF"}
                    
                    response = {
                        "text": final_text,
                        "pages_processed": pages_processed,
                        "total_pages": total_pages
                    }
                    
                    if truncated:
                        response["truncated"] = True
                    
                    logger.info(f"Finished processing PDF. Processed {pages_processed} of {total_pages} pages.")
                    return response
                except Exception as e:
                    logger.error(f"Error during PDF processing: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error processing PDF: {str(e)}"
                    )

            elif is_image_content(content):
                logger.info("Processing as image")
                try:
                    # Open image using PIL
                    image = Image.open(io.BytesIO(content))
                    logger.info(f"Image opened successfully. Format: {image.format}, Size: {image.size}")

                    # Convert image to RGB if necessary
                    if image.mode not in ('L', 'RGB'):
                        image = image.convert('RGB')
                        logger.info("Converted image to RGB mode")

                    # Convert image to text using Tesseract
                    logger.info("Starting Tesseract OCR")
                    text = pytesseract.image_to_string(image)

                    if not text.strip():
                        logger.warning("No text extracted from image")
                        return {"text": "", "warning": "No text could be extracted from the image"}

                    logger.info("Tesseract OCR completed")
                    return {"text": text}
                except Exception as e:
                    logger.error(f"Error processing image: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise HTTPException(
                        status_code=500,
                        detail=f"Error processing image with Tesseract: {str(e)}"
                    )
            else:
                logger.info(f"Unsupported content type: {mime_type}")
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {mime_type}. Only PDF and image files are supported."
                )

    except requests.RequestException as e:
        logger.error(f"Error downloading file: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Error downloading file: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"Error processing document: {str(e)}")

@app.get("/health", status_code=200)
async def health_check():
    return {"status": "healthy"}
