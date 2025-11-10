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

# Add current directory to path for relative imports
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import azure.functions as func
from .supplier_id_service import identify_supplier
from .katoomba_extractor import extract_katoomba_fields
from .ai_prompt_service import extract_with_ai


def custom_json_serializer(obj):
    """Custom JSON serializer for objects not serializable by default json code"""
    if isinstance(obj, (datetime, date)):
        return obj.isoformat()
    raise TypeError(f"Object of type {obj.__class__.__name__} is not JSON serializable")


def main(jsonBlob: func.InputStream, outputBlob: func.Out[str]):
    logging.info(f"Processing OCR JSON blob: {jsonBlob.name}")
    
    try:
        # Read the OCR JSON data
        json_content = jsonBlob.read().decode('utf-8')
        ocr_json = json.loads(json_content)
        
        logging.info(f"Loaded OCR JSON data for processing")

        # Step 2: Supplier identification
        supplier = identify_supplier(ocr_json)
        logging.info(f"Identified supplier: {supplier}")

        # Step 3: Supplier-specific extraction
        if supplier == "KATOOMBA":
            invoice_data = extract_katoomba_fields(ocr_json)
        else:
            # Fallback to AI prompt engineering
            invoice_data = extract_with_ai(ocr_json, supplier)

        # Step 4: Output processed JSON with custom serializer
        try:
            output_json = json.dumps(invoice_data, default=custom_json_serializer, indent=2)
            outputBlob.set(output_json)
            logging.info("Invoice processing complete and output written.")
        except Exception as e:
            logging.error(f"Error serializing output JSON: {e}")
            # Fallback: convert problematic objects to strings
            fallback_data = json.loads(json.dumps(invoice_data, default=str, indent=2))
            outputBlob.set(json.dumps(fallback_data, indent=2))
            logging.info("Invoice processing complete with fallback serialization.")
            
    except Exception as e:
        logging.error(f"Error processing OCR JSON: {e}")
        # Output error information
        error_output = {
            "error": str(e),
            "status": "failed",
            "blob_name": jsonBlob.name
        }
        outputBlob.set(json.dumps(error_output, indent=2))