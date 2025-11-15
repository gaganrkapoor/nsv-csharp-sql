@echo off
REM Todo Application Container Startup Script for Windows

echo 🚀 Starting Todo Application Containerized Environment
echo ==================================================

REM Check if Docker is running
docker info >nul 2>&1
if errorlevel 1 (
    echo ❌ Docker is not running. Please start Docker Desktop and try again.
    pause
    exit /b 1
)

REM Check if .env file exists
if not exist .env (
    echo 📝 Creating .env file from template...
    copy .env.example .env >nul
    echo ⚠️  Please edit .env file and set SQL_SA_PASSWORD before continuing.
    echo    The password must meet SQL Server requirements:
    echo    - At least 8 characters
    echo    - Contains uppercase and lowercase letters
    echo    - Contains numbers and special characters
    pause
)

echo 🏗️  Building and starting containers...
docker-compose up --build -d

echo ⏳ Waiting for services to be ready...

REM Wait for SQL Server to be healthy
echo 🗄️  Waiting for SQL Server to be ready...
:wait_sql
timeout /t 10 /nobreak >nul
for /f "tokens=2 delims==" %%a in ('findstr SQL_SA_PASSWORD .env') do set SA_PASSWORD=%%a
docker-compose exec -T sqlserver /opt/mssql-tools/bin/sqlcmd -S localhost -U sa -P "%SA_PASSWORD%" -Q "SELECT 1" >nul 2>&1
if errorlevel 1 (
    echo    Still waiting for SQL Server...
    goto wait_sql
)
echo ✅ SQL Server is ready!

REM Wait for API to be healthy  
echo 🔧 Waiting for API to be ready...
:wait_api
timeout /t 5 /nobreak >nul
curl -f http://localhost:3100/health >nul 2>&1
if errorlevel 1 (
    echo    Still waiting for API...
    goto wait_api
)
echo ✅ API is ready!

REM Setup storage containers
echo 📦 Setting up storage containers...
where az >nul 2>&1
if errorlevel 1 (
    echo ⚠️  Azure CLI not found. Storage containers need to be created manually.
    echo    Install Azure CLI and run: docker\setup-storage.bat
) else (
    call docker\setup-storage.bat
)

echo.
echo 🎉 Todo Application is ready!
echo ================================
echo.
echo 🌐 Application URLs:
echo    Web Application:    http://localhost:3000
echo    API Documentation:  http://localhost:3100  
echo    Azure Function:     http://localhost:7071
echo.
echo 🔧 Management URLs:
echo    Azurite Blob:       http://localhost:10000
echo    Azurite Queue:      http://localhost:10001
echo    Azurite Table:      http://localhost:10002
echo.
echo 💾 Database Connection:
echo    Server:             localhost,1433
echo    Database:           TodoDb
echo    Username:           sa
echo    Password:           (from .env file)
echo.
echo 📋 Useful Commands:
echo    View logs:          docker-compose logs
echo    Stop services:      docker-compose down
echo    Restart services:   docker-compose restart
echo    View status:        docker-compose ps
echo.
echo 📚 For detailed documentation, see: README-CONTAINERS.md
echo.
pause