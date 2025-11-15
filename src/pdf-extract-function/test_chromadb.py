#!/usr/bin/env python3
"""
Test script for ChromaDB integration
"""
import sys
import os
import json
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from vector_service import VectorService

def test_chromadb_connection():
    """Test ChromaDB connection and basic operations"""
    print("🔍 Testing ChromaDB Integration...")
    
    # Initialize vector service
    vector_service = VectorService()
    
    # Test health check
    print("\n1. Testing health check...")
    try:
        is_healthy = vector_service.health_check()
        print(f"   ✅ Health check: {'Passed' if is_healthy else 'Failed'}")
    except Exception as e:
        print(f"   ❌ Health check failed: {e}")
        return False
    
    # Test storing a sample invoice
    print("\n2. Testing vector storage...")
    try:
        sample_invoice_data = {
            "supplier": "Katoomba Building Supplies",
            "invoice_number": "INV-12345",
            "total_amount": 1250.50,
            "line_items": [
                {"description": "Timber planks", "quantity": 10, "unit_price": 25.00, "total": 250.00},
                {"description": "Screws (box)", "quantity": 5, "unit_price": 15.00, "total": 75.00}
            ],
            "discount_amount": 25.50,
            "gst_amount": 112.55
        }
        
        document_id = vector_service.store_document_vector(
            pdf_filename="test_katoomba_invoice.pdf",
            extracted_json=sample_invoice_data,
            pdf_type="katoomba"
        )
        print(f"   ✅ Stored document with ID: {document_id}")
        
    except Exception as e:
        print(f"   ❌ Vector storage failed: {e}")
        return False
    
    # Test searching
    print("\n3. Testing vector search...")
    try:
        search_results = vector_service.search_similar_documents(
            query_text="Katoomba building supplies timber screws invoice",
            n_results=5
        )
        print(f"   ✅ Found {len(search_results.get('documents', [[]])[0])} matching documents")
        if search_results.get('documents') and search_results['documents'][0]:
            print(f"   📄 First result: {search_results['documents'][0][0][:100]}...")
            
    except Exception as e:
        print(f"   ❌ Vector search failed: {e}")
        return False
    
    print("\n✅ All ChromaDB tests passed! Integration is working correctly.")
    return True

if __name__ == "__main__":
    success = test_chromadb_connection()
    exit(0 if success else 1)