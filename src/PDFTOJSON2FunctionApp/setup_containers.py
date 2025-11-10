import os
import sys
import json
from datetime import datetime

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.abspath(__file__))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

from azure.storage.blob import BlobServiceClient


def create_containers():
    """Create the required blob containers for the invoice processing pipeline"""
    
    # Get connection string from environment
    connection_string = os.getenv('AzureWebJobsStorage')
    if not connection_string:
        print("Error: AzureWebJobsStorage not found in environment variables")
        return
    
    # For local development, use the development storage
    if connection_string == "UseDevelopmentStorage=true":
        connection_string = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    
    try:
        # Create blob service client
        blob_service_client = BlobServiceClient.from_connection_string(connection_string)
        
        # Define containers to create
        containers = [
            "invoices",              # Input container for PDF invoices
            "invoice-json",          # Container for OCR JSON files
            "invoice-json-templates", # Container for JSON templates by supplier
            "processed-invoices"     # Container for final processed invoice data
        ]
        
        for container_name in containers:
            try:
                container_client = blob_service_client.get_container_client(container_name)
                
                # Check if container exists
                if not container_client.exists():
                    container_client.create_container()
                    print(f"✓ Created container: {container_name}")
                else:
                    print(f"✓ Container already exists: {container_name}")
                    
            except Exception as e:
                print(f"✗ Error creating container {container_name}: {e}")
        
        # Create sample template files in invoice-json-templates container
        create_sample_templates(blob_service_client)
        
        print("\n✓ Container setup complete!")
        
    except Exception as e:
        print(f"Error setting up containers: {e}")


def create_sample_templates(blob_service_client):
    """Create sample template files in the invoice-json-templates container"""
    
    try:
        container_client = blob_service_client.get_container_client("invoice-json-templates")
        
        # Katoomba template
        katoomba_template = {
            "supplier": "KATOOMBA",
            "template_version": "1.0",
            "created_date": datetime.now().isoformat(),
            "fields": {
                "invoice_header": {
                    "supplier": "string",
                    "invoice_date": "date",
                    "invoice_number": "string",
                    "invoice_total": "decimal",
                    "total_gst": "decimal",
                    "total_discount": "decimal"
                },
                "invoice_lines": [
                    {
                        "description": "string",
                        "quantity": "decimal",
                        "unit_price": "decimal",
                        "amount": "decimal"
                    }
                ]
            },
            "extraction_rules": {
                "invoice_number": "Look for patterns like 'Invoice #' or 'INV-'",
                "supplier_identification": "Look for 'KATOOMBA' in company name or header",
                "date_format": "DD/MM/YYYY or DD-MM-YYYY",
                "currency": "AUD"
            }
        }
        
        # Generic template
        generic_template = {
            "supplier": "GENERIC",
            "template_version": "1.0",
            "created_date": datetime.now().isoformat(),
            "fields": {
                "invoice_header": {
                    "supplier": "string",
                    "invoice_date": "date",
                    "invoice_number": "string", 
                    "invoice_total": "decimal",
                    "total_gst": "decimal",
                    "total_discount": "decimal"
                },
                "invoice_lines": [
                    {
                        "description": "string",
                        "quantity": "decimal",
                        "unit_price": "decimal",
                        "amount": "decimal"
                    }
                ]
            },
            "extraction_rules": {
                "fallback_to_ai": True,
                "ai_model": "gpt-4",
                "currency": "AUD"
            }
        }
        
        # Upload templates
        templates = [
            ("katoomba_template.json", katoomba_template),
            ("generic_template.json", generic_template)
        ]
        
        for filename, template_data in templates:
            try:
                blob_client = container_client.get_blob_client(filename)
                template_json = json.dumps(template_data, indent=2)
                blob_client.upload_blob(template_json, overwrite=True)
                print(f"✓ Created template: {filename}")
            except Exception as e:
                print(f"✗ Error creating template {filename}: {e}")
                
    except Exception as e:
        print(f"Error creating templates: {e}")


if __name__ == "__main__":
    print("Setting up Azure Storage containers for invoice processing...")
    create_containers()