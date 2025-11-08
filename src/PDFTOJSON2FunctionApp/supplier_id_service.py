def identify_supplier(ocr_json):
    # Example: look for supplier name in OCR fields
    header = ocr_json.get('documents', [{}])[0].get('fields', {})
    supplier = header.get('VendorName', {}).get('value', '').upper()
    if 'KATOOMBA' in supplier:
        return 'KATOOMBA'
    # Add more supplier rules here
    return 'UNKNOWN'
