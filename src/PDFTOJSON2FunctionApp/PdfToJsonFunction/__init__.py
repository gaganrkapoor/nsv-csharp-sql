import logging
import os
import json
import sys
from datetime import date, datetime

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)
sys.path.append(function_app_root)

import azure.functions as func
from .ocr_service import extract_text_and_fields

BLOB_OUTPUT_CONTAINER = os.getenv('BLOB_OUTPUT_CONTAINER')


def custom_json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def main(blob: func.InputStream, ocrJsonBlob: func.Out[str]):
    logging.info(f"Processing PDF blob: {blob.name}, Size: {blob.length} bytes")
    pdf_bytes = blob.read()

    # Step 1: OCR and initial field extraction only
    ocr_json = extract_text_and_fields(pdf_bytes)
    
    # Save OCR JSON to intermediate container for ProcessInvoiceJSONFunction
    try:
        ocr_json_output = json.dumps(ocr_json, default=custom_json_serializer, indent=2)
        ocrJsonBlob.set(ocr_json_output)
        logging.info("OCR JSON saved to intermediate container")
    except Exception as e:
        logging.error(f"Error saving OCR JSON: {e}")
        # Fallback: convert problematic objects to strings
        fallback_ocr_data = json.loads(json.dumps(ocr_json, default=str, indent=2))
        ocrJsonBlob.set(json.dumps(fallback_ocr_data, indent=2))
        logging.info("OCR JSON saved with fallback serialization")
    
    # Log OCR JSON safely with custom serializer
    try:
        ocr_preview = json.dumps(ocr_json, default=custom_json_serializer)[:500]
        logging.info(f"OCR JSON preview: {ocr_preview}")
    except Exception as e:
        logging.warning(f"Could not serialize OCR JSON for logging: {e}")
        logging.info("OCR extraction completed successfully")
