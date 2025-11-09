import os
import sys
import json

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.abspath(__file__))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

from openai import AzureOpenAI

def extract_with_ai(ocr_json, supplier):
    client = AzureOpenAI(
        api_key=os.getenv('AZURE_OPENAI_KEY'),
        api_version="2024-02-01",
        azure_endpoint=os.getenv('AZURE_OPENAI_ENDPOINT')
    )
    
    deployment = os.getenv('AZURE_OPENAI_DEPLOYMENT')
    prompt = f"""
You are an invoice extraction AI. Extract the following fields from the invoice JSON below:
- supplier
- invoice_date
- invoice_total
- total_gst
- total_discount
- invoice_lines (with description, quantity, unit_price, amount)
Supplier: {supplier}
Invoice JSON:
{ocr_json}
Return a JSON object with 'invoice_header' and 'invoice_lines'.
"""
    response = client.chat.completions.create(
        model=deployment,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.0,
        max_tokens=1024
    )
    content = response.choices[0].message.content
    return json.loads(content)
