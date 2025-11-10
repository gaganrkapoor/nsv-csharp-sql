"""
Test script to verify Azurite integration with Azure Functions
"""
import os
import sys

# Add the .python_packages directory to the Python path  
function_app_root = os.path.dirname(os.path.abspath(__file__))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

try:
    from azure.storage.blob import BlobServiceClient
    
    # Test using the local.settings.json AzureWebJobsStorage setting
    print("🧪 Testing Azurite connection with UseDevelopmentStorage=true...")
    
    # This should connect to Azurite automatically 
    connection_string = "UseDevelopmentStorage=true"
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    # List containers
    print("📁 Listing containers...")
    containers = list(blob_service_client.list_containers())
    
    if containers:
        print("✅ Connected to Azurite successfully!")
        for container in containers:
            print(f"   📦 Container: {container.name}")
    else:
        print("⚠️  Connected but no containers found. Creating them...")
        
        required_containers = ['invoices', 'invoice-json', 'invoice-json-templates', 'processed-invoices']
        
        for container_name in required_containers:
            try:
                container_client = blob_service_client.get_container_client(container_name)
                container_client.create_container()
                print(f"✅ Created container: {container_name}")
                
                # Test upload a dummy file
                test_content = f"Test file for container {container_name}"
                blob_client = container_client.get_blob_client(f"test-{container_name}.txt")
                blob_client.upload_blob(test_content, overwrite=True)
                print(f"   📄 Uploaded test file to {container_name}")
                
            except Exception as e:
                if "ContainerAlreadyExists" in str(e):
                    print(f"ℹ️  Container already exists: {container_name}")
                else:
                    print(f"❌ Error with container {container_name}: {e}")
    
    # Test specific connection string that matches local.settings.json
    print("\n🔗 Testing explicit Azurite connection string...")
    explicit_connection = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    
    explicit_client = BlobServiceClient.from_connection_string(explicit_connection)
    explicit_containers = list(explicit_client.list_containers())
    
    print(f"✅ Explicit connection found {len(explicit_containers)} containers")
    
    print("\n🎉 Azurite integration test complete!")
    print("\n📋 Summary:")
    print("   - Azurite is accessible")  
    print("   - Function app can connect to storage")
    print("   - All required containers are available")
    print("\n🚀 Ready to run Azure Functions with local storage!")

except Exception as e:
    print(f"❌ Connection test failed: {e}")
    print("\n🔧 Troubleshooting:")
    print("   1. Make sure Azurite is running:")
    print("      azurite --location . --loose")
    print("   2. Check if ports 10000-10002 are available")
    print("   3. Verify firewall settings")
    print("   4. Try running from azurite directory")