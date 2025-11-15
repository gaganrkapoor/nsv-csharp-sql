#!/bin/bash

# Todo Application Container Startup Script

set -e

echo "🚀 Starting Todo Application Containerized Environment"
echo "=================================================="

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker Desktop and try again."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose > /dev/null 2>&1; then
    echo "❌ docker-compose is not installed. Please install Docker Compose and try again."
    exit 1
fi

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.example .env
    echo "⚠️  Please edit .env file and set SQL_SA_PASSWORD before continuing."
    echo "   The password must meet SQL Server requirements:"
    echo "   - At least 8 characters"
    echo "   - Contains uppercase and lowercase letters"
    echo "   - Contains numbers and special characters"
    read -p "Press enter when you've updated the .env file..."
fi

echo "🏗️  Building and starting containers..."
docker-compose up --build -d

echo "⏳ Waiting for services to be ready..."

# Wait for SQL Server to be healthy
echo "🗄️  Waiting for SQL Server to be ready..."
timeout=300  # 5 minutes
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if docker-compose exec -T sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "$(grep SQL_SA_PASSWORD .env | cut -d '=' -f2)" -Q "SELECT 1" > /dev/null 2>&1; then
        echo "✅ SQL Server is ready!"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "   Still waiting... (${elapsed}s/${timeout}s)"
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ SQL Server failed to start within ${timeout} seconds"
    echo "📋 Check logs: docker-compose logs sqlserver"
    exit 1
fi

# Wait for API to be healthy
echo "🔧 Waiting for API to be ready..."
timeout=120  # 2 minutes
elapsed=0
while [ $elapsed -lt $timeout ]; do
    if curl -f http://localhost:3100/health > /dev/null 2>&1; then
        echo "✅ API is ready!"
        break
    fi
    sleep 5
    elapsed=$((elapsed + 5))
    echo "   Still waiting... (${elapsed}s/${timeout}s)"
done

if [ $elapsed -ge $timeout ]; then
    echo "❌ API failed to start within ${timeout} seconds"
    echo "📋 Check logs: docker-compose logs api"
    exit 1
fi

# Setup storage containers
echo "📦 Setting up storage containers..."
if command -v az > /dev/null 2>&1; then
    chmod +x docker/setup-storage.sh
    ./docker/setup-storage.sh
else
    echo "⚠️  Azure CLI not found. Storage containers need to be created manually."
    echo "   Install Azure CLI and run: ./docker/setup-storage.sh"
fi

echo ""
echo "🎉 Todo Application is ready!"
echo "================================"
echo ""
echo "🌐 Application URLs:"
echo "   Web Application:    http://localhost:3000"
echo "   API Documentation:  http://localhost:3100"
echo "   Azure Function:     http://localhost:7071"
echo ""
echo "🔧 Management URLs:"
echo "   Azurite Blob:       http://localhost:10000"
echo "   Azurite Queue:      http://localhost:10001"  
echo "   Azurite Table:      http://localhost:10002"
echo ""
echo "💾 Database Connection:"
echo "   Server:             localhost,1433"
echo "   Database:           TodoDb"
echo "   Username:           sa"
echo "   Password:           (from .env file)"
echo ""
echo "📋 Useful Commands:"
echo "   View logs:          docker-compose logs"
echo "   Stop services:      docker-compose down"
echo "   Restart services:   docker-compose restart"
echo "   View status:        docker-compose ps"
echo ""
echo "📚 For detailed documentation, see: README-CONTAINERS.md"