import os
import sys

# Add the .python_packages directory to the Python path
function_app_root = os.path.dirname(os.path.abspath(__file__))
python_packages_path = os.path.join(function_app_root, '.python_packages', 'lib', 'site-packages')
if python_packages_path not in sys.path:
    sys.path.insert(0, python_packages_path)

try:
    from azure.storage.blob import BlobServiceClient
    
    connection_string = "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    
    blob_service_client = BlobServiceClient.from_connection_string(connection_string)
    
    print("🔍 Listing existing containers...")
    containers = blob_service_client.list_containers()
    container_list = [container.name for container in containers]
    
    if container_list:
        print("✅ Found containers:")
        for container_name in container_list:
            print(f"   - {container_name}")
    else:
        print("ℹ️  No containers found. Creating required containers...")
        
        required_containers = ['invoices', 'invoice-json', 'invoice-json-templates', 'processed-invoices']
        
        for container_name in required_containers:
            try:
                container_client = blob_service_client.get_container_client(container_name)
                container_client.create_container()
                print(f"✅ Created container: {container_name}")
            except Exception as e:
                if "ContainerAlreadyExists" in str(e):
                    print(f"ℹ️  Container already exists: {container_name}")
                else:
                    print(f"❌ Error creating container {container_name}: {e}")
    
    print("\n🎉 Container setup verification complete!")
    
except Exception as e:
    print(f"❌ Failed to connect to Azurite: {e}")
    print("Make sure Azurite is running on localhost:10000")