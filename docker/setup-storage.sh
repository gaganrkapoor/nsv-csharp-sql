#!/bin/bash

# Setup script for Azurite containers and initial configuration
# This script initializes the storage containers needed for the application

echo "🚀 Setting up Azurite storage containers..."

# Wait for Azurite to be ready
echo "⏳ Waiting for Azurite to start..."
sleep 10

# Create containers using Azure CLI with Azurite endpoint
echo "📦 Creating storage containers..."

# Set environment variables for Azurite connection
export AZURE_STORAGE_CONNECTION_STRING="DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;QueueEndpoint=http://localhost:10001/devstoreaccount1;TableEndpoint=http://localhost:10002/devstoreaccount1;"

# Create blob containers
echo "Creating 'invoices' container..."
az storage container create --name invoices --connection-string "$AZURE_STORAGE_CONNECTION_STRING" --only-show-errors

echo "Creating 'results' container..."  
az storage container create --name results --connection-string "$AZURE_STORAGE_CONNECTION_STRING" --only-show-errors

echo "Creating 'processed' container..."
az storage container create --name processed --connection-string "$AZURE_STORAGE_CONNECTION_STRING" --only-show-errors

echo "✅ Storage containers created successfully!"

# List created containers
echo "📋 Available containers:"
az storage container list --connection-string "$AZURE_STORAGE_CONNECTION_STRING" --output table --only-show-errors