# Frontend Update: Finetune Support

**Audience:** the coding agent building/maintaining the frontend.
**Companion to:** [`FRONTEND_API_GUIDE.md`](./FRONTEND_API_GUIDE.md) and [`RENDER_API.md`](./RENDER_API.md) — everything there is still accurate. This document is **purely additive**.

## TL;DR — what changed and what you must do

The backend now supports **ElevenLabs music finetunes** (genre/style-specialized models that steer generation).

1. **New endpoint `GET /finetunes`** returns the list of usable finetunes (id + name + genre/tags) so you can build a picker. No ElevenLabs API key is needed client-side — the backend proxies it.
2. **`POST /render` (and the `/render/ws` WebSocket) now accept two optional fields:** `finetune_id` and `finetune_strength`. When present, the render is steered by that finetune.

**There are no breaking changes.** Finetunes are entirely optional:
- If you don't call `/finetunes`, nothing changes.
- If you omit `finetune_id` on `/render`, rendering behaves exactly as before.
- The `/prompt` and `/plan` endpoints are **unaffected** — finetunes apply only at render time.

**What you should build:**
1. Fetch `GET /finetunes` and render a finetune picker (dropdown / searchable list). Include a "None" option.
2. Persist the chosen `finetune_id` (and optional `finetune_strength`) in your render state.
3. Send `finetune_id` (+ optional `finetune_strength`) in the `POST /render` body.

---

## 1. Where finetunes fit in the pipeline

The app is a three-stage pipeline. Finetunes attach at **render only**:

| Stage | Endpoint | Uses finetune? |
| --- | --- | --- |
| Prompt generation | `POST /prompt` | ❌ No |
| Composition plan | `POST /plan` | ❌ No |
| **Render audio** | `POST /render` / `WS /render/ws` | ✅ **Yes** (`finetune_id`) |

**Important consequence for the plan-first workflow:** the composition plan does **not** carry the finetune. If a user picks a finetune and you generate a plan via `/plan`, the finetune is **not** stored in that plan and is **not** echoed back in the render response. **The frontend must hold the user's finetune choice and re-send `finetune_id` on the `/render` call.** Whether the user renders from a raw prompt or from a plan, the finetune is applied the same way — at render time.

---

## 2. New endpoint: `GET /finetunes`

Lists the finetunes available to use with `/render`.

### Request

```
GET /finetunes
```

**Query parameters (all optional):**

| Param | Type | Default | Description |
| --- | --- | --- | --- |
| `model_id` | string | — | Filter to a model, e.g. `music_v2`. **Recommended: pass `music_v2`** since renders use `music_v2` by default. |
| `include_incomplete` | bool | `false` | If `false` (default), only finetunes that finished training (`status: "completed"`) are returned — i.e. only usable ones. Leave this off for a picker. |
| `visibility` | string | — | `private` \| `workspace` \| `public`. |
| `created_by` | string | — | `self` \| `workspace` \| `elevenlabs`. |
| `refresh` | bool | `false` | Bypass the server-side cache and refetch from ElevenLabs. Normally not needed. |
| `cursor` | string | — | Pagination cursor (see `next_cursor` below). |
| `page_size` | int (1–100) | — | Page size to request. |

**Recommended call for a picker:**

```
GET /finetunes?model_id=music_v2
```

### Response `200 OK`

```jsonc
{
  "finetunes": [
    {
      "id": "aslj0pdvdods2agammwb",   // <-- pass THIS as finetune_id on /render
      "name": "Indie Dance",
      "tags": ["Electronic", "House", "Nu-Disco", "Deep House", "Indie Dance", "Dance"],
      "primary_genre": "Indie",
      "model_id": "music_v2",
      "created_at": "2026-07-21T13:22:52.615000Z",  // ISO 8601 (nullable)
      "visibility": "public",
      "created_by": "elevenlabs",
      "status": "completed",           // only "completed" returned unless include_incomplete=true
      "training_progress": 1.0,        // 0.0–1.0 (nullable)
      "failure_reason": null           // string if training failed (nullable)
    }
    // ...more finetunes
  ],
  "count": 37,          // number of finetunes in THIS response (after filtering)
  "has_more": false,    // true if more pages exist
  "next_cursor": null   // pass as ?cursor= to fetch the next page (when has_more)
}
```

**Fields you'll actually use for the picker:** `id` (the value to submit), `name` (label), `primary_genre` and `tags` (grouping/search/badges).

### Errors

| Status | Meaning | Frontend handling |
| --- | --- | --- |
| `500` | Backend misconfigured (no ElevenLabs API key). | Hide the finetune picker; log. This is an ops issue, not user error. |
| `502` | Backend could not reach ElevenLabs. | Show a non-blocking message ("Finetunes unavailable, try again") and let the user render without one. |

### Caching (informational)

The backend caches finetune results in-memory for a few minutes (default 300s), so calling `/finetunes` on every page load is cheap and does **not** hammer ElevenLabs. You generally do **not** need to add your own caching. If you ever need a guaranteed-fresh list (e.g. right after a user created a finetune elsewhere), call `GET /finetunes?refresh=true`.

### TypeScript types

```ts
export interface FinetuneSummary {
  id: string;
  name: string | null;
  tags: string[];
  primary_genre: string | null;
  model_id: string | null;
  created_at: string | null;   // ISO 8601
  visibility: string | null;
  created_by: string | null;
  status: string | null;       // "completed" when usable
  training_progress: number | null;
  failure_reason: string | null;
}

export interface FinetuneListResponse {
  finetunes: FinetuneSummary[];
  count: number;
  has_more: boolean;
  next_cursor: string | null;
}
```

### Fetch helper

```ts
async function listFinetunes(baseUrl: string): Promise<FinetuneSummary[]> {
  const res = await fetch(`${baseUrl}/finetunes?model_id=music_v2`);
  if (!res.ok) throw new Error(`Failed to load finetunes: ${res.status}`);
  const data: FinetuneListResponse = await res.json();
  return data.finetunes;
}
```

---

## 3. Updated `/render` request (adds `finetune_id` / `finetune_strength`)

Two new **optional** fields on the existing `/render` request body. Everything else is unchanged.

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `finetune_id` | string \| null | `null` | The `id` from `GET /finetunes`. Works in **both** prompt mode (`prompt`) and plan mode (`chunks`). |
| `finetune_strength` | number \| null | `null` | How strongly the finetune influences generation. Range **0.0–1.0** (API default is 1.0 / full strength; lower = softer). **Only valid when `finetune_id` is also set** — sending it alone is a `422` validation error. |

> Note on naming: the API field is `finetune_strength`. (ElevenLabs docs sometimes call this "finetune influence"; the backend exposes it as `finetune_strength`, clamped 0.0–1.0.)

### Example — prompt mode with a finetune

```jsonc
POST /render
{
  "prompt": "An upbeat indie dance track with a driving four-on-the-floor beat",
  "music_length_ms": 20000,
  "finetune_id": "aslj0pdvdods2agammwb",
  "finetune_strength": 0.8            // optional
}
```

### Example — plan mode with a finetune

```jsonc
POST /render
{
  "chunks": [ /* composition plan from POST /plan */ ],
  "title": "My Track",
  "finetune_id": "aslj0pdvdods2agammwb"
}
```

### Example — no finetune (unchanged behavior)

```jsonc
POST /render
{
  "prompt": "An upbeat indie dance track",
  "music_length_ms": 20000
}
```

### Response

**The `/render` response shape is unchanged.** `finetune_id` is a pure input-side steering parameter — it is **not** echoed back in the response and is **not** stored inside the returned `composition_plan` or `song_metadata`. If you want to remember which finetune produced a track, **store it client-side** alongside the render `id`.

### Validation errors (`422`)

- `finetune_strength` provided without `finetune_id` → `422` with detail `"'finetune_strength' can only be used together with 'finetune_id'."`
- `finetune_strength` outside `0.0`–`1.0` → `422` (Pydantic range error).

### Runtime errors (bad finetune id)

The backend does **not** pre-validate that a `finetune_id` exists — ElevenLabs does. If you submit a bad/nonexistent id, the render currently fails and surfaces as **`500`** from `/render` (message: `"Music rendering failed: ..."`).

**Mitigation (recommended):** only ever submit ids that came from `GET /finetunes`, so this can't happen through the UI.

> If you'd prefer a bad `finetune_id` to come back as a clean `4xx` with a friendly message instead of `500`, ask the backend team — that mapping is a small, agreed follow-up, not yet implemented.

---

## 4. WebSocket render (`/render/ws`)

Finetunes work identically over the streaming WebSocket path. The `finetune_id` / `finetune_strength` fields go inside the same render request object you already send (the payload nested under `composition_plan` in `RenderWebSocketRequest`). No protocol change beyond adding those two optional fields. See [`frontend-websocket-integration.md`](./frontend-websocket-integration.md) for the base protocol.

---

## 5. Suggested UX

1. **Load finetunes** with `GET /finetunes?model_id=music_v2` when the render screen mounts.
2. **Render a picker** with a **"None (default model)"** option first, then group/list finetunes by `primary_genre`, labeled with `name` and optionally `tags` as badges.
3. **On render**, if a finetune is selected, include `finetune_id` in the `/render` body. Only include `finetune_strength` if you expose a strength slider (0.0–1.0); otherwise omit it and the API uses full strength.
4. **Handle the picker gracefully** if `/finetunes` returns `502` — fall back to rendering without a finetune.
5. **Remember the choice** per track (store `finetune_id` in your render/history state) since the backend doesn't persist or echo it.

---

## 6. Quick reference

| Thing | Value |
| --- | --- |
| List finetunes | `GET /finetunes?model_id=music_v2` |
| Field to submit | `finetune_id` (from a finetune's `id`) |
| Optional strength | `finetune_strength` (0.0–1.0, requires `finetune_id`) |
| Applies at | `POST /render` and `WS /render/ws` only |
| Not applicable to | `POST /prompt`, `POST /plan` |
| Echoed in render response? | No — store client-side |
| Force-fresh finetune list | `GET /finetunes?refresh=true` |
| Interactive API docs | `GET /docs` (see the **Finetunes** and **Music Render** tags) |
