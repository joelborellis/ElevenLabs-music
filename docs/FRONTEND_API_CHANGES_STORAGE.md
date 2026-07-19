# Frontend Update: Render IDs + Blob/DB Storage

**Audience:** the coding agent maintaining the React frontend.
**Companion to:** [`FRONTEND_API_GUIDE.md`](./FRONTEND_API_GUIDE.md) — that guide is still accurate **except** for the `/render` response shape and the download/stream URLs, which this document supersedes.

## TL;DR — what changed and what you must do

The backend now stores rendered audio in **Azure Blob Storage** and render metadata in a **PostgreSQL database**. Files are no longer served from a local disk path. For the frontend this means **one substantive change**:

- **Every render now has a stable `id`** (a UUID). It is the primary handle for a track.
- **`download_url` and `stream_url` are now built from that `id`**, e.g. `/render/download/{id}` instead of `/render/download/{filename}`.

**What you should do:**
1. Add `id: string` (and `duration_ms: number | null`) to your `RenderResponse` type.
2. **Always use the `download_url` / `stream_url` returned in the response** — do not construct these URLs yourself from `filename`. (If you already do this, you're done — nothing breaks.)
3. Persist the `id` wherever you track a rendered track (state, history, deep links).

There are **no breaking changes to the request bodies** for `/prompt`, `/plan`, or `/render`, and **no change to how audio is fetched/played** (same-origin relative URLs, `audio/mpeg`, seekable). Audio bytes are proxied through the backend from Blob storage — the browser never talks to Azure directly and needs no Azure credentials.

---

## 1. Updated `/render` response (§3.3 of the main guide)

```jsonc
{
  "id": "beb37911-fc19-4cf0-9cc1-be8ffcc48566",   // NEW — stable render id (UUID). Primary handle.
  "filename": "bright_pop_anthem_abc123.mp3",       // still present (display / download filename)
  "file_path": "https://<acct>.blob.core.windows.net/music/bright_pop_anthem_abc123.mp3",
                                                    // CHANGED — now the canonical storage URL (blob URL
                                                    // or file:// in local dev). INFORMATIONAL ONLY —
                                                    // it is NOT browser-fetchable (the container is private).
                                                    // Nullable. Do NOT use for playback/download.
  "download_url": "/render/download/beb37911-...",  // CHANGED — now id-based. Use as-is.
  "stream_url":   "/render/stream/beb37911-...",    // CHANGED — now id-based AND now always populated
                                                    // on the REST path too (was null before).
  "content_type": "audio/mpeg",
  "file_size_bytes": 524288,
  "duration_ms": 30000,                             // NEW — total duration in ms (nullable)
  "composition_plan": { "chunks": [ /* final plan */ ] },
  "song_metadata": { /* passthrough from ElevenLabs; may be null */ },
  "request_id": "uuid",
  "timestamp": "2026-07-19T16:00:33.703867"
}
```

**Field-by-field delta**

| Field | Change | Frontend guidance |
| --- | --- | --- |
| `id` | **Added** | Store it. Use for playback/download URLs, deep links, and future history. |
| `duration_ms` | **Added** (nullable) | Nice for showing track length / sizing a waveform. Fall back gracefully if `null`. |
| `download_url` | Now `/render/download/{id}` | Use the value verbatim; prepend the base URL. |
| `stream_url` | Now `/render/stream/{id}`, **now non-null on REST too** | Use the value verbatim; set as `<audio src>`. |
| `file_path` | Now a storage URL (blob/`file://`), nullable | **Informational only.** Never fetch it from the browser (private container). |
| everything else | unchanged | — |

---

## 2. Updated download / stream endpoints (§3.4–3.5)

The path parameter is now an **identifier** that resolves by render `id`, with a **filename fallback** for backward compatibility.

- `GET /render/download/{identifier}` → `audio/mpeg`, `Content-Disposition: attachment`, `Content-Length` set, `Accept-Ranges: bytes`.
- `GET /render/stream/{identifier}` → `audio/mpeg`, `Content-Disposition: inline`, `Content-Length` set, `Accept-Ranges: bytes` (seekable).
- `{identifier}` = the render `id` (preferred) **or** a `filename` (legacy — still works).
- **Errors:** `404` if no matching render exists **or** the audio object is missing from storage. The `404` body is `{ "detail": "Render not found: ..." }`.

**Backward compatibility:** if your current code calls `/render/download/{filename}`, it keeps working — the backend falls back to a filename lookup. You don't have to change it, but prefer `id` going forward (filenames are not guaranteed unique long-term; ids are).

---

## 3. Updated WebSocket result (§3.6)

No protocol change. The terminal `result` message's `data` is the same shape as the REST response, so it now **also includes `id`, `duration_ms`, id-based `download_url`/`stream_url`, and a populated `stream_url`**:

```jsonc
{
  "type": "result",
  "data": {
    "id": "….",
    "download_url": "/render/stream/…" ,   // id-based
    "stream_url": "/render/stream/…",       // id-based
    "duration_ms": 30000,
    /* …rest of RenderResponse… */
  }
}
```

Progress stages and error codes are unchanged. Note the `saving` stage (→90%) now means "uploading to Blob storage" — no UI change needed, but the label "Saving…" is still accurate.

---

## 4. Updated TypeScript types (replace the `RenderResponse` in §5)

```ts
export interface RenderResponse {
  id: string;                       // NEW — stable render id (UUID)
  filename: string;
  file_path: string | null;         // CHANGED — storage URL/URI, informational only (not fetchable)
  download_url: string;             // id-based, server-relative — use verbatim
  stream_url: string | null;        // id-based, server-relative — now populated on REST too
  content_type: string;             // "audio/mpeg"
  file_size_bytes: number;
  duration_ms: number | null;       // NEW
  composition_plan: { chunks: Chunk[] } | null;
  song_metadata: Record<string, unknown> | null;
  request_id: string;
  timestamp: string;
}
```

Everything else in §5 (`PromptRequest/Response`, `PlanRequest/Response`, `RenderRequest`, `Chunk`, WS message types) is unchanged. `WsResult` already references `RenderResponse`, so updating the interface above is sufficient.

---

## 5. Recommended usage pattern

```ts
const res = await fetch(`${BASE_URL}/render`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify(renderRequest),
}).then(r => r.json() as Promise<RenderResponse>);

// Store the id as the track's canonical handle.
const track = {
  id: res.id,
  title: renderRequest.title ?? res.filename,
  durationMs: res.duration_ms,
  // Build absolute URLs from the server-relative values the backend returned:
  streamUrl: `${BASE_URL}${res.stream_url}`,
  downloadUrl: `${BASE_URL}${res.download_url}`,
};

// Playback:  <audio src={track.streamUrl} controls />
// Download:  <a href={track.downloadUrl}>Download</a>
```

**Do:** use `res.download_url` / `res.stream_url` as returned.
**Don't:** build URLs from `filename` or `file_path`, and don't try to fetch `file_path` (the blob URL) directly — the container is private.

---

## 6. Not yet available (roadmap note)

- There is **no `GET /render` list/history endpoint yet**. Metadata for every render is now persisted (id, size, duration, plan, timestamps), so a "your renders" gallery is feasible — but the frontend can't fetch a list until that endpoint is added on the backend. Don't build UI that assumes it exists; ask for it if you need it.
- `/health` now performs a **real database connectivity check** (the `dependencies.database` status is live, no longer a stub). The `cache` entry is still a stub. Safe to keep using `/health` for a status indicator.

---

## 7. Migration checklist for the frontend

- [ ] Add `id` and `duration_ms` to the `RenderResponse` type; make `file_path` nullable.
- [ ] Ensure all playback/download links come from `res.download_url` / `res.stream_url` (not hand-built from `filename`).
- [ ] Store `res.id` as the canonical per-track identifier in app state.
- [ ] (Optional) Display `duration_ms` as a formatted length.
- [ ] No changes needed to `/prompt`, `/plan`, request bodies, WS protocol, CORS, or error handling.
