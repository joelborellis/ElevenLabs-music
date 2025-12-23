# Fix: Azure PostgreSQL Token Expiration Issue

## Problem
```
FATAL: The access token has expired. Acquire a new token and try again.
```

The MCP server is using Microsoft Entra ID token-based authentication for Azure PostgreSQL Flexible Server, and the access token expires (typically after 1 hour).

## Root Cause
Azure PostgreSQL with Entra ID authentication requires:
1. **Password = Access Token** (not a static password)
2. **Tokens expire** every ~60 minutes
3. The connection pool holds expired tokens and can't reconnect

## Solutions

### Option 1: Use Managed Identity with Token Refresh (RECOMMENDED)

The postgres-mcp server needs to be configured to automatically refresh tokens. Here's what needs to be done:

#### 1.1 Enable Managed Identity on Container App
```bash
# Enable system-assigned managed identity
az containerapp identity assign \
  --name postgres-mcp \
  --resource-group <your-resource-group> \
  --system-assigned

# Get the identity's principal ID
PRINCIPAL_ID=$(az containerapp identity show \
  --name postgres-mcp \
  --resource-group <your-resource-group> \
  --query principalId -o tsv)

echo "Managed Identity Principal ID: $PRINCIPAL_ID"
```

#### 1.2 Grant Database Access to Managed Identity
```sql
-- Connect to PostgreSQL as an admin and run:

-- For system-assigned managed identity
SET aad_validate_oids_in_tenant = off;

CREATE ROLE "postgres-mcp" WITH LOGIN IN ROLE azure_ad_user;
GRANT ALL PRIVILEGES ON DATABASE your_database TO "postgres-mcp";
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO "postgres-mcp";
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO "postgres-mcp";
```

#### 1.3 Update Connection String for Managed Identity
The MCP server code needs to use `azure-identity` library to get tokens:

**Problem:** Standard `postgres-mcp` may not support this out of the box.

### Option 2: Use Password Authentication (SIMPLER)

Switch from Entra ID auth to PostgreSQL native authentication:

#### 2.1 Create PostgreSQL User with Password
```sql
-- Connect as admin
CREATE USER mcp_user WITH PASSWORD 'your-secure-password-here';
GRANT ALL PRIVILEGES ON DATABASE your_database TO mcp_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO mcp_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO mcp_user;
```

#### 2.2 Update DATABASE_URI
```bash
# Update Container App environment variable
az containerapp update \
  --name postgres-mcp \
  --resource-group <your-resource-group> \
  --set-env-vars "DATABASE_URI=postgresql://mcp_user:your-secure-password-here@135.119.75.52:5432/your_database?sslmode=require"
```

Or use secrets:
```bash
# Create secret
az containerapp secret set \
  --name postgres-mcp \
  --resource-group <your-resource-group> \
  --secrets database-uri="postgresql://mcp_user:your-secure-password-here@135.119.75.52:5432/your_database?sslmode=require"

# Reference secret
az containerapp update \
  --name postgres-mcp \
  --resource-group <your-resource-group> \
  --set-env-vars "DATABASE_URI=secretref:database-uri"
```

### Option 3: Custom Token Refresh Wrapper

If you must use Entra ID auth, create a wrapper that refreshes tokens:

#### 3.1 Install Azure Identity
Add to your MCP server's dependencies:
```toml
[dependencies]
azure-identity = "^1.15.0"
psycopg2-binary = "^2.9.9"  # or asyncpg
```

#### 3.2 Create Token Refresh Connection Class
```python
from azure.identity import DefaultAzureCredential
import psycopg2
import time

class AzurePostgresConnection:
    def __init__(self, host, database, user):
        self.host = host
        self.database = database
        self.user = user
        self.credential = DefaultAzureCredential()
        self.token = None
        self.token_expiry = 0
        
    def get_connection_string(self):
        # Refresh token if expired (refresh 5 min before expiry)
        if time.time() >= self.token_expiry - 300:
            token_result = self.credential.get_token(
                "https://ossrdbms-aad.database.windows.net/.default"
            )
            self.token = token_result.token
            self.token_expiry = token_result.expires_on
            
        return f"postgresql://{self.user}:{self.token}@{self.host}:5432/{self.database}?sslmode=require"
```

### Option 4: Restart Container App (TEMPORARY FIX)

This will acquire a new token but will expire again in ~1 hour:

```bash
# Restart the container app
az containerapp revision restart \
  --name postgres-mcp \
  --resource-group <your-resource-group> \
  --revision <revision-name>

# Or restart all revisions
az containerapp restart \
  --name postgres-mcp \
  --resource-group <your-resource-group>
```

## Recommended Approach

**For production: Use Option 2 (Password Authentication)**
- Simpler to maintain
- No token expiration issues
- Store password in Azure Key Vault or Container App secrets
- Works with standard postgres-mcp without modifications

**For enhanced security: Use Option 1 or 3 (Managed Identity)**
- No passwords to manage
- Better for compliance/security requirements
- Requires custom token refresh logic
- May need to fork/modify postgres-mcp

## Verification Steps

After applying the fix:

1. **Restart the container app:**
   ```bash
   az containerapp restart --name postgres-mcp --resource-group <rg>
   ```

2. **Watch the logs:**
   ```bash
   az containerapp logs show --name postgres-mcp --resource-group <rg> --follow
   ```

3. **Test the connection:**
   ```bash
   uv run python testing/test_postgres_mcp.py
   ```

4. **Verify no token errors:**
   You should NOT see "The access token has expired" in the logs

## Quick Fix Commands

```powershell
# PowerShell commands for quick fix (Option 2)

# 1. Create a strong password
$password = -join ((33..126) | Get-Random -Count 32 | ForEach-Object {[char]$_})

# 2. Update the DATABASE_URI (replace values)
az containerapp update `
  --name postgres-mcp `
  --resource-group your-resource-group `
  --set-env-vars "DATABASE_URI=postgresql://mcp_user:$password@135.119.75.52:5432/your_database?sslmode=require"

# 3. Restart the app
az containerapp restart --name postgres-mcp --resource-group your-resource-group
```

## Additional Resources

- [Azure PostgreSQL Entra ID Auth](https://learn.microsoft.com/en-us/azure/postgresql/flexible-server/concepts-azure-ad-authentication)
- [Container Apps Managed Identity](https://learn.microsoft.com/en-us/azure/container-apps/managed-identity)
- [Azure Identity SDK](https://learn.microsoft.com/en-us/python/api/overview/azure/identity-readme)
