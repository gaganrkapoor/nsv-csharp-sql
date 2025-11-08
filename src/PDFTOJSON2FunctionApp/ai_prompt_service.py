import os
import openai

def extract_with_ai(ocr_json, supplier):
    openai.api_type = "azure"
    openai.api_base = os.getenv('AZURE_OPENAI_ENDPOINT')
    openai.api_key = os.getenv('AZURE_OPENAI_KEY')
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
    response = openai.ChatCompletion.create(
        engine=deployment,
        messages=[{"role": "system", "content": prompt}],
        temperature=0.0,
        max_tokens=1024
    )
    content = response['choices'][0]['message']['content']
    return json.loads(content)
