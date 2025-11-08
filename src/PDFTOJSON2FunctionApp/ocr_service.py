import os
from azure.ai.formrecognizer import DocumentAnalysisClient
from azure.core.credentials import AzureKeyCredential
import io

def extract_text_and_fields(pdf_bytes):
    endpoint = os.getenv('AZURE_FORM_RECOGNIZER_ENDPOINT')
    key = os.getenv('AZURE_FORM_RECOGNIZER_KEY')
    client = DocumentAnalysisClient(endpoint, AzureKeyCredential(key))
    poller = client.begin_analyze_document('prebuilt-invoice', document=io.BytesIO(pdf_bytes))
    result = poller.result()
    # Convert result to dict for downstream processing
    return result.to_dict()
