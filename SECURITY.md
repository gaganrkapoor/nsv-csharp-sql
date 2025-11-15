# Security Best Practices - Environment Variables

## Overview
This project uses environment variables to manage configuration and secrets securely. Follow these practices to maintain security:

## Files and Their Purpose

### `.env` (NEVER COMMIT)
- Contains actual sensitive values (passwords, API keys, endpoints)
- Listed in `.gitignore` to prevent accidental commits
- Each developer needs their own copy with real values

### `.env.example` (SAFE TO COMMIT)
- Template showing required environment variables
- Contains placeholder/example values only
- Used for documentation and setup guidance

## Setup Instructions

### For New Developers
1. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with actual values:
   - `SQL_SA_PASSWORD`: Set a strong password for SQL Server
   - `AZURE_FORM_RECOGNIZER_ENDPOINT`: Your Azure Document Intelligence endpoint
   - `AZURE_FORM_RECOGNIZER_KEY`: Your Azure Document Intelligence API key

### For Existing Projects
If you accidentally committed `.env` files:
```bash
# Remove from Git tracking (keeps local file)
git rm --cached .env

# Add to .gitignore if not already there
echo ".env" >> .gitignore

# Commit the changes
git add .gitignore
git commit -m "Remove .env from tracking and update .gitignore"
```

## Security Checklist

- [ ] `.env` files are in `.gitignore`
- [ ] No secrets in `.env.example`
- [ ] Real `.env` file exists locally with proper values
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