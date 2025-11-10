# Invoice Processing Pipeline

This Azure Function App processes PDF invoices through a multi-stage pipeline that extracts data using Azure Document Intelligence and AI-powered supplier-specific processing.

## Architecture Overview

### Containers

1. **invoices** - Input container for PDF invoice files
2. **invoice-json** - Intermediate container storing OCR extracted JSON data  
3. **invoice-json-templates** - Template definitions for supplier-specific extraction rules
4. **processed-invoices** - Final output container with processed invoice data

### Functions

1. **PdfToJsonFunction** - Triggered by PDF files in `invoices` container
   - Performs OCR extraction using Azure Document Intelligence
   - Saves raw OCR JSON to `invoice-json` container
   - Continues processing for complete pipeline

2. **ProcessInvoiceJsonFunction** - Triggered by JSON files in `invoice-json` container  
   - Identifies supplier from OCR data
   - Applies supplier-specific extraction rules
   - Uses AI fallback for unknown suppliers
   - Saves processed data to `processed-invoices` container

## Processing Pipeline

```
PDF Invoice → OCR Extraction → Supplier ID → Specific Processing → Final JSON
    ↓              ↓              ↓              ↓                ↓
  invoices    invoice-json    (logic)      AI/Rules        processed-invoices
```

## Configuration

### Environment Variables

- `BLOB_INPUT_CONTAINER` - "invoices"
- `INVOICE_JSON_CONTAINER` - "invoice-json" 
- `INVOICE_JSON_TEMPLATES_CONTAINER` - "invoice-json-templates"
- `BLOB_OUTPUT_CONTAINER` - "processed-invoices"
- `AZURE_FORM_RECOGNIZER_ENDPOINT` - Azure Document Intelligence endpoint
- `AZURE_FORM_RECOGNIZER_KEY` - Azure Document Intelligence key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_OPENAI_KEY` - Azure OpenAI key
- `AZURE_OPENAI_DEPLOYMENT` - GPT model deployment name

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
