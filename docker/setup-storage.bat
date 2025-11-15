@echo off
REM Setup script for Azurite containers and initial configuration (Windows)

echo 🚀 Setting up Azurite storage containers...

REM Wait for Azurite to be ready
echo ⏳ Waiting for Azurite to start...
timeout /t 10 /nobreak >nul

REM Set environment variables for Azurite connection
set AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://localhost:10000/devstoreaccount1;QueueEndpoint=http://localhost:10001/devstoreaccount1;TableEndpoint=http://localhost:10002/devstoreaccount1;

echo 📦 Creating storage containers...

REM Create blob containers
echo Creating 'invoices' container...
az storage container create --name invoices --connection-string "%AZURE_STORAGE_CONNECTION_STRING%" --only-show-errors

echo Creating 'results' container...
az storage container create --name results --connection-string "%AZURE_STORAGE_CONNECTION_STRING%" --only-show-errors

echo Creating 'processed' container...
az storage container create --name processed --connection-string "%AZURE_STORAGE_CONNECTION_STRING%" --only-show-errors

echo ✅ Storage containers created successfully!

REM List created containers
echo 📋 Available containers:
az storage container list --connection-string "%AZURE_STORAGE_CONNECTION_STRING%" --output table --only-show-errors

pause