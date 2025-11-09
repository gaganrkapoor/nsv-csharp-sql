import os
import sys

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.abspath(__file__))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

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
