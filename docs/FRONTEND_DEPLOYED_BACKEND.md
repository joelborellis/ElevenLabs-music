# Frontend Update: Point at the Deployed Backend

**Audience:** the coding agent maintaining the React frontend.
**Goal:** switch the frontend from the local backend (`http://localhost:8000`) to the deployed Azure backend, over HTTPS/WSS.

> Read alongside [`FRONTEND_API_GUIDE.md`](./FRONTEND_API_GUIDE.md) (full contract)
> and [`FRONTEND_API_CHANGES_STORAGE.md`](./FRONTEND_API_CHANGES_STORAGE.md)
> (the render-`id` changes). **This document only changes the base URLs** — the
> API contract is identical to what those docs describe.

## 1. Production endpoints

| Item | Value |
| --- | --- |
| **HTTPS base URL** | `https://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io` |
| **WebSocket base URL** | `wss://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io` |
| Health check | `GET {base}/health` |
| Swagger / schema | `{base}/docs`, `{base}/openapi.json` |

Note the schemes: **`https://`** for REST and **`wss://`** for the render
WebSocket (`{wsBase}/render/ws`). Do not mix `ws://` with an `https` page — a
secure page requires `wss://`.

## 2. Make the base URL configurable (do this — don't hardcode)

Use an environment variable so local vs. production is a build-time switch.

**Vite** (`.env.development` / `.env.production`):
```dotenv
# .env.development
VITE_API_BASE_URL=http://localhost:8000
VITE_WS_BASE_URL=ws://localhost:8000

# .env.production
VITE_API_BASE_URL=https://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io
VITE_WS_BASE_URL=wss://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io
```

**Create React App** — same idea with `REACT_APP_API_BASE_URL` / `REACT_APP_WS_BASE_URL`.

Central helper:
```ts
export const API_BASE = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const WS_BASE  = import.meta.env.VITE_WS_BASE_URL  ?? "ws://localhost:8000";

// If you don't want a separate WS var, derive it from API_BASE:
// const WS_BASE = API_BASE.replace(/^http/, "ws");
```

Then build every call from `API_BASE` / `WS_BASE`:
```ts
await fetch(`${API_BASE}/prompt`, { ... });
const ws = new WebSocket(`${WS_BASE}/render/ws`);
```

**Reminder (from the storage changes doc):** the render response's
`download_url` / `stream_url` are **server-relative** — prepend `API_BASE`:
```ts
<audio src={`${API_BASE}${res.stream_url}`} controls />
<a href={`${API_BASE}${res.download_url}`}>Download</a>
```

## 3. CORS — important

The backend only allows browser requests from origins in its allow-list.
Currently it permits the **localhost dev origins** (`http://localhost:3000`,
`5173`, `8000`). That means:

- ✅ Running the frontend **locally** (Vite/CRA) against the **deployed** backend works today.
- ❌ Once you **deploy the frontend** to a real domain, that domain must be added
  to the backend's `CORS_ORIGINS`, or browser calls will fail with a CORS error.

**Action:** when you know the deployed frontend URL, tell the backend owner (or
run) so it's allow-listed:
```bash
az containerapp update -n elevenlabs-music-api -g ElevenLabsMusic \
  --set-env-vars 'CORS_ORIGINS=["https://<your-frontend-domain>"]'
```
`credentials` are allowed and all methods/headers are permitted, so no other CORS
config is needed on the client.

## 4. Everything else is unchanged

- Request/response shapes, enums, validation, error bodies, WebSocket protocol,
  progress stages, and the `X-Request-ID` header are exactly as documented in the
  two companion guides. No payload changes.
- Latencies are the same (prompt ~10–60 s, plan ~5–30 s, render ~15–120 s+) —
  keep the WebSocket-based progress UI for `/render/ws`.
- The API is HTTPS with a valid Azure certificate; no special TLS handling needed.
- **Cold start:** the app runs at 1 replica; if it has been idle it is still warm
  (min-replicas=1), so no significant cold-start delay is expected. If you ever
  see a slow first request, it's the ElevenLabs generation time, not the platform.

## 5. Quick verification after switching

```ts
// Should return { status: "healthy", ... }
await fetch(`${API_BASE}/health`).then(r => r.json());
```
Then run one render in prompt mode and confirm playback via `stream_url`.

## 6. Migration checklist

- [ ] Add `VITE_API_BASE_URL` / `VITE_WS_BASE_URL` (or CRA equivalents) for dev and prod.
- [ ] Replace any hardcoded `http://localhost:8000` / `ws://localhost:8000` with `API_BASE` / `WS_BASE`.
- [ ] Ensure `download_url` / `stream_url` are prefixed with `API_BASE`.
- [ ] Use `wss://` for the render WebSocket in production.
- [ ] When the frontend is deployed, get its origin added to backend `CORS_ORIGINS`.
