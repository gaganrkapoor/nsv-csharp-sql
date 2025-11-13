import logging
import os
import time
import json
import requests
from azure.storage.blob import BlobServiceClient
import azure.functions as func

app = func.FunctionApp()

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
    model_id = os.environ["FORM_RECOGNIZER_MODEL_ID"]
    
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

        # Save extracted JSON to output container
        output_client = blob_service_client.get_blob_client(
            container=output_container,
            blob=blob_name.replace(".pdf", ".json")
        )
        output_client.upload_blob(json.dumps(extracted_fields, indent=2), overwrite=True)
        logging.info(f"✅ Saved extracted fields to {output_container}/{blob_name.replace('.pdf', '.json')}")
