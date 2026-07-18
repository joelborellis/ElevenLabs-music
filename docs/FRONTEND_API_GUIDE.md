# Backend API Guide (for the React Frontend)

This document describes every backend endpoint the frontend can use — inputs, outputs, error shapes, and recommended user flows — so you can design the React app's screens and data flow against a stable contract.

> Source of truth: this reflects the FastAPI backend in this repo. A live, always-current schema is also available at **`/openapi.json`** and interactive docs at **`/docs`** when the server is running — you can generate a typed client from the former.

---

## 1. Basics

| Item | Value |
| --- | --- |
| Base URL (dev) | `http://localhost:8000` |
| WebSocket URL (dev) | `ws://localhost:8000` |
| Content type (requests/responses) | `application/json` (audio endpoints return `audio/mpeg`) |
| Interactive docs | `GET /docs` (Swagger UI), `GET /redoc` |
| Machine schema | `GET /openapi.json` |

### CORS
The backend allows browser requests from these origins out of the box:
- `http://localhost:3000` (Create React App)
- `http://localhost:5173` (Vite)
- `http://localhost:8000`

Credentials are allowed and all methods/headers are permitted. If you run the frontend on a different port, that origin must be added to the backend `cors_origins` list (in `main.py`).

### Request tracing
- Every response includes an **`X-Request-ID`** header.
- You may send your own `X-Request-ID` request header; it will be echoed back. Otherwise the server generates one.
- Most JSON bodies also include a `request_id` field for correlation/logging. Surface it in error toasts so issues are traceable.

### Timestamps
All `timestamp` fields are ISO 8601 UTC strings (e.g. `2025-12-22T10:30:00.123456`).

---

## 2. The generation pipeline (mental model)

The app is a three-stage pipeline. Each stage is a separate endpoint, and the output of one feeds the next:

```
   ┌─────────────┐        ┌───────────┐        ┌─────────────┐
   │ POST /prompt│  ───►  │ POST /plan│  ───►  │ POST /render│  ───►  audio file
   │ presets →   │ prompt │ prompt →  │  plan  │ plan/prompt │  (mp3, download/stream)
   │ prompt text │        │ comp plan │        │ → audio     │
   └─────────────┘        └───────────┘        └─────────────┘
```

**Two important flexibilities for your UX design:**

1. **`/render` accepts EITHER a composition plan OR a raw prompt.** So you can offer:
   - **Guided/advanced flow:** `/prompt` → `/plan` → (let the user review/edit the plan) → `/render`.
   - **Quick flow:** `/prompt` → `/render` with just the prompt (skip the plan step), or even a user-typed prompt straight to `/render`.
2. **Rendering is long-running.** Prefer the **WebSocket render** (`/render/ws`) for real-time progress; use the plain `POST /render` only if you don't need progress UI.

Approximate latencies to design loading states around:
- `/prompt`: ~10–60s (calls an LLM agent that may do a web search).
- `/plan`: ~5–30s.
- `/render`: ~15–120s+ depending on length (design a progress bar; use the WebSocket).

---

## 3. Endpoint reference

### 3.1 `POST /prompt` — Generate a music prompt from preset selections

Turns the "three-choice wizard" selections into a polished prompt (plus a title and description).

**Request body**

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `project_blueprint` | enum (string) | ✅ | — | Use case / structure. See table below. |
| `sound_profile` | enum (string) | ✅ | — | Genre / sonic character. See table below. |
| `delivery_and_control` | enum (string) | ✅ | — | Workflow / output style. See table below. |
| `instrumental_only` | boolean | ❌ | `false` | Force instrumental regardless of blueprint. |
| `user_narrative` | string \| null | ❌ | `null` | Freeform story/occasion/people to shape lyrics & tone. May contain URLs (the agent will fetch them). |

**Preset enum values** (use these exact string IDs; build your wizard UI from them):

| `project_blueprint` | `sound_profile` | `delivery_and_control` |
| --- | --- | --- |
| `ad_brand_fast_hook` | `bright_pop_electro` | `exploratory_iterate` |
| `podcast_voiceover_loop` | `dark_trap_night` | `balanced_studio` |
| `video_game_action_loop` | `lofi_cozy` | `blueprint_plan_first` |
| `meditation_sleep` | `epic_cinematic` | `live_one_take` |
| `standalone_song_mini` | `indie_live_band` | `isolation_stems` |

**Response `200`**

```jsonc
{
  "prompt": "Create a 30-second uplifting electronic track...",  // paste-ready music prompt
  "title": "Bright Pop Anthem",                                   // short catchy title (may be null)
  "description": "A 30-second uplifting electronic ad spot...",   // 1-2 sentence summary (may be null)
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2025-12-22T10:30:00Z",
  "input_parameters": {                                           // echoes what you sent
    "project_blueprint": "ad_brand_fast_hook",
    "sound_profile": "bright_pop_electro",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": null
  }
}
```

**Frontend notes**
- The `prompt` string is what you pass to `/plan` (as `prompt`) or `/render` (as `prompt`).
- `title` is useful to pre-fill a "track name" field and is later used to name the rendered file.
- Errors: `422` if an enum value is invalid; `500` on generation failure.

---

### 3.2 `POST /plan` — Generate a composition plan from a prompt

Expands a prompt into a structured, editable plan (a list of "chunks"/sections). This is the step to expose if you want users to review or fine-tune structure before rendering.

**Request body**

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `prompt` | string | ✅ | — | Text description of the desired music. |
| `music_length_ms` | integer \| null | ❌ | parsed from prompt, else `30000` | **Range 1000–300000** (1–300 s). |

**Response `200`** — the composition plan (returned directly, not wrapped):

```jsonc
{
  "chunks": [
    {
      "text": "[Intro]",                       // section marker and/or lyrics
      "positive_styles": ["120 BPM", "bright synths", "uplifting electronic pop"],
      "negative_styles": ["vocals"],
      "duration_ms": 6000,
      "context_adherence": "high"              // may be null
      // NOTE: extra music_v2 fields may also appear (e.g. conditioning_ref, condition_strength)
    }
    // ...more chunks
  ]
}
```

**Frontend notes**
- The whole `{ "chunks": [...] }` object is directly usable as the plan-mode `/render` body (just add an optional `title`).
- `chunks` is an **editable** structure — a good place for an "edit sections" UI (reorder, tweak styles, change durations). Each chunk's `duration_ms` must be **≥ 3000** to be renderable (see `/render` validation).
- Errors: `422` for a missing prompt or out-of-range `music_length_ms`; `500` on generation failure.

---

### 3.3 `POST /render` — Render audio (single request, no progress)

Renders audio from **either** a composition plan **or** a prompt. Returns metadata + URLs to fetch the audio. Use this when you don't need a progress bar; otherwise use the WebSocket (§3.6).

**Request body** — provide EITHER `prompt` OR `chunks` (mutually exclusive):

| Field | Type | Required | Default | Notes |
| --- | --- | --- | --- | --- |
| `prompt` | string \| null | one of prompt/chunks | `null` | Text-to-music. **Mutually exclusive with `chunks`.** |
| `chunks` | Chunk[] | one of prompt/chunks | `[]` | A composition plan (from `/plan`). **Mutually exclusive with `prompt`.** |
| `music_length_ms` | integer \| null | ❌ | `null` | **Only valid with `prompt`.** Range **3000–600000** (3–600 s). |
| `model_id` | string | ❌ | `"music_v2"` | `"music_v1"` or `"music_v2"`. |
| `force_instrumental` | boolean | ❌ | `false` | Guarantee an instrumental result. |
| `store_for_inpainting` | boolean | ❌ | `false` | Store the song to allow later inpainting. |
| `with_timestamps` | boolean | ❌ | `false` | Return word-level timestamps. |
| `sign_with_c2pa` | boolean | ❌ | `false` | Add C2PA provenance signature. |
| `output_format` | string \| null | ❌ | `null` (API default) | e.g. `"mp3_44100_128"`, `"pcm_44100"`. |
| `title` | string \| null | ❌ | `null` | Local-only; used to name the saved file. Not sent to ElevenLabs. |

**Validation rules (all return `422`):**
- Neither `prompt` nor `chunks` provided.
- Both `prompt` and `chunks` provided.
- `music_length_ms` provided without `prompt`.
- Any chunk `duration_ms` < 3000, or total duration outside 3000–600000 ms.

**Response `200`**

```jsonc
{
  "filename": "bright_pop_anthem_abc123.mp3",
  "file_path": "/output/music/bright_pop_anthem_abc123.mp3",  // server path (informational)
  "download_url": "/render/download/bright_pop_anthem_abc123.mp3",
  "stream_url": "/render/stream/bright_pop_anthem_abc123.mp3", // may be null on the REST path
  "content_type": "audio/mpeg",
  "file_size_bytes": 524288,
  "composition_plan": { "chunks": [ /* final plan, may include generated lyrics */ ] },
  "song_metadata": {                                          // passthrough from ElevenLabs; may be null
    "title": null, "description": null, "genres": [], "languages": [], "is_explicit": false
  },
  "request_id": "uuid",
  "timestamp": "2025-01-01T00:00:00"
}
```

**Frontend notes**
- To play/download, prepend the base URL to `download_url`/`stream_url` (they are server-relative paths).
- `composition_plan` in the response is the *final* plan and may contain generated lyrics — useful to display alongside the player.

---

### 3.4 `GET /render/download/{filename}` — Download a rendered file

- **Input:** `filename` path param (from a render response).
- **Output:** `audio/mpeg` file with `Content-Disposition: attachment`. Supports range requests (`Accept-Ranges: bytes`).
- **Errors:** `404` if the file doesn't exist.
- **Frontend use:** wire to a "Download" button (`<a href>` or `window.location`).

### 3.5 `GET /render/stream/{filename}` — Stream a rendered file for playback

- **Input:** `filename` path param.
- **Output:** `audio/mpeg` stream, `Content-Disposition: inline`, with `Content-Length` and `Accept-Ranges: bytes` (seekable).
- **Errors:** `404` if the file doesn't exist.
- **Frontend use:** set as the `src` of an `<audio>` element for in-app playback.

---

### 3.6 `WS /render/ws` — Render with real-time progress (recommended)

Same render capability as `POST /render`, but streams progress updates over a WebSocket. This is the endpoint to build the render progress UI around.

**Protocol / message sequence**

1. Client connects to `ws://<host>/render/ws`.
2. Server immediately sends a `progress` message with `stage: "connected"`.
3. Client sends a **render request** message.
4. Server streams multiple `progress` messages.
5. Server sends one terminal message: `result` (success) or `error` (failure), then closes the connection.

**Client → server message**

```jsonc
{
  "type": "render",
  "composition_plan": {
    // This object is a full /render request body (see §3.3):
    // EITHER { "title": "...", "chunks": [...] }  (plan mode)
    // OR     { "title": "...", "prompt": "...", "music_length_ms": 8000, ... }  (prompt mode)
    "title": "My Track",
    "chunks": [ /* ... */ ]
  }
}
```
> Note: the field is named `composition_plan` but it carries the entire render request (including the prompt-mode fields and pass-through params).

**Server → client messages**

`progress`:
```jsonc
{ "type": "progress", "stage": "generating", "progress_percent": 35,
  "message": "Generating music...", "timestamp": "..." }
```

`result` (terminal, success): `data` is the same shape as the `POST /render` `200` response.
```jsonc
{ "type": "result", "data": { "filename": "...", "download_url": "...", "stream_url": "...", /* ...RenderResponse... */ } }
```

`error` (terminal, failure):
```jsonc
{ "type": "error", "error_code": "VALIDATION_ERROR", "message": "Provide either 'prompt' or 'chunks'.", "timestamp": "..." }
```

**Progress stages (for a determinate progress bar)**

| stage | percent | meaning |
| --- | --- | --- |
| `connected` | 0 | socket open, awaiting request |
| `validating` | 5 | validating the request |
| `validated` | 10 | request accepted |
| `generating` | 15 → ~65 | ElevenLabs generation in progress (increments over time) |
| `processing` | → 75 | processing API response |
| `saving` | → 90 | writing audio file |
| `extracting` | → 95 | extracting metadata |
| `complete` | 100 | done (a `result` message follows) |

**Error codes**

| `error_code` | When |
| --- | --- |
| `INVALID_REQUEST` | Message wasn't valid JSON, or the envelope is malformed (e.g. wrong/missing `type`). |
| `VALIDATION_ERROR` | The composition plan / render request failed validation (empty, both sources, bad durations, etc.). |
| `SERVER_ERROR` | Unexpected error during rendering. |

**Frontend notes**
- Treat `result` and `error` as terminal; the server closes the socket afterward. Handle unexpected close (`onclose`) as a failure state.
- The `result.data.download_url` / `stream_url` are ready to use immediately.

---

### 3.7 Utility / health endpoints

Not part of the generation flow, but handy for status indicators or environment checks.

| Method & path | Returns |
| --- | --- |
| `GET /` | Service info + a map of available endpoints + `request_id`. |
| `GET /health` | `{ status, timestamp, service, version, dependencies }` — `200` healthy, `503` degraded. (Note: dependency checks are currently stubs.) |
| `GET /ready` | `{ ready: true, timestamp }` (K8s readiness). |
| `GET /alive` | `{ alive: true, timestamp }` (K8s liveness). |

---

## 4. Error handling

There are two error-body shapes depending on where the error originates. Design your API client to handle both.

**A) Request/body validation & uncaught errors** (global handlers) — used for most `422` (invalid body) and generic `500`:
```jsonc
{ "error": "Validation Error", "message": "Invalid request parameters",
  "request_id": "uuid", "timestamp": "..." }
```

**B) Route-raised errors** (`HTTPException`) — e.g. `/render` plan validation, `/prompt` & `/plan` `500`s, `404` on file endpoints. The body is under `detail`, which may be a string or an object:
```jsonc
{ "detail": "Composition plan must have at least one chunk. ..." }
// or
{ "detail": { "error": "Generation Error", "message": "...", "request_id": "uuid" } }
```

**Status codes summary**

| Code | Meaning |
| --- | --- |
| `200` | Success. |
| `404` | Audio file not found (download/stream). |
| `422` | Validation error (bad enum, missing/`out-of-range` field, mutual-exclusivity violation, bad plan). |
| `500` | Server/generation error (include `request_id` when reporting). |
| `503` | Health check degraded. |

Recommended client behavior: read `X-Request-ID`/`request_id`, show a user-friendly message, and log the raw detail for support.

---

## 5. Suggested TypeScript types

Drop-in starting point for the frontend (adjust as your client evolves):

```ts
// ---- Presets (POST /prompt) ----
export type ProjectBlueprint =
  | "ad_brand_fast_hook" | "podcast_voiceover_loop" | "video_game_action_loop"
  | "meditation_sleep" | "standalone_song_mini";
export type SoundProfile =
  | "bright_pop_electro" | "dark_trap_night" | "lofi_cozy"
  | "epic_cinematic" | "indie_live_band";
export type DeliveryAndControl =
  | "exploratory_iterate" | "balanced_studio" | "blueprint_plan_first"
  | "live_one_take" | "isolation_stems";

export interface PromptRequest {
  project_blueprint: ProjectBlueprint;
  sound_profile: SoundProfile;
  delivery_and_control: DeliveryAndControl;
  instrumental_only?: boolean;      // default false
  user_narrative?: string | null;   // default null
}
export interface PromptResponse {
  prompt: string;
  title: string | null;
  description: string | null;
  request_id: string;
  timestamp: string;
  input_parameters: PromptRequest;
}

// ---- Plan (POST /plan) ----
export interface Chunk {
  text: string;
  positive_styles: string[];
  negative_styles: string[];
  duration_ms: number;              // must be >= 3000 to render
  context_adherence?: string | null;
  [extra: string]: unknown;         // music_v2 may add fields
}
export interface PlanRequest {
  prompt: string;
  music_length_ms?: number | null;  // 1000..300000
}
export interface PlanResponse {
  chunks: Chunk[];
}

// ---- Render (POST /render and WS) ----
export interface RenderRequest {
  // provide EXACTLY ONE of prompt | chunks
  prompt?: string | null;
  chunks?: Chunk[];
  music_length_ms?: number | null;  // 3000..600000, only with prompt
  model_id?: "music_v1" | "music_v2";
  force_instrumental?: boolean;
  store_for_inpainting?: boolean;
  with_timestamps?: boolean;
  sign_with_c2pa?: boolean;
  output_format?: string | null;    // e.g. "mp3_44100_128"
  title?: string | null;            // names the output file
}
export interface RenderResponse {
  filename: string;
  file_path: string;
  download_url: string;             // server-relative
  stream_url: string | null;
  content_type: string;            // "audio/mpeg"
  file_size_bytes: number;
  composition_plan: { chunks: Chunk[] } | null;
  song_metadata: Record<string, unknown> | null;
  request_id: string;
  timestamp: string;
}

// ---- WebSocket messages (/render/ws) ----
export type WsClientMessage = { type: "render"; composition_plan: RenderRequest };
export type WsProgress = { type: "progress"; stage: string; progress_percent: number; message: string; timestamp: string };
export type WsResult   = { type: "result"; data: RenderResponse };
export type WsError    = { type: "error"; error_code: "INVALID_REQUEST" | "VALIDATION_ERROR" | "SERVER_ERROR"; message: string; timestamp: string };
export type WsServerMessage = WsProgress | WsResult | WsError;
```

---

## 6. Recommended frontend flows

**Flow A — Guided wizard (most control):**
1. Wizard screens collect the three presets + optional instrumental toggle + optional narrative → `POST /prompt`.
2. Show generated `prompt`/`title`/`description`; let the user tweak the prompt text.
3. `POST /plan` → render an editable list of chunks (sections).
4. User reviews/edits chunks → open a WebSocket to `/render/ws`, send `{ type: "render", composition_plan: { title, chunks } }`.
5. Drive a progress bar from `progress` messages; on `result`, play via `stream_url` and offer `download_url`.

**Flow B — Quick generate (fewer steps):**
1. Presets/narrative → `POST /prompt`.
2. `/render/ws` in **prompt mode**: send `{ type: "render", composition_plan: { title, prompt, music_length_ms } }` (skip `/plan`).
3. Progress → `result` → play/download.

**Flow C — Power user / direct:**
- Let advanced users type a raw prompt and render it directly (Flow B step 2), or paste/import a composition plan and render it (plan mode).

**Cross-cutting UI considerations**
- Long operations: always use `/render/ws` for the render step so users see progress; disable submit while in-flight.
- Persist `request_id`s from responses/errors for support.
- Playback: use `stream_url` in an `<audio>` element; use `download_url` for saving.
- Validation mirroring: enforce the mutual-exclusivity and duration rules client-side (§3.3) to avoid round-trip `422`s.
