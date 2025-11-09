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
from ocr_service import extract_text_and_fields
from supplier_id_service import identify_supplier
from katoomba_extractor import extract_katoomba_fields
from ai_prompt_service import extract_with_ai

BLOB_OUTPUT_CONTAINER = os.getenv('BLOB_OUTPUT_CONTAINER')


def custom_json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def main(blob: func.InputStream, outputBlob: func.Out[str]):
    logging.info(f"Processing blob: {blob.name}, Size: {blob.length} bytes")
    pdf_bytes = blob.read()

    # Step 1: OCR and initial field extraction
    ocr_json = extract_text_and_fields(pdf_bytes)
    
    # Log OCR JSON safely with custom serializer
    try:
        ocr_preview = json.dumps(ocr_json, default=custom_json_serializer)[:500]
        logging.info(f"OCR JSON: {ocr_preview}")
    except Exception as e:
        logging.warning(f"Could not serialize OCR JSON for logging: {e}")
        logging.info("OCR extraction completed successfully")

    # Step 2: Supplier identification
    supplier = identify_supplier(ocr_json)
    logging.info(f"Identified supplier: {supplier}")

    # Step 3: Supplier-specific extraction
    if supplier == "KATOOMBA":
        invoice_data = extract_katoomba_fields(ocr_json)
    else:
        # Fallback to AI prompt engineering
        invoice_data = extract_with_ai(ocr_json, supplier)

    # Step 4: Output JSON with custom serializer
    try:
        output_json = json.dumps(invoice_data, default=custom_json_serializer, indent=2)
        outputBlob.set(output_json)
        logging.info("Extraction complete and output written.")
    except Exception as e:
        logging.error(f"Error serializing output JSON: {e}")
        # Fallback: convert problematic objects to strings
        fallback_data = json.loads(json.dumps(invoice_data, default=str, indent=2))
        outputBlob.set(json.dumps(fallback_data, indent=2))
        logging.info("Extraction complete with fallback serialization.")
