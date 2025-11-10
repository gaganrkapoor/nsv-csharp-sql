import os
import sys
import logging
import re
from datetime import datetime

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # Go up to PDFTOJSON2FunctionApp
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

def extract_katoomba_fields(ocr_json):
    """Extract Katoomba-specific invoice fields"""
    try:
        content = ocr_json.get("content", "")
        fields = ocr_json.get("fields", {})
        tables = ocr_json.get("tables", [])
        documents = ocr_json.get("documents", [])
        
        # Extract header fields using multiple sources
        invoice_header = {
            "InvoiceNumber": extract_invoice_number(content, documents),
            "InvoiceDate": extract_invoice_date(content, documents),
            "LineTotalExclGST": extract_line_total_excl_gst(content, documents),
            "ExpenseDiscount": extract_expense_discount(content, documents),
            "TotalExclGST": extract_total_excl_gst(content, documents),
            "GSTAmount": extract_gst_amount(content, documents),
            "TotalInclGST": extract_total_incl_gst(content, documents),
            "SupplierName": "KATOOMBA GLOBAL FOODS",
            "CustomerName": extract_customer_name(content, documents),
            "PONumber": extract_po_number(content, documents)
        }
        
        # Extract line items from tables and structured data
        line_items = extract_line_items(tables, documents, content)
        
        result = {
            "supplier": "KATOOMBA",
            "header": invoice_header,
            "line_items": line_items,
            "extraction_method": "KATOOMBA_RULE_BASED",
            "processed_at": datetime.now().isoformat()
        }
        
        logging.info(f"Katoomba extraction completed: {len(line_items)} line items")
        return result
        
    except Exception as e:
        logging.error(f"Error in Katoomba extraction: {e}")
        return {"error": str(e), "supplier": "KATOOMBA"}

def extract_invoice_number(content, documents):
    """Extract invoice number using multiple methods"""
    # Try structured fields first
    for doc in documents:
        fields = doc.get('fields', {})
        if 'InvoiceId' in fields and fields['InvoiceId'].get('value'):
            return fields['InvoiceId']['value']
    
    # Fallback to pattern matching
    patterns = [
        r"Invoice\s*#?\s*:?\s*([A-Z0-9\-]+)",
        r"INV\s*:?\s*([A-Z0-9\-]+)",
        r"Invoice\s+Number\s*:?\s*([A-Z0-9\-]+)"
    ]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""

def extract_invoice_date(content, documents):
    """Extract invoice date"""
    # Try structured fields first
    for doc in documents:
        fields = doc.get('fields', {})
        if 'InvoiceDate' in fields and fields['InvoiceDate'].get('value'):
            date_value = fields['InvoiceDate']['value']
            if isinstance(date_value, str):
                return date_value
            elif hasattr(date_value, 'isoformat'):
                return date_value.isoformat()
    
    # Pattern matching for date
    date_patterns = [
        r"Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"Invoice\s+Date\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
        r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})"
    ]
    for pattern in date_patterns:
        match = re.search(pattern, content)
        if match:
            return match.group(1)
    return ""

def extract_line_total_excl_gst(content, documents):
    """Extract line total excluding GST"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'SubTotal' in fields and fields['SubTotal'].get('value'):
            return float(fields['SubTotal']['value'] or 0)
    
    # Pattern matching
    patterns = [r"Sub\s*Total\s*:?\s*\$?([0-9,]+\.?\d*)", r"Line\s*Total\s*:?\s*\$?([0-9,]+\.?\d*)"]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    return 0.0

def extract_expense_discount(content, documents):
    """Extract expense discount"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'TotalDiscount' in fields and fields['TotalDiscount'].get('value'):
            return float(fields['TotalDiscount']['value'] or 0)
    return 0.0

def extract_total_excl_gst(content, documents):
    """Extract total excluding GST"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'SubTotal' in fields and fields['SubTotal'].get('value'):
            return float(fields['SubTotal']['value'] or 0)
    return 0.0

def extract_gst_amount(content, documents):
    """Extract GST amount"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'TotalTax' in fields and fields['TotalTax'].get('value'):
            return float(fields['TotalTax']['value'] or 0)
    
    # Pattern matching
    patterns = [r"GST\s*:?\s*\$?([0-9,]+\.?\d*)", r"Tax\s*:?\s*\$?([0-9,]+\.?\d*)"]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    return 0.0

def extract_total_incl_gst(content, documents):
    """Extract total including GST"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'InvoiceTotal' in fields and fields['InvoiceTotal'].get('value'):
            return float(fields['InvoiceTotal']['value'] or 0)
    
    # Pattern matching
    patterns = [r"Total\s*:?\s*\$?([0-9,]+\.?\d*)", r"Amount\s+Due\s*:?\s*\$?([0-9,]+\.?\d*)"]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return float(match.group(1).replace(',', ''))
    return 0.0

def extract_customer_name(content, documents):
    """Extract customer name"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'CustomerName' in fields and fields['CustomerName'].get('value'):
            return fields['CustomerName']['value']
    return ""

def extract_po_number(content, documents):
    """Extract PO number"""
    for doc in documents:
        fields = doc.get('fields', {})
        if 'PurchaseOrder' in fields and fields['PurchaseOrder'].get('value'):
            return fields['PurchaseOrder']['value']
    
    # Pattern matching
    patterns = [r"PO\s*#?\s*:?\s*([A-Z0-9\-]+)", r"Purchase\s+Order\s*:?\s*([A-Z0-9\-]+)"]
    for pattern in patterns:
        match = re.search(pattern, content, re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return ""

def extract_line_items(tables, documents, content):
    """Extract line items from tables and structured data"""
    line_items = []
    
    # Try structured document fields first
    for doc in documents:
        fields = doc.get('fields', {})
        items_field = fields.get('Items', {})
        if items_field and 'valueArray' in items_field:
            for item in items_field['valueArray']:
                item_fields = item.get('valueObject', {})
                line_items.append({
                    'description': item_fields.get('Description', {}).get('value', ''),
                    'quantity': float(item_fields.get('Quantity', {}).get('value', 0) or 0),
                    'unit_price': float(item_fields.get('UnitPrice', {}).get('value', 0) or 0),
                    'amount': float(item_fields.get('Amount', {}).get('value', 0) or 0),
                })
    
    # If no structured items found, try to extract from tables
    if not line_items and tables:
        for table in tables:
            cells = table.get('cells', [])
            # Group cells by row
            rows = {}
            for cell in cells:
                row_idx = cell.get('row_index', 0)
                if row_idx not in rows:
                    rows[row_idx] = {}
                rows[row_idx][cell.get('column_index', 0)] = cell.get('content', '')
            
            # Process rows (skip header row)
            for row_idx in sorted(rows.keys())[1:]:  # Skip first row (header)
                row_data = rows[row_idx]
                if len(row_data) >= 4:  # Ensure we have enough columns
                    line_items.append({
                        'description': row_data.get(0, ''),
                        'quantity': safe_float(row_data.get(1, '0')),
                        'unit_price': safe_float(row_data.get(2, '0')),
                        'amount': safe_float(row_data.get(3, '0')),
                    })
    
    return line_items

def safe_float(value):
    """Safely convert value to float"""
    try:
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            # Remove currency symbols and commas
            cleaned = re.sub(r'[^\d.-]', '', value.replace(',', ''))
            return float(cleaned) if cleaned else 0.0
    except (ValueError, TypeError):
        pass
    return 0.0