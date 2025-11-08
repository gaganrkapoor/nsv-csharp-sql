# PDFToJSON2FunctionApp

This project is a Python Azure Function App that processes PDF invoices from a blob storage container, extracts invoice header and line item fields using Azure Document Intelligence and Azure OpenAI, and outputs structured JSON to another blob container. It supports supplier-specific extraction logic and prompt engineering for flexible field extraction.

## Features
- Blob-triggered invoice processing
- OCR and structured field extraction using Azure Document Intelligence
- Supplier identification and supplier-specific extraction logic
- Prompt engineering with Azure OpenAI for advanced extraction
- Outputs invoice header and line items as JSON
- Easily extensible for new suppliers

## Project Structure
- `__init__.py` - Main function entry point
- `ocr_service.py` - Handles OCR and field extraction
- `supplier_id_service.py` - Identifies supplier from invoice
- `katoomba_extractor.py` - Supplier-specific extraction logic (example)
- `ai_prompt_service.py` - Handles prompt engineering with Azure OpenAI
- `models.py` - Data models for invoice header and lines
- `utils.py` - Utility functions

## Setup
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Configure `local.settings.json` with your Azure resources.
3. Start the function app:
   ```bash
   func start
   ```

## Adding New Suppliers
- Add a new extractor in the `extractors/` directory and register it in the main function.

## Environment Variables
See `local.settings.json` for required configuration keys.
