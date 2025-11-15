# Containerized Todo Application

This directory contains the full containerization setup for the Todo application with SQL Server Express.

## 🏗️ Architecture

The containerized setup includes:

- **React Web App** (Frontend) - Port 3000
- **C# .NET 8 Web API** (Backend) - Port 3100  
- **Python Azure Function** (PDF Processing) - Port 7071
- **SQL Server Express** (Database) - Port 1433
- **Azurite** (Storage Emulator) - Ports 10000-10002

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- Docker Compose v2.0+
- Azure CLI (for storage container setup)

### 1. Environment Setup

```bash
# Copy the environment template
cp .env.example .env

# Edit .env file to set your SQL Server password
# Minimum requirements: 8 characters, uppercase, lowercase, number, special char
```

### 2. Build and Start All Services

```bash
# Build and start all containers
docker-compose up --build

# Or run in detached mode
docker-compose up -d --build
```

### 3. Setup Storage Containers

After containers are running, initialize Azurite storage:

**Windows:**
```cmd
docker\setup-storage.bat
```

**Linux/Mac:**
```bash
chmod +x docker/setup-storage.sh
./docker/setup-storage.sh
```

### 4. Access the Application

- **Web Application**: http://localhost:3000
- **API Documentation**: http://localhost:3100 (Swagger UI)
- **Azure Function**: http://localhost:7071
- **Azurite Blob Storage**: http://localhost:10000

## 🔧 Development Commands

### Container Management

```bash
# View running containers
docker-compose ps

# View logs for all services
docker-compose logs

# View logs for specific service
docker-compose logs api
docker-compose logs web
docker-compose logs function
docker-compose logs sqlserver

# Restart specific service
docker-compose restart api

# Stop all services
docker-compose down

# Stop and remove volumes (⚠️ destroys data)
docker-compose down -v
```

### Database Management

```bash
# Connect to SQL Server
docker exec -it todo-sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong!Passw0rd

# Run SQL commands
USE TodoDb;
SELECT * FROM TodoLists;
GO
```

### Debugging

```bash
# Execute bash in API container
docker exec -it todo-api bash

# Execute bash in Function container  
docker exec -it todo-function bash

# Execute PowerShell in SQL Server container
docker exec -it todo-sqlserver /bin/bash
```

## 📁 Directory Structure

```
/
├── docker/
│   ├── sql/
│   │   └── init.sql              # Database initialization
│   ├── setup-storage.sh         # Storage setup (Linux/Mac)
│   └── setup-storage.bat        # Storage setup (Windows)
├── src/
│   ├── api/
│   │   ├── Dockerfile           # .NET API container
│   │   └── .dockerignore
│   ├── web/
│   │   ├── Dockerfile           # React app container
│   │   └── .dockerignore
│   └── pdf-extract-function/
│       ├── Dockerfile           # Python function container
│       └── .dockerignore
├── docker-compose.yml           # Main orchestration file
├── .env                         # Environment variables
├── .env.example                 # Environment template
└── README-CONTAINERS.md         # This file
```

## 🔒 Security Notes

### For Development
- Using SA account for SQL Server (acceptable for local dev)
- Default Azurite credentials (development only)
- No HTTPS termination (use reverse proxy in production)

### For Production
- Create dedicated SQL users with minimal permissions
- Use Azure Key Vault or Docker secrets for sensitive data
- Implement proper networking and firewalls
- Add HTTPS/TLS termination
- Use production-grade SQL Server (not Express)

## 🐛 Troubleshooting

### SQL Server Won't Start
- Ensure password meets complexity requirements
- Check available memory (SQL Server needs sufficient RAM)
- Verify port 1433 is not already in use

### API Can't Connect to Database
- Wait for SQL Server health check to pass
- Check connection string in docker-compose.yml
- Verify TodoDb database was created

### Function App Issues
- Check Azurite is running and accessible
- Verify storage connection string
- Ensure required containers exist

### Storage Container Creation Fails
- Verify Azurite is running on ports 10000-10002
- Check Azure CLI is installed and accessible
- Wait longer for Azurite to fully initialize

## 📊 Health Checks

The setup includes health checks for critical services:

```bash
# Check all service health
docker-compose ps

# Manual health check commands
docker exec todo-sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P YourStrong!Passw0rd -Q "SELECT 1"
curl -f http://localhost:3100/health
curl -f http://localhost:3000
curl -f http://localhost:10000/devstoreaccount1
```

## 🔄 Data Persistence

Data is persisted using Docker volumes:

- `sqlserver_data`: SQL Server database files
- `azurite_data`: Azurite storage data

To backup/restore data:

```bash
# Backup SQL Server data
docker run --rm -v sqlserver_data:/data -v $(pwd):/backup ubuntu tar czf /backup/sqlserver-backup.tar.gz -C /data .

# Restore SQL Server data
docker run --rm -v sqlserver_data:/data -v $(pwd):/backup ubuntu tar xzf /backup/sqlserver-backup.tar.gz -C /data
```

## 🚢 Production Deployment

For production deployment, consider:

1. **Container Orchestration**: Kubernetes, Docker Swarm, or Azure Container Apps
2. **Database**: Azure SQL Database or managed SQL Server instance
3. **Storage**: Azure Storage Account instead of Azurite
4. **Monitoring**: Application Insights, Prometheus + Grafana
5. **Secrets**: Azure Key Vault, Kubernetes secrets, or HashiCorp Vault
6. **Load Balancing**: Application Gateway, NGINX, or Traefik
7. **CI/CD**: Azure DevOps, GitHub Actions, or GitLab CI

## 🆘 Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review container logs: `docker-compose logs [service-name]`
3. Verify all prerequisites are installed
4. Ensure Docker Desktop has sufficient resources allocated
5. Try rebuilding containers: `docker-compose build --no-cache`