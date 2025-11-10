import os
import sys
import logging
import re

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to PDFTOJSON2FunctionApp
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

def identify_supplier(ocr_json):
    """Identify supplier from OCR JSON data"""
    try:
        content = ocr_json.get("content", "").upper()
        fields = ocr_json.get("fields", {})
        
        # Get vendor name from structured fields first
        vendor_name = ""
        documents = ocr_json.get('documents', [])
        if documents:
            header = documents[0].get('fields', {})
            vendor_field = header.get('VendorName', {})
            if vendor_field and 'value' in vendor_field:
                vendor_name = str(vendor_field['value']).upper()
        
        # Check for Katoomba patterns in structured fields
        if vendor_name and any(pattern in vendor_name for pattern in ['KATOOMBA', 'KG FOODS']):
            logging.info(f"Identified KATOOMBA from vendor field: {vendor_name}")
            return 'KATOOMBA'
        
        # Check for Katoomba patterns in raw content
        katoomba_patterns = [
            r'KATOOMBA\s*GLOBAL\s*FOODS',
            r'KG\s*FOODS',
            r'KATOOMBA',
            # Add ABN or other identifying patterns here
        ]
        
        for pattern in katoomba_patterns:
            if re.search(pattern, content):
                logging.info(f"Identified KATOOMBA using pattern: {pattern}")
                return 'KATOOMBA'
        
        # Add more supplier identification logic here for other suppliers
        # Example:
        # if 'SUPPLIER_NAME' in content:
        #     return 'SUPPLIER_CODE'
        
        logging.info("Could not identify specific supplier, using UNKNOWN")
        return 'UNKNOWN'
        
    except Exception as e:
        logging.error(f"Error identifying supplier: {e}")
        return 'UNKNOWN'