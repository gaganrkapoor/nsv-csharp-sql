# Use the official Azure Functions Python base image
FROM mcr.microsoft.com/azure-functions/python:4-python3.11

# Set environment variables for Azure Functions
ENV AzureWebJobsScriptRoot=/home/site/wwwroot \
    AzureFunctionsJobHost__Logging__Console__IsEnabled=true \
    FUNCTIONS_WORKER_RUNTIME=python

# Install system dependencies including updated SQLite3 for ChromaDB
RUN apt-get update && \
    apt-get install -y \
    build-essential \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install newer SQLite3 from source (required for ChromaDB)
RUN curl -O https://www.sqlite.org/2024/sqlite-autoconf-3460000.tar.gz && \
    tar xzf sqlite-autoconf-3460000.tar.gz && \
    cd sqlite-autoconf-3460000 && \
    ./configure --prefix=/usr/local && \
    make && \
    make install && \
    cd .. && \
    rm -rf sqlite-autoconf-3460000* && \
    ldconfig

# Update environment to use new SQLite3
ENV LD_LIBRARY_PATH=/usr/local/lib:$LD_LIBRARY_PATH

# Set working directory
WORKDIR /home/site/wwwroot

# Copy requirements and install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy function code
COPY . .

# Make sure the function app is executable
RUN chmod +x .

# Expose the port that Azure Functions runtime uses
EXPOSE 80

# The base image already has the correct entry point
# CMD is handled by the base image