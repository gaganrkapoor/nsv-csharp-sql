#!/usr/bin/env python3
"""
Test script for ChromaDB Vector Database Integration
Run this after starting the containers to verify everything works
"""

import requests
import json
import time
import os

# Configuration
FUNCTION_BASE_URL = "http://localhost:7071/api"
FUNCTION_ENDPOINTS = {
    "health": f"{FUNCTION_BASE_URL}/health",
    "search": f"{FUNCTION_BASE_URL}/search",
    "collections": f"{FUNCTION_BASE_URL}/collections",
    "delete": f"{FUNCTION_BASE_URL}/delete-document"
}

def test_health_check():
    """Test the health check endpoint"""
    print("🔍 Testing Health Check...")
    try:
        response = requests.get(FUNCTION_ENDPOINTS["health"], timeout=10)
        if response.status_code == 200:
            health_data = response.json()
            print(f"✅ Health Check: {health_data['status']}")
            
            # Print service statuses
            for service, status in health_data.get('services', {}).items():
                service_status = status.get('status', 'unknown')
                print(f"   - {service}: {service_status}")
            
            return True
        else:
            print(f"❌ Health Check Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Health Check Error: {e}")
        return False

def test_collections():
    """Test collections endpoint"""
    print("\n📊 Testing Collections...")
    try:
        response = requests.get(FUNCTION_ENDPOINTS["collections"], timeout=10)
        if response.status_code == 200:
            collections_data = response.json()
            print(f"✅ Collections Retrieved")
            print(f"   Total Collections: {collections_data.get('total_collections', 0)}")
            
            for name, info in collections_data.get('collections', {}).items():
                doc_count = info.get('document_count', 0)
                print(f"   - {name}: {doc_count} documents")
            
            return True
        else:
            print(f"❌ Collections Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Collections Error: {e}")
        return False

def test_search(query="invoice total"):
    """Test vector search"""
    print(f"\n🔍 Testing Vector Search with query: '{query}'...")
    try:
        search_payload = {
            "query": query,
            "top_k": 3
        }
        
        response = requests.post(
            FUNCTION_ENDPOINTS["search"],
            json=search_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            search_data = response.json()
            print(f"✅ Search Successful")
            print(f"   Query: {search_data['query']}")
            print(f"   Results: {search_data['count']}")
            print(f"   Search Time: {search_data.get('search_time_seconds', 'N/A')}s")
            
            # Show top results
            for i, result in enumerate(search_data.get('results', [])[:3]):
                filename = result.get('filename', 'unknown')
                pdf_type = result.get('pdf_type', 'unknown')
                similarity = result.get('similarity_score', 0)
                print(f"   {i+1}. {filename} ({pdf_type}) - Score: {similarity:.3f}")
            
            return True
        else:
            print(f"❌ Search Failed: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Search Error: {e}")
        return False

def test_typed_search(pdf_type="invoice", query="total amount"):
    """Test search with specific PDF type"""
    print(f"\n🎯 Testing Typed Search ({pdf_type}) with query: '{query}'...")
    try:
        search_payload = {
            "query": query,
            "pdf_type": pdf_type,
            "top_k": 3
        }
        
        response = requests.post(
            FUNCTION_ENDPOINTS["search"],
            json=search_payload,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            search_data = response.json()
            print(f"✅ Typed Search Successful")
            print(f"   PDF Type: {search_data['pdf_type']}")
            print(f"   Results: {search_data['count']}")
            
            return True
        else:
            print(f"❌ Typed Search Failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Typed Search Error: {e}")
        return False

def wait_for_service(max_retries=12, retry_delay=5):
    """Wait for the Azure Function to be ready"""
    print("⏳ Waiting for Azure Function to be ready...")
    
    for i in range(max_retries):
        try:
            response = requests.get(FUNCTION_ENDPOINTS["health"], timeout=5)
            if response.status_code == 200:
                print("✅ Azure Function is ready!")
                return True
        except requests.exceptions.RequestException:
            pass
        
        if i < max_retries - 1:
            print(f"   Attempt {i+1}/{max_retries} failed, retrying in {retry_delay}s...")
            time.sleep(retry_delay)
    
    print("❌ Azure Function did not become ready in time")
    return False

def run_full_test():
    """Run all tests"""
    print("🚀 ChromaDB Vector Database Integration Test")
    print("=" * 50)
    
    # Wait for service to be ready
    if not wait_for_service():
        print("❌ Service not available. Make sure containers are running:")
        print("   docker-compose up --build")
        return False
    
    # Run tests
    tests = [
        ("Health Check", test_health_check),
        ("Collections", test_collections),
        ("Vector Search", lambda: test_search("invoice")),
        ("Typed Search", lambda: test_typed_search("katoomba", "product"))
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n--- {test_name} ---")
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! ChromaDB integration is working perfectly.")
        print("\n📋 Next Steps:")
        print("   1. Upload a PDF to test automatic vector storage")
        print("   2. Try searching for content from your PDFs")
        print("   3. Explore the new vector search APIs")
    else:
        print("⚠️  Some tests failed. Check the logs above for details.")
        print("\n🛠️  Troubleshooting:")
        print("   1. Ensure all containers are running: docker-compose ps")
        print("   2. Check ChromaDB logs: docker-compose logs chromadb")
        print("   3. Check Function logs: docker-compose logs function")
        print("   4. Verify environment variables in .env file")
    
    return passed == total

if __name__ == "__main__":
    success = run_full_test()
    exit(0 if success else 1)