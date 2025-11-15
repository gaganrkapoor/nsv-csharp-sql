# Security Best Practices - Environment Variables

## Overview
This project uses environment variables to manage configuration and secrets securely. Follow these practices to maintain security:

## Files and Their Purpose

### `.env` (NEVER COMMIT)
- Contains actual sensitive values (passwords, API keys, endpoints)
- Listed in `.gitignore` to prevent accidental commits
- Each developer needs their own copy with real values

### `.env.template` (SAFE TO COMMIT)
- Template showing required environment variables
- Contains placeholder/example values only  
- Used for documentation and setup guidance

### `.env.example` (NEVER COMMIT - IGNORED)
- May contain real values during development
- Listed in `.gitignore` to prevent accidental commits
- Each developer creates their own copy from template

## Setup Instructions

### For New Developers
1. Copy `.env.template` to `.env.example`, then to `.env`:
   ```bash
   cp .env.template .env.example
   cp .env.template .env
   ```

2. Update `.env.example` with your actual values (this stays local)
3. Update `.env` with actual values for docker-compose
   - `SQL_SA_PASSWORD`: Set a strong password for SQL Server
   - `AZURE_FORM_RECOGNIZER_ENDPOINT`: Your Azure Document Intelligence endpoint
   - `AZURE_FORM_RECOGNIZER_KEY`: Your Azure Document Intelligence API key

### For Existing Projects
If you accidentally committed `.env` or `.env.example` files with real secrets:
```bash
# Remove from Git tracking (keeps local files)
git rm --cached .env .env.example

# Add to .gitignore if not already there
echo -e ".env\n.env.example" >> .gitignore

# Commit the changes
git add .gitignore
git commit -m "Remove sensitive env files from tracking and update .gitignore"
```

## Security Checklist

- [ ] `.env` and `.env.example` files are in `.gitignore`
- [ ] No secrets in `.env.template`
- [ ] Real environment files exist locally with proper values
- [ ] Sensitive values are never hardcoded in source code
- [ ] Production secrets are managed through secure deployment processes

## Azure Document Intelligence Configuration

Required environment variables:
- `AZURE_FORM_RECOGNIZER_ENDPOINT`: The endpoint URL for your Azure Document Intelligence resource
- `AZURE_FORM_RECOGNIZER_KEY`: The API key for authentication

To get these values:
1. Go to Azure Portal
2. Navigate to your Document Intelligence resource
3. Find "Keys and Endpoint" in the left menu
4. Copy the endpoint and either key

## Troubleshooting

### Common Issues
1. **Function not connecting to Azure**: Check endpoint and key values
2. **SQL Server connection fails**: Verify SQL_SA_PASSWORD matches docker-compose.yml
3. **Environment variables not loading**: Ensure .env file is in project root

### Validation
Test your configuration:
```bash
# Check if .env is properly ignored
git status

# Verify environment variables are loaded
docker-compose config
```

## Production Deployment

For production environments:
- Use Azure Key Vault or similar secret management
- Set environment variables through deployment pipelines
- Never use `.env` files in production
- Rotate secrets regularly