import logging
import os
import json
import azure.functions as func
from .ocr_service import extract_text_and_fields
from .supplier_id_service import identify_supplier
from .katoomba_extractor import extract_katoomba_fields
from .ai_prompt_service import extract_with_ai

BLOB_OUTPUT_CONTAINER = os.getenv('BLOB_OUTPUT_CONTAINER')


def main(blob: func.InputStream, outputBlob: func.Out[str]):
    logging.info(f"Processing blob: {blob.name}, Size: {blob.length} bytes")
    pdf_bytes = blob.read()

    # Step 1: OCR and initial field extraction
    ocr_json = extract_text_and_fields(pdf_bytes)
    logging.info(f"OCR JSON: {json.dumps(ocr_json)[:500]}")

    # Step 2: Supplier identification
    supplier = identify_supplier(ocr_json)
    logging.info(f"Identified supplier: {supplier}")

    # Step 3: Supplier-specific extraction
    if supplier == "KATOOMBA":
        invoice_data = extract_katoomba_fields(ocr_json)
    else:
        # Fallback to AI prompt engineering
        invoice_data = extract_with_ai(ocr_json, supplier)

    # Step 4: Output JSON
    outputBlob.set(json.dumps(invoice_data, indent=2))
    logging.info("Extraction complete and output written.")
