# Deployment — Azure Container Apps

Runbook for deploying this API to **Azure Container Apps** (ACA). The app stores
audio in **Azure Blob Storage** and metadata in **Azure Database for PostgreSQL**,
so it holds no local state and fits ACA's ephemeral filesystem.

> **Shell note:** commands use bash line-continuations (`\`). Run them in **Git
> Bash**, **WSL**, or the **Azure Cloud Shell**. In PowerShell, replace the
> trailing `\` with a backtick `` ` `` (or put each command on one line).

## Prerequisites

- Azure CLI logged in: `az login` (and `az account set --subscription <id>` if needed).
- These resources already exist: storage account `gtlopenaidemostorage`, Postgres
  Flexible Server `mcp-registry-postgres` (database `elevenlabs_music`, already
  migrated to head), and an Azure Container Registry (ACR).
- The `containerapp` CLI extension: `az extension add --name containerapp --upgrade`.

## What goes where (config model)

| Config | Where | Notes |
| --- | --- | --- |
| API keys, `DATABASE_URL` | ACA **secrets** → referenced via `secretref:` | Sensitive; never plaintext env, never in the image. |
| `STORAGE_BACKEND`, `AZURE_STORAGE_ACCOUNT_URL`, `AZURE_STORAGE_CONTAINER`, `ENVIRONMENT`, `CORS_ORIGINS` | ACA **env vars** | Non-sensitive runtime config. |
| `AZURE_STORAGE_CONNECTION_STRING` | **omitted in prod** | Absence makes the app use managed identity for Blob. |
| ACR name / login server | **deploy-time shell vars only** | Not app config; the app never talks to ACR at runtime. `.env` is unchanged and not shipped. |

## Step 0 — Discover values & set shell variables

```bash
az account show -o table
az group list -o table
az acr list -o table                        # note NAME + loginServer
az postgres flexible-server list -o table   # note server name + its resource group

# Fill these in:
RG=<resource-group-for-the-app>
LOCATION=<region e.g. eastus>
ACR_NAME=<your-acr-name>
APP=elevenlabs-music-api
ENV=elevenlabs-env
PG_RG=<resource-group-of-postgres>

# Derived:
ACR_LOGIN_SERVER=$(az acr show -n $ACR_NAME --query loginServer -o tsv)
STORAGE_ID=$(az storage account show -n gtlopenaidemostorage --query id -o tsv)

# Secrets (paste values or source from your local .env):
OPENAI_API_KEY=<...>
ELEVENLABS_API_KEY=<...>
DATABASE_URL='postgresql+asyncpg://<user>:<pass>@mcp-registry-postgres.postgres.database.azure.com:5432/elevenlabs_music?ssl=require'
FRONTEND_ORIGIN='https://<your-frontend-domain>'
```

## Step 1 — Build & push the image (cloud build; no local Docker needed)

```bash
az acr build -r $ACR_NAME -t elevenlabs-music-api:v1 .
```

## Step 2 — Create the Container Apps environment

```bash
az containerapp env create -n $ENV -g $RG -l $LOCATION
```

## Step 3 — Create the Container App

```bash
az containerapp create -n $APP -g $RG --environment $ENV \
  --image $ACR_LOGIN_SERVER/elevenlabs-music-api:v1 \
  --system-assigned \
  --registry-server $ACR_LOGIN_SERVER --registry-identity system \
  --ingress external --target-port 8000 \
  --min-replicas 1 --max-replicas 1 \
  --secrets openai-key=$OPENAI_API_KEY elevenlabs-key=$ELEVENLABS_API_KEY db-url="$DATABASE_URL" \
  --env-vars \
    ENVIRONMENT=production \
    STORAGE_BACKEND=azure \
    AZURE_STORAGE_ACCOUNT_URL=https://gtlopenaidemostorage.blob.core.windows.net \
    AZURE_STORAGE_CONTAINER=music \
    STORAGE_SIGNED_URLS=false \
    OTEL_ENABLED=false \
    "CORS_ORIGINS=[\"$FRONTEND_ORIGIN\"]" \
    OPENAI_API_KEY=secretref:openai-key \
    ELEVENLABS_API_KEY=secretref:elevenlabs-key \
    DATABASE_URL=secretref:db-url
```

> If ACR pull via managed identity fails, fall back to admin creds:
> `az acr update -n $ACR_NAME --admin-enabled true`, then re-run with
> `--registry-username $(az acr credential show -n $ACR_NAME --query username -o tsv)`
> `--registry-password $(az acr credential show -n $ACR_NAME --query 'passwords[0].value' -o tsv)`.

## Step 4 — Grant the app's identity Blob data access

```bash
PRINCIPAL_ID=$(az containerapp show -n $APP -g $RG --query identity.principalId -o tsv)
az role assignment create \
  --assignee-object-id $PRINCIPAL_ID --assignee-principal-type ServicePrincipal \
  --role "Storage Blob Data Contributor" \
  --scope $STORAGE_ID
```

> Data-plane role (not control-plane "Contributor"). Propagation can take a few
> minutes — early requests may return 403 until it lands. The `music` container
> already exists, so the identity only needs blob read/write.

## Step 5 — Allow Container Apps → Postgres

```bash
az postgres flexible-server firewall-rule create \
  -g $PG_RG -n mcp-registry-postgres \
  --rule-name allow-azure --start-ip-address 0.0.0.0 --end-ip-address 0.0.0.0
```

`0.0.0.0/0.0.0.0` means "allow access from Azure services". TLS is required and is
handled by the app. For stricter isolation use VNet integration + a private
endpoint instead.

## Step 6 — Get the URL & verify

```bash
FQDN=$(az containerapp show -n $APP -g $RG --query properties.configuration.ingress.fqdn -o tsv)
echo "https://$FQDN"

curl https://$FQDN/health     # dependencies.database.status == "healthy"
curl https://$FQDN/docs       # Swagger UI loads
az containerapp logs show -n $APP -g $RG --follow
```

Then drive one render (prompt mode is quickest):

```bash
curl -X POST https://$FQDN/render -H "Content-Type: application/json" \
  -d '{"prompt":"a short upbeat test track","music_length_ms":8000,"title":"deploy smoke test"}'
```

Confirm a `200` with an `id`, then `GET https://$FQDN/render/stream/{id}`. Verify a
new blob appears in the `music` container and a new row exists in `renders`
(`SELECT count(*) FROM renders;`). This proves managed-identity Blob writes and
Postgres access from inside Container Apps.

## Redeploy

```bash
az acr build -r $ACR_NAME -t elevenlabs-music-api:v2 .
az containerapp update -n $APP -g $RG --image $ACR_LOGIN_SERVER/elevenlabs-music-api:v2
```

## Rollback

```bash
az containerapp revision list -n $APP -g $RG -o table
az containerapp revision activate -n $APP -g $RG --revision <previous-revision-name>
```

## Database migrations (future schema changes)

The DB is already at head, so the **initial deploy needs no migration**. When a
future change adds an Alembic revision, apply it **before** rolling the new image,
from any machine that can reach the DB:

```bash
uv run python scripts/init_db.py          # idempotent: ensure DB + alembic upgrade head
# or: uv run alembic upgrade head
```

Do not run migrations at container startup (multiple replicas would race).

## Updating config later

```bash
# Change/add an env var:
az containerapp update -n $APP -g $RG --set-env-vars CORS_ORIGINS="[\"https://new-frontend\"]"

# Rotate a secret:
az containerapp secret set -n $APP -g $RG --secrets db-url="<new-value>"
```
