def extract_katoomba_fields(ocr_json):
    # Extract header fields
    header = ocr_json.get('documents', [{}])[0].get('fields', {})
    invoice_header = {
        'supplier': header.get('VendorName', {}).get('value', ''),
        'invoice_date': header.get('InvoiceDate', {}).get('value', ''),
        'invoice_total': header.get('InvoiceTotal', {}).get('value', ''),
        'total_gst': header.get('TotalTax', {}).get('value', ''),
        'total_discount': header.get('TotalDiscount', {}).get('value', ''),
    }
    # Extract line items
    line_items = []
    for item in header.get('Items', {}).get('valueArray', []):
        fields = item.get('valueObject', {})
        line_items.append({
            'description': fields.get('Description', {}).get('value', ''),
            'quantity': fields.get('Quantity', {}).get('value', ''),
            'unit_price': fields.get('UnitPrice', {}).get('value', ''),
            'amount': fields.get('Amount', {}).get('value', ''),
        })
    return {'invoice_header': invoice_header, 'invoice_lines': line_items}
