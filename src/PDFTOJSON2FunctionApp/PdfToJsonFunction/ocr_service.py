import os
import sys

# Add the virtual environment packages to the Python path
function_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to PDFTOJSON2FunctionApp

# Try .venv first (more reliable for Azure Functions)
venv_path = os.path.join(function_app_root, '.venv', 'Lib', 'site-packages')
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')

# Add paths in order of preference
paths_to_add = [venv_path, python_packages_path]
for path in paths_to_add:
    if os.path.exists(path) and path not in sys.path:
        sys.path.insert(0, path)

import logging

# Debug information
logging.info(f"Function app root: {function_app_root}")
logging.info(f"Venv path exists: {os.path.exists(venv_path)}")
logging.info(f"Python packages path exists: {os.path.exists(python_packages_path)}")

# Try to import Azure modules
try:
    from azure.ai.formrecognizer import DocumentAnalysisClient
    from azure.core.credentials import AzureKeyCredential
    logging.info("✅ Azure modules imported successfully from virtual environment!")
    
except ImportError as e:
    logging.error(f"❌ Import error: {e}")
    
    # List what's actually available for debugging
    for path in paths_to_add:
        if os.path.exists(path):
            logging.info(f"Checking path: {path}")
            try:
                azure_path = os.path.join(path, 'azure')
                if os.path.exists(azure_path):
                    azure_contents = os.listdir(azure_path)
                    logging.info(f"Azure contents in {path}: {azure_contents}")
            except Exception as list_error:
                logging.error(f"Error listing {path}: {list_error}")
    
    raise ImportError(f"Cannot import Azure modules. Error: {e}")

import io
import json

def extract_text_and_fields(pdf_bytes):
    """Extract text and fields from PDF using Azure Document Intelligence"""
    try:
        endpoint = os.getenv("AZURE_FORM_RECOGNIZER_ENDPOINT") or os.getenv("DOCUMENT_INTELLIGENCE_ENDPOINT")
        key = os.getenv("AZURE_FORM_RECOGNIZER_KEY") or os.getenv("DOCUMENT_INTELLIGENCE_API_KEY")
        
        if not endpoint or not key:
            logging.error("Azure Form Recognizer/Document Intelligence endpoint and key must be provided")
            raise ValueError("Azure Form Recognizer/Document Intelligence endpoint and key must be provided")
        
        logging.info(f"Using endpoint: {endpoint[:50]}...")
        
        client = DocumentAnalysisClient(endpoint=endpoint, credential=AzureKeyCredential(key))
        
        # Convert bytes to BytesIO if needed
        if isinstance(pdf_bytes, bytes):
            pdf_stream = io.BytesIO(pdf_bytes)
        else:
            pdf_stream = pdf_bytes
        
        logging.info("Starting document analysis...")
        
        # Use the prebuilt invoice model for better field extraction
        poller = client.begin_analyze_document("prebuilt-invoice", pdf_stream)
        result = poller.result()
        
        extracted_data = {
            "content": result.content,
            "pages": [],
            "tables": [],
            "fields": {},
            "extraction_metadata": {
                "model_used": "prebuilt-invoice",
                "api_version": "2023-07-31"
            }
        }
        
        # Extract page content
        for page in result.pages:
            page_data = {
                "page_number": page.page_number,
                "lines": [line.content for line in page.lines],
                "words": [{"content": word.content, "confidence": getattr(word, 'confidence', None)} for word in page.words]
            }
            extracted_data["pages"].append(page_data)
        
        # Extract tables
        for table in result.tables:
            table_data = {
                "row_count": table.row_count,
                "column_count": table.column_count,
                "cells": []
            }
            for cell in table.cells:
                cell_data = {
                    "content": cell.content,
                    "row_index": cell.row_index,
                    "column_index": cell.column_index,
                    "confidence": getattr(cell, 'confidence', None)  # Handle missing confidence attribute
                }
                table_data["cells"].append(cell_data)
            extracted_data["tables"].append(table_data)
        
        # Extract fields (for invoices)
        if result.documents:
            for document in result.documents:
                for name, field in document.fields.items():
                    if field.value:
                        extracted_data["fields"][name] = {
                            "value": field.value,
                            "confidence": getattr(field, 'confidence', None)
                        }
        
        logging.info(f"OCR extraction completed successfully. Found {len(extracted_data['pages'])} pages, {len(extracted_data['tables'])} tables, {len(extracted_data['fields'])} fields")
        return extracted_data
        
    except Exception as e:
        logging.error(f"Error in OCR extraction: {e}")
        return {"error": str(e), "content": "", "pages": [], "tables": [], "fields": {}}