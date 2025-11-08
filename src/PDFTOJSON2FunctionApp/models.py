from typing import List, Dict

class InvoiceHeader:
    def __init__(self, supplier: str, invoice_date: str, invoice_total: str, total_gst: str, total_discount: str):
        self.supplier = supplier
        self.invoice_date = invoice_date
        self.invoice_total = invoice_total
        self.total_gst = total_gst
        self.total_discount = total_discount

class InvoiceLine:
    def __init__(self, description: str, quantity: str, unit_price: str, amount: str):
        self.description = description
        self.quantity = quantity
        self.unit_price = unit_price
        self.amount = amount

class InvoiceData:
    def __init__(self, invoice_header: InvoiceHeader, invoice_lines: List[InvoiceLine]):
        self.invoice_header = invoice_header
        self.invoice_lines = invoice_lines
