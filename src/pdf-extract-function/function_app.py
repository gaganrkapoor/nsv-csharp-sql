import logging
import os
import time
import json
import requests
from azure.storage.blob import BlobServiceClient
import azure.functions as func

# Import our vector service
try:
    from vector_service import VectorService
    VECTOR_SERVICE_AVAILABLE = True
    logging.info("Vector service imported successfully")
except ImportError as e:
    VECTOR_SERVICE_AVAILABLE = False
    logging.warning(f"Vector service not available: {e}")

app = func.FunctionApp()

# Initialize vector service (global to persist across function calls)
vector_service = None
if VECTOR_SERVICE_AVAILABLE:
    try:
        vector_service = VectorService()
        logging.info("Vector service initialized successfully")
    except Exception as e:
        logging.error(f"Failed to initialize vector service: {e}")
        vector_service = None

@app.function_name(name="PdfExtractFunction")
@app.blob_trigger(arg_name="pdfblob", path="invoices/{name}", connection="AzureWebJobsStorage")
def pdf_extract_function(pdfblob: func.InputStream):
    """
    PDF extraction function that processes files uploaded to the configured input container.
    
    Note: The blob trigger path is hardcoded to 'invoices/{name}' due to Azure Functions limitations,
    but the actual container name used for processing is configurable via INVOICES_CONTAINER_NAME.
    Ensure the Key Vault secret INVOICES-CONTAINER matches the trigger path.
    """
    logging.info(f"Triggered by blob: {pdfblob.name}")

    # === Environment Variables ===
    endpoint = os.environ["FORM_RECOGNIZER_ENDPOINT"].rstrip('/')  # Remove trailing slash
    api_key = os.environ["FORM_RECOGNIZER_KEY"]
    
    # Determine invoice format first to select appropriate model
    invoice_format = determine_pdf_type(pdfblob.name.split("/")[-1])
    model_id = get_model_for_invoice_format(invoice_format)
    
    logging.info(f"Detected invoice format: {invoice_format}, Using model: {model_id}")
    
    # Read all container names from environment variables (sourced from Key Vault)
    input_container = os.environ["INVOICES_CONTAINER_NAME"]  # "invoices"
    output_container = os.environ["INVOICES_JSON_CONTAINER_NAME"]  # "invoices-json"
    processed_container = os.environ["PROCESSED_INVOICES_CONTAINER_NAME"]  # "processed-invoices"
    
    storage_connection = os.environ["AzureWebJobsStorage"]

    # Log container configuration for debugging
    logging.info(f"Container configuration - Input: {input_container}, Output: {output_container}, Processed: {processed_container}")

    # === Connect to Azure Blob storage ===
    blob_service_client = BlobServiceClient.from_connection_string(storage_connection)
    container_name = input_container  # Use configurable container name instead of hardcoded "invoices"
    blob_name = pdfblob.name.split("/")[-1]
    blob_client = blob_service_client.get_blob_client(container=container_name, blob=blob_name)

    logging.info(f"Processing PDF: {blob_name}")

    # === Call the custom model ===
    analyze_url = f"{endpoint}/documentintelligence/documentModels/{model_id}:analyze?api-version=2024-11-30"
    logging.info(f"Calling Document Intelligence API: {analyze_url}")
    
    # Read the PDF content directly instead of using SAS URL (since Azurite is local)
    pdf_content = pdfblob.read()
    logging.info(f"PDF size: {len(pdf_content)} bytes")
    
    headers = {
        "Ocp-Apim-Subscription-Key": api_key,
        "Content-Type": "application/pdf"
    }
    
    try:
        response = requests.post(analyze_url, headers=headers, data=pdf_content)
        logging.info(f"Response status: {response.status_code}")
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        # Enhanced diagnostics for all HTTP errors
        logging.error(f"HTTP Error: {e}")
        logging.error(f"Response status: {response.status_code}")
        logging.error(f"Response headers: {dict(response.headers)}")
        logging.error(f"Response content: {response.text}")

        if response.status_code == 400:
            logging.error("400 Bad Request - likely issue with request format, SAS URL, or API parameters")
            
        elif response.status_code == 404:
            # Try to fetch model info
            try:
                model_info_url = f"{endpoint}/documentintelligence/documentModels/{model_id}?api-version=2024-11-30"
                logging.error(f"Fetching model info: {model_info_url}")
                model_info = requests.get(model_info_url, headers={"Ocp-Apim-Subscription-Key": api_key})
                logging.error(f"Model info status: {model_info.status_code}")
                logging.error(f"Model info content: {model_info.text}")
            except Exception as inner_e:
                logging.error(f"Failed to fetch model info: {inner_e}")

            # Try to list available models
            try:
                list_url = f"{endpoint}/documentintelligence/documentModels?api-version=2024-11-30"
                logging.error(f"Listing models: {list_url}")
                list_resp = requests.get(list_url, headers={"Ocp-Apim-Subscription-Key": api_key})
                logging.error(f"List models status: {list_resp.status_code}")
                logging.error(f"List models content: {list_resp.text}")
            except Exception as inner_e:
                logging.error(f"Failed to list models: {inner_e}")

            logging.error("404 returned from analyze - verify that the model ID, endpoint and key are correct and that the model exists on the specified resource.")

        # Re-raise original exception so function host registers failure
        raise

    # Get operation URL
    operation_url = response.headers["operation-location"]

    # === Poll for result ===
    result = None
    for i in range(15):
        poll = requests.get(operation_url, headers={"Ocp-Apim-Subscription-Key": api_key})
        data = poll.json()
        if data.get("status") == "succeeded":
            result = data
            break
        elif data.get("status") in ["failed", "invalid"]:
            logging.error(f"Model analysis failed: {data}")
            return
        time.sleep(2)

    # === Extract only your custom fields ===
    if result and "analyzeResult" in result:
        extracted_fields = result["analyzeResult"].get("documents", [])[0].get("fields", {})
        logging.info(f"Extracted fields: {json.dumps(extracted_fields, indent=2)}")
        
        # Normalize invoice fields based on format
        normalized_fields = extract_invoice_fields(extracted_fields, invoice_format)
        logging.info(f"Normalized invoice fields: {json.dumps(normalized_fields, indent=2)}")

        # Save both raw and normalized data to output container
        output_data = {
            "raw_extraction": extracted_fields,
            "normalized_fields": normalized_fields,
            "invoice_format": invoice_format,
            "model_used": model_id
        }

        output_client = blob_service_client.get_blob_client(
            container=output_container,
            blob=blob_name.replace(".pdf", ".json")
        )
        output_client.upload_blob(json.dumps(output_data, indent=2), overwrite=True)
        logging.info(f"✅ Saved extracted fields to {output_container}/{blob_name.replace('.pdf', '.json')}")

        # === NEW: Store in Vector Database ===
        if vector_service:
            try:
                # Store document in vector database with normalized fields
                document_id = vector_service.store_document_vector(
                    pdf_filename=blob_name,
                    extracted_json=normalized_fields,  # Use normalized fields for better search
                    pdf_type=invoice_format
                )
                
                logging.info(f"✅ Stored document in vector database with ID: {document_id}")
                
            except Exception as e:
                logging.error(f"❌ Failed to store in vector database: {e}")
                # Don't fail the entire function if vector storage fails
        else:
            logging.warning("⚠️ Vector service not available, skipping vector storage")


def get_model_for_invoice_format(invoice_format):
    """
    Select the appropriate Document Intelligence model based on invoice format.
    Can be customized to use specialized models for specific supplier formats.
    """
    # Model mapping for different invoice types
    model_mapping = {
        "katoomba": "prebuilt-invoice",  # Could use custom model if trained
        "woolworths": "prebuilt-invoice",  # Could use custom model if trained
        "coles": "prebuilt-invoice",
        "telstra": "prebuilt-invoice",
        "optus": "prebuilt-invoice",
        "commonwealth_bank": "prebuilt-invoice",
        "westpac": "prebuilt-invoice",
        "anz": "prebuilt-invoice",
        "nab": "prebuilt-invoice",
        "office_depot": "prebuilt-invoice",
        "generic": "prebuilt-invoice"  # fallback
    }
    
    return model_mapping.get(invoice_format, "prebuilt-invoice")


def determine_pdf_type(filename: str) -> str:
    """
    Determine invoice format type from filename
    All documents are invoices, but from different suppliers/formats
    """
    filename_lower = filename.lower()
    
    # Invoice format detection for 38-40 different invoice formats
    invoice_format_mapping = {
        # Supplier-specific invoice formats
        'katoomba': ['katoomba', 'sbonfacp', 'jobrpt'],
        'woolworths': ['woolworths', 'wwl', 'safeway'],
        'coles': ['coles', 'cole', 'supermarket'],
        'aldi': ['aldi', 'discount'],
        'bunnings': ['bunnings', 'warehouse'],
        'officeworks': ['officeworks', 'office'],
        'kmart': ['kmart', 'retail'],
        'target': ['target', 'tgt'],
        'big_w': ['bigw', 'big_w'],
        'jb_hifi': ['jbhifi', 'jb_hifi', 'electronics'],
        'harvey_norman': ['harvey', 'norman', 'electrical'],
        'officeworks': ['officeworks', 'stationery'],
        'chemist_warehouse': ['chemist', 'pharmacy', 'cwh'],
        'priceline': ['priceline', 'pharmacy'],
        'spotlight': ['spotlight', 'craft'],
        'super_cheap': ['supercheap', 'automotive'],
        'mitre10': ['mitre10', 'hardware'],
        'masters': ['masters', 'home'],
        'ikea': ['ikea', 'furniture'],
        'fantastic_furniture': ['fantastic', 'furniture'],
        'amart': ['amart', 'furniture'],
        'bcf': ['bcf', 'boating', 'camping'],
        'rebel_sport': ['rebel', 'sport'],
        'anaconda': ['anaconda', 'outdoor'],
        'ray_white': ['raywhite', 'realestate'],
        'lj_hooker': ['ljhooker', 'hooker'],
        'century21': ['century21', 'c21'],
        'telstra': ['telstra', 'telecom'],
        'optus': ['optus', 'mobile'],
        'vodafone': ['vodafone', 'voda'],
        'origin': ['origin', 'energy'],
        'agl': ['agl', 'australian_gas'],
        'energyaustralia': ['energyaustralia', 'ea'],
        'ausgrid': ['ausgrid', 'electricity'],
        'sydney_water': ['sydneywater', 'water'],
        'council': ['council', 'rates', 'municipal'],
        'taxation_office': ['ato', 'taxation', 'tax_office'],
        'centrelink': ['centrelink', 'services_australia'],
        'medicare': ['medicare', 'health'],
        'nrma': ['nrma', 'insurance'],
        # Generic invoice patterns as fallback
        'standard_tax_invoice': ['tax_invoice', 'invoice', 'inv'],
        'receipt': ['receipt', 'rcpt'],
        'statement': ['statement', 'stmt'],
        'bill': ['bill', 'billing'],
        'purchase_order': ['purchase_order', 'po_'],
        'credit_note': ['credit_note', 'cn_'],
        'debit_note': ['debit_note', 'dn_'],
    }
    
    # Check for specific invoice format first
    for invoice_format, keywords in invoice_format_mapping.items():
        if any(keyword in filename_lower for keyword in keywords):
            return invoice_format
    
    # Default to generic invoice type if no specific format detected
    return 'generic_invoice'


def get_model_for_invoice_format(invoice_format: str) -> str:
    """Get appropriate Document Intelligence model for specific invoice format"""
    
    # Model mapping for different invoice formats
    invoice_model_mapping = {
        # Custom trained models for specific suppliers
        'katoomba': 'kt-model-1',  # Your existing custom model
        
        # Prebuilt models for standard invoices
        'woolworths': 'prebuilt-invoice',
        'coles': 'prebuilt-invoice', 
        'aldi': 'prebuilt-invoice',
        'bunnings': 'prebuilt-invoice',
        'standard_tax_invoice': 'prebuilt-invoice',
        'receipt': 'prebuilt-receipt',
        'bill': 'prebuilt-invoice',
        
        # Utility bills might need document model
        'telstra': 'prebuilt-document',
        'optus': 'prebuilt-document',
        'origin': 'prebuilt-document',
        'agl': 'prebuilt-document',
        'sydney_water': 'prebuilt-document',
        'council': 'prebuilt-document',
        
        # Government documents
        'taxation_office': 'prebuilt-document',
        'centrelink': 'prebuilt-document',
        'medicare': 'prebuilt-document',
    }
    
    # Return specific model or default to prebuilt-invoice
    return invoice_model_mapping.get(invoice_format, 'prebuilt-invoice')


def extract_invoice_fields(extracted_fields: dict, invoice_format: str) -> dict:
    """
    Extract and normalize key invoice fields based on format
    Returns standardized invoice data structure
    """
    
    # Standard invoice fields we want to extract
    normalized_invoice = {
        'supplier': {
            'name': None,
            'abn': None,
            'address': None,
            'contact': None
        },
        'invoice_details': {
            'invoice_number': None,
            'invoice_date': None,
            'due_date': None,
            'purchase_order': None
        },
        'customer': {
            'name': None,
            'address': None
        },
        'line_items': [],
        'totals': {
            'subtotal': None,
            'total_discount': None,
            'total_gst': None,
            'total_amount': None
        },
        'payment_terms': None,
        'invoice_format': invoice_format
    }
    
    # Format-specific field extraction logic
    if invoice_format == 'katoomba':
        # Your custom Katoomba invoice extraction
        normalized_invoice = extract_katoomba_fields(extracted_fields)
    elif invoice_format in ['woolworths', 'coles', 'aldi']:
        # Retail invoice extraction
        normalized_invoice = extract_retail_invoice_fields(extracted_fields)
    elif invoice_format in ['telstra', 'optus', 'vodafone']:
        # Telecom bill extraction  
        normalized_invoice = extract_telecom_bill_fields(extracted_fields)
    elif invoice_format in ['origin', 'agl', 'energyaustralia']:
        # Utility bill extraction
        normalized_invoice = extract_utility_bill_fields(extracted_fields)
    else:
        # Generic invoice extraction
        normalized_invoice = extract_generic_invoice_fields(extracted_fields)
    
    return normalized_invoice


def extract_katoomba_fields(fields: dict) -> dict:
    """Extract fields specific to Katoomba invoice format"""
    # Implement your existing Katoomba extraction logic here
    return {
        'supplier': {
            'name': fields.get('SupplierName', {}).get('content'),
            'abn': fields.get('SupplierABN', {}).get('content'),
            'address': fields.get('SupplierAddress', {}).get('content')
        },
        'invoice_details': {
            'invoice_number': fields.get('InvoiceNumber', {}).get('content'),
            'invoice_date': fields.get('InvoiceDate', {}).get('content'),
            'due_date': fields.get('DueDate', {}).get('content')
        },
        'line_items': fields.get('LineItems', []),
        'totals': {
            'subtotal': fields.get('Subtotal', {}).get('content'),
            'total_gst': fields.get('TotalGST', {}).get('content'),
            'total_amount': fields.get('TotalAmount', {}).get('content')
        }
    }


def extract_generic_invoice_fields(fields: dict) -> dict:
    """Extract fields from generic invoice using prebuilt-invoice model"""
    return {
        'supplier': {
            'name': fields.get('VendorName', {}).get('content'),
            'address': fields.get('VendorAddress', {}).get('content')
        },
        'invoice_details': {
            'invoice_number': fields.get('InvoiceId', {}).get('content'),
            'invoice_date': fields.get('InvoiceDate', {}).get('content'),
            'due_date': fields.get('DueDate', {}).get('content')
        },
        'customer': {
            'name': fields.get('CustomerName', {}).get('content'),
            'address': fields.get('CustomerAddress', {}).get('content')
        },
        'totals': {
            'subtotal': fields.get('SubTotal', {}).get('content'),
            'total_amount': fields.get('InvoiceTotal', {}).get('content'),
            'total_gst': fields.get('TotalTax', {}).get('content')
        }
    }


def extract_retail_invoice_fields(fields: dict) -> dict:
    """Extract fields from retail invoices (Woolworths, Coles, etc.)"""
    # Implement retail-specific extraction
    return extract_generic_invoice_fields(fields)


def extract_telecom_bill_fields(fields: dict) -> dict:
    """Extract fields from telecom bills (Telstra, Optus, etc.)"""
    # Implement telecom-specific extraction
    return extract_generic_invoice_fields(fields)


def extract_utility_bill_fields(fields: dict) -> dict:
    """Extract fields from utility bills (Origin, AGL, etc.)"""
    # Implement utility-specific extraction
    return extract_generic_invoice_fields(fields)


# === NEW: Vector Search API Endpoints ===

@app.route(route="search", methods=["POST"], auth_level=func.AuthLevel.ANONYMOUS)
def vector_search(req: func.HttpRequest) -> func.HttpResponse:
    """Search documents using vector similarity"""
    try:
        if not vector_service:
            return func.HttpResponse(
                json.dumps({"error": "Vector service not available"}),
                status_code=503,
                mimetype="application/json"
            )
        
        # Parse request body
        try:
            req_body = req.get_json()
        except ValueError:
            return func.HttpResponse(
                json.dumps({"error": "Invalid JSON in request body"}),
                status_code=400,
                mimetype="application/json"
            )
        
        # Validate required parameters
        query = req_body.get('query')
        if not query:
            return func.HttpResponse(
                json.dumps({"error": "Query parameter is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        pdf_type = req_body.get('pdf_type')  # Optional filter
        top_k = req_body.get('top_k', 5)
        
        # Perform vector search
        start_time = time.time()
        results = vector_service.search_similar_documents(
            query=query,
            pdf_type=pdf_type,
            top_k=top_k
        )
        search_time = time.time() - start_time
        
        return func.HttpResponse(
            json.dumps({
                "query": query,
                "pdf_type": pdf_type,
                "results": results,
                "count": len(results),
                "search_time_seconds": round(search_time, 3)
            }, indent=2),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f'Error in vector search: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="collections", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def get_collections(req: func.HttpRequest) -> func.HttpResponse:
    """Get statistics about vector collections"""
    try:
        if not vector_service:
            return func.HttpResponse(
                json.dumps({"error": "Vector service not available"}),
                status_code=503,
                mimetype="application/json"
            )
        
        stats = vector_service.get_collection_stats()
        
        return func.HttpResponse(
            json.dumps(stats, indent=2),
            mimetype="application/json"
        )
        
    except Exception as e:
        logging.error(f'Error getting collections: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="health", methods=["GET"], auth_level=func.AuthLevel.ANONYMOUS)
def health_check(req: func.HttpRequest) -> func.HttpResponse:
    """Health check endpoint for the entire service"""
    try:
        health_status = {
            "status": "healthy",
            "timestamp": time.time(),
            "services": {
                "document_intelligence": {
                    "status": "configured" if os.getenv('FORM_RECOGNIZER_ENDPOINT') else "not_configured"
                },
                "azure_storage": {
                    "status": "configured" if os.getenv('AzureWebJobsStorage') else "not_configured"
                }
            }
        }
        
        # Check vector service
        if vector_service:
            vector_health = vector_service.health_check()
            health_status["services"]["vector_database"] = vector_health
            
            # Update overall status if vector service has issues
            if vector_health.get("overall_status") != "healthy":
                health_status["status"] = "degraded"
        else:
            health_status["services"]["vector_database"] = {
                "status": "not_available",
                "message": "Vector service not initialized"
            }
            health_status["status"] = "degraded"
        
        return func.HttpResponse(
            json.dumps(health_status, indent=2),
            mimetype="application/json",
            status_code=200 if health_status["status"] in ["healthy", "degraded"] else 500
        )
        
    except Exception as e:
        logging.error(f'Error in health check: {str(e)}')
        return func.HttpResponse(
            json.dumps({
                "status": "error",
                "error": str(e),
                "timestamp": time.time()
            }),
            status_code=500,
            mimetype="application/json"
        )


@app.route(route="delete-document", methods=["DELETE"], auth_level=func.AuthLevel.ANONYMOUS)
def delete_document(req: func.HttpRequest) -> func.HttpResponse:
    """Delete a document from vector database"""
    try:
        if not vector_service:
            return func.HttpResponse(
                json.dumps({"error": "Vector service not available"}),
                status_code=503,
                mimetype="application/json"
            )
        
        # Get document ID from query parameters
        document_id = req.params.get('document_id')
        if not document_id:
            return func.HttpResponse(
                json.dumps({"error": "document_id parameter is required"}),
                status_code=400,
                mimetype="application/json"
            )
        
        pdf_type = req.params.get('pdf_type')  # Optional
        
        # Delete document
        success = vector_service.delete_document(document_id, pdf_type)
        
        if success:
            return func.HttpResponse(
                json.dumps({
                    "message": f"Document {document_id} deleted successfully",
                    "document_id": document_id
                }),
                mimetype="application/json"
            )
        else:
            return func.HttpResponse(
                json.dumps({
                    "error": f"Document {document_id} not found or could not be deleted"
                }),
                status_code=404,
                mimetype="application/json"
            )
        
    except Exception as e:
        logging.error(f'Error deleting document: {str(e)}')
        return func.HttpResponse(
            json.dumps({"error": f"Internal server error: {str(e)}"}),
            status_code=500,
            mimetype="application/json"
        )
