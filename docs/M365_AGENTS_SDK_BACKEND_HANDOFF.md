# Microsoft 365 Agents SDK Music Agent: Backend Handoff

## Purpose

This document is the implementation brief for the coding agent building a Microsoft 365 Agents SDK agent that is surfaced in Microsoft 365 Copilot Chat and Microsoft Teams.

The M365 agent must let a user:

1. Choose an ElevenLabs music finetune.
2. Describe the song they want.
3. Choose the song's use case and generation workflow.
4. Generate a professional music prompt.
5. Generate a composition plan.
6. Render the finished audio.
7. Play or download the result from the conversation.

The Agents SDK project is already scaffolded. Implement the integration against the backend contract in this document. Do not place OpenAI, ElevenLabs, database, or storage credentials in the M365 client or an Adaptive Card. The music backend owns those integrations.

The current live OpenAPI document is always the final machine-readable source of truth:

- Production OpenAPI: `https://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io/openapi.json`
- Production Swagger UI: `https://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io/docs`
- Local OpenAPI: `http://localhost:8000/openapi.json`

## Base URLs

Configure the backend URL in the agent service's environment. Do not scatter or hardcode it through handlers.

| Environment | REST base URL | WebSocket base URL |
| --- | --- | --- |
| Local | `http://localhost:8000` | `ws://localhost:8000` |
| Production | `https://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io` | `wss://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io` |

Suggested configuration names:

```dotenv
MUSIC_API_BASE_URL=https://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io
MUSIC_API_WS_URL=wss://elevenlabs-music-api.politerock-e572f8fa.southcentralus.azurecontainerapps.io
```

All request and response bodies are JSON except the audio stream/download responses.

## Recommended Agent Architecture

Treat the FastAPI backend as a set of deterministic application tools called by the M365 agent service. The language model may understand the user's intent and collect missing values, but code must own API calls, enum mapping, state transitions, validation, and retry decisions.

```text
User in M365 Chat or Teams
        |
        v
Microsoft 365 Agents SDK activity handler
        |
        +-- conversation/user state
        +-- Adaptive Cards and normal messages
        +-- typed Music API client
                 |
                 v
       FastAPI music backend
          /finetunes
          /prompt
          /plan
          /render
                 |
                 v
        ElevenLabs + storage
```

Use a typed `MusicApiClient` or equivalent service with methods similar to:

```text
listFinetunes(options)
generatePrompt(request)
generatePlan(request)
renderMusic(request)
getAudioStream(identifier)
```

Keep transport code out of message and card handlers. The handler should translate an activity into an application command, update conversation state, call the typed client, then send or update the user-facing activity.

## Required Conversation State

Persist generation state using the storage/state facilities already selected in the Agents SDK project. Do not rely only on process memory because Teams and M365 requests can land on different instances or resume in a later turn.

Store at least:

```text
selectedFinetune:
  id
  name
  primaryGenre
  tags
soundProfileSlug
projectBlueprint
deliveryAndControl
instrumentalOnly
userNarrative
musicLengthMs
generatedPrompt
generatedTitle
generatedDescription
compositionPlan
renderStatus
renderId
streamUrl
downloadUrl
requestIdsByStage
```

Scope draft generation state to the conversation and user. In a group chat or Teams channel, do not allow one person's card submission to overwrite another person's draft. Include a generation/session identifier in card action data and verify that the submitting user owns that draft.

The composition plan does not contain the finetune choice, and the render response does not echo it. The agent must retain the selected finetune and explicitly send the same `finetune_id` to both `/prompt` and `/render`.

## Recommended User Flow

### 1. Start or reset a song draft

Recognize clear intents such as "create a song," "make music," or "start over." Create a new draft identifier and clear any previous in-progress values after confirmation when appropriate.

### 2. Load and select a finetune

Call:

```http
GET /finetunes?model_id=music_v2
```

Present completed finetunes as a searchable or paginated selection experience. A long static list of buttons will not scale. In an Adaptive Card, use the card capabilities supported by both target hosts; when searchable choices are not consistently available, show a compact genre list first and then a smaller finetune list.

Display:

- `name` as the primary label.
- `primary_genre` as grouping or secondary context.
- A small subset of `tags` as additional context.

Submit and retain the finetune's `id`, not its display name.

There must be no "None" choice in the guided flow. `POST /prompt` requires a non-empty `finetune_id`. If finetunes cannot be loaded, show a retry action and do not silently invent a genre.

### 3. Collect the song details

Collect, infer, or confirm these values:

- Project blueprint: the song's use case and structure.
- Delivery and control: the desired workflow/output behavior.
- Instrumental-only choice.
- User narrative: story, occasion, people, lyrical details, mood, and emotional intent.
- Desired duration in seconds, converted to milliseconds for `/plan`.

The user narrative must not be used as a second genre selector. Do not inject text such as `SOUND DIRECTION`, a finetune name, "style model," or implementation details. The selected finetune is authoritative for genre, tempo, groove, harmony, and instrumentation. The narrative supplies story and emotional or lyrical intent.

If natural-language inference is uncertain, ask a concise follow-up or show a confirmation card before spending generation credits. At minimum, explicitly confirm the selected style, duration, instrumental/vocal choice, and short description before composing.

### 4. Generate the music prompt

Call `POST /prompt`. Store its `prompt`, `title`, and `description`.

The agent may show a short summary and offer Edit, Continue, or Cancel. Do not expose the full internal payload unless useful to the user.

### 5. Generate the composition plan

For the full guided experience, pass the generated prompt to `POST /plan`. Store the returned `chunks` exactly, including additional fields not known to the agent's static model.

The user may be offered a high-level plan review, but do not require users to edit low-level chunk JSON in chat.

### 6. Render the audio

Send the plan chunks, generated title, selected finetune ID, and instrumental setting to `POST /render`.

Use `POST /render` as the default integration for an M365 agent. A bot activity handler is not a browser page, and the WebSocket lifecycle does not naturally map to a single chat turn. Send or update a "Composing your track" activity while the request runs. If the selected Agents SDK architecture already supports durable background work and proactive updates, perform rendering in that worker and update the conversation when complete.

Use `WS /render/ws` only if the project deliberately implements a durable WebSocket worker and maps backend progress to updated activities. Do not hold an inbound M365 activity open indefinitely solely to mirror every backend progress percentage.

### 7. Deliver the result

The render response contains server-relative `stream_url` and `download_url` values. Convert them to absolute HTTPS URLs using `MUSIC_API_BASE_URL`.

Example:

```text
https://elevenlabs-music-api...azurecontainerapps.io
  + /render/stream/beb37911-fc19-4cf0-9cc1-be8ffcc48566
```

Show the title, description, duration when available, and actions to listen and download. Use `stream_url` for inline playback where the host supports it and `download_url` for download behavior.

Microsoft 365 Copilot Chat and Teams can differ in how they render media and attachments. Implement a graceful fallback:

1. Try the channel-appropriate audio/media or card action supported by the existing Agents SDK project.
2. Always provide an HTTPS link to the backend stream or download endpoint.
3. If a host requires a real uploaded attachment rather than a URL, fetch the bytes server-side from `download_url` and use that host's supported file-upload flow. Check host file-size limits before uploading.

Never use `file_path` for playback or download. It is an informational storage URI and may point to a private Azure Blob container or local file URI.

## Backend Pipeline

```text
GET /finetunes
      |
      | selected id + slug
      v
POST /prompt  -- generated prompt --> POST /plan
      |                                  |
      | same finetune_id                 | chunks
      +----------------------------------+
                                         v
                                  POST /render
                                         |
                                         v
                         GET /render/stream/{id}
                       GET /render/download/{id}
```

There is also a quick path in which a prompt goes directly to `/render`, but the agent described by this brief should default to the plan-first path because the requested experience is to compose a song from selected style and details. The quick path can be added as an explicit user option later.

## Endpoint Reference

### `GET /finetunes`

Lists ElevenLabs music finetunes without exposing the ElevenLabs API key.

Recommended request:

```http
GET /finetunes?model_id=music_v2
Accept: application/json
```

Optional query parameters:

| Parameter | Type | Default | Notes |
| --- | --- | --- | --- |
| `model_id` | string | unset | Use `music_v2` for this agent. |
| `visibility` | string | unset | `private`, `workspace`, or `public`. |
| `created_by` | string | unset | `self`, `workspace`, or `elevenlabs`. |
| `include_incomplete` | boolean | `false` | Keep false; incomplete models cannot be used reliably. |
| `cursor` | string | unset | Cursor from a prior `next_cursor`. |
| `page_size` | integer | server default | Range 1-100. |
| `refresh` | boolean | `false` | Bypasses the backend's short-lived cache. Use sparingly. |

Response:

```json
{
  "finetunes": [
    {
      "id": "aslj0pdvdods2agammwb",
      "name": "Indie Dance",
      "tags": ["Electronic", "House", "Nu-Disco"],
      "primary_genre": "Indie",
      "model_id": "music_v2",
      "created_at": "2026-07-21T13:22:52.615000Z",
      "visibility": "public",
      "created_by": "elevenlabs",
      "status": "completed",
      "training_progress": 1.0,
      "failure_reason": null
    }
  ],
  "count": 1,
  "has_more": false,
  "next_cursor": null
}
```

Follow pagination while `has_more` is true, passing `next_cursor` as the next `cursor`. Cache the list briefly in the agent service if useful, but do not persist it indefinitely because finetunes can be removed or added.

Errors:

- `500`: backend or ElevenLabs credentials are misconfigured.
- `502`: the backend could not reach ElevenLabs.

Both prevent the guided flow from continuing. Offer Retry and retain the user's other draft details.

### `POST /prompt`

Transforms two preset choices, the selected finetune, and the user's narrative into a professional music prompt.

Request:

```json
{
  "project_blueprint": "standalone_song_mini",
  "sound_profile": "indie_dance",
  "finetune_id": "aslj0pdvdods2agammwb",
  "delivery_and_control": "balanced_studio",
  "instrumental_only": false,
  "user_narrative": "A joyful anniversary song for Sam and Alex about meeting on a rainy afternoon."
}
```

Fields:

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `project_blueprint` | enum string | yes | Exact values below. |
| `sound_profile` | non-empty string | yes | Slug made from the chosen finetune name. It is open-ended, not an enum. |
| `finetune_id` | non-empty string | yes | ID returned by `GET /finetunes`. |
| `delivery_and_control` | enum string | yes | Exact values below. |
| `instrumental_only` | boolean | no | Defaults to `false`. |
| `user_narrative` | string or null | no | Story, occasion, names, lyrical details, and emotional intent. |

Project blueprint values:

| Value | Agent-facing meaning |
| --- | --- |
| `ad_brand_fast_hook` | Short ad or branded track with an immediate hook. |
| `podcast_voiceover_loop` | Repeatable podcast/background bed that leaves room for speech. |
| `video_game_action_loop` | Loopable action-oriented game music. |
| `meditation_sleep` | Calm meditation, relaxation, or sleep music. |
| `standalone_song_mini` | A compact standalone song with a song-like arc. |

Delivery and control values:

| Value | Agent-facing meaning |
| --- | --- |
| `exploratory_iterate` | Favor exploration and iteration. |
| `balanced_studio` | Balanced, polished default. Use when the user has no preference. |
| `blueprint_plan_first` | Favor deliberate structure and planning. |
| `live_one_take` | Favor a cohesive live-performance feel. |
| `isolation_stems` | Favor separation useful for stem-oriented work. |

Build `sound_profile` from the selected finetune name using a stable slug function: lowercase, replace non-alphanumeric runs with `_`, collapse repeated underscores, and trim underscores. If no name exists, use a non-empty slug derived from its ID. The backend resolves musical metadata from `finetune_id`; the slug is still required but is not the authoritative genre lookup key.

Response:

```json
{
  "prompt": "Create a compact, uplifting indie dance song...",
  "title": "Rainlit Anniversary",
  "description": "A joyful anniversary track with an energetic dance pulse and personal lyrical details.",
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "timestamp": "2026-07-29T10:30:00.000000",
  "input_parameters": {
    "project_blueprint": "standalone_song_mini",
    "sound_profile": "indie_dance",
    "finetune_id": "aslj0pdvdods2agammwb",
    "delivery_and_control": "balanced_studio",
    "instrumental_only": false,
    "user_narrative": "A joyful anniversary song for Sam and Alex about meeting on a rainy afternoon."
  }
}
```

Important behavior:

- The backend looks up `finetune_id` and passes only its name, primary genre, and tags to its prompt-generation agent.
- If that lookup fails, prompt generation currently continues and infers style from `sound_profile`. This degraded path still returns `200`; the caller is not told it occurred.
- Use a recently returned finetune ID and do not allow arbitrary IDs from model-generated text.
- The generated title and description may be null according to the public response model, so handle null safely.
- Do not mention the finetune name, slug, or the terms "finetune" and "style model" in user-facing generated music copy.

Expected latency is approximately 10-60 seconds. Set an HTTP timeout that permits this operation.

### `POST /plan`

Converts the generated music prompt into a `music_v2` composition plan.

Request:

```json
{
  "prompt": "Create a compact, uplifting indie dance song...",
  "music_length_ms": 30000
}
```

Fields:

| Field | Type | Required | Constraints |
| --- | --- | --- | --- |
| `prompt` | string | yes | Pass `PromptGenerationResponse.prompt`. |
| `music_length_ms` | integer or null | no | 1,000-300,000 ms. If omitted, the service extracts a duration from the prompt or defaults to 30 seconds. |

Response is returned directly, not inside a `plan` wrapper:

```json
{
  "chunks": [
    {
      "text": "[Intro]",
      "positive_styles": ["120 BPM", "bright synthesizer hook"],
      "negative_styles": [],
      "duration_ms": 6000,
      "context_adherence": "high"
    }
  ]
}
```

Each chunk contains:

- `text`: section marker and/or lyrics.
- `positive_styles`: styles to include.
- `negative_styles`: styles to avoid.
- `duration_ms`: chunk duration.
- `context_adherence`: nullable adherence value.
- Possible additional `music_v2` fields.

Preserve unknown chunk fields when storing and forwarding the plan. Do not deserialize into a type that discards future fields before sending them to `/render`.

Expected latency is approximately 5-30 seconds.

### `POST /render`

Renders and persists audio. It accepts exactly one source: a text `prompt` or composition-plan `chunks`.

Recommended plan-mode request for this agent:

```json
{
  "title": "Rainlit Anniversary",
  "chunks": [
    {
      "text": "[Intro]",
      "positive_styles": ["120 BPM", "bright synthesizer hook"],
      "negative_styles": [],
      "duration_ms": 6000,
      "context_adherence": "high"
    }
  ],
  "model_id": "music_v2",
  "finetune_id": "aslj0pdvdods2agammwb",
  "force_instrumental": false,
  "with_timestamps": false,
  "sign_with_c2pa": false
}
```

Request fields:

| Field | Type | Default | Rules |
| --- | --- | --- | --- |
| `prompt` | string or null | null | Prompt mode only; mutually exclusive with non-empty `chunks`. |
| `chunks` | array | `[]` | Plan mode only; mutually exclusive with a non-empty `prompt`. |
| `music_length_ms` | integer or null | null | Prompt mode only; 3,000-600,000 ms. |
| `model_id` | string | `music_v2` | Keep `music_v2`. |
| `finetune_id` | string or null | null | Send the same selected ID used for `/prompt`. |
| `finetune_strength` | number or null | API default | 0.0-1.0 and only valid with `finetune_id`. Omit unless the product explicitly exposes this advanced control. |
| `force_instrumental` | boolean | `false` | Keep consistent with the choice sent to `/prompt`. |
| `store_for_inpainting` | boolean | `false` | Enable only for a defined inpainting workflow. |
| `with_timestamps` | boolean | `false` | Requests word-level timestamps. |
| `sign_with_c2pa` | boolean | `false` | Requests C2PA provenance metadata. |
| `output_format` | string or null | API default | For example `mp3_44100_128` or `pcm_44100`. Prefer the default MP3-compatible result for chat delivery. |
| `title` | string or null | null | Local-only filename input; use the generated or user-approved title. |

Validation failures include:

- Neither `prompt` nor `chunks` is present.
- Both `prompt` and non-empty `chunks` are present.
- `music_length_ms` is supplied in plan mode.
- `finetune_strength` is supplied without `finetune_id`.
- `finetune_strength` is outside 0.0-1.0.
- Prompt-mode duration is outside 3,000-600,000 ms.

Response:

```json
{
  "id": "beb37911-fc19-4cf0-9cc1-be8ffcc48566",
  "filename": "rainlit_anniversary_abc123.mp3",
  "file_path": "https://storage.example/private/path.mp3",
  "download_url": "/render/download/beb37911-fc19-4cf0-9cc1-be8ffcc48566",
  "stream_url": "/render/stream/beb37911-fc19-4cf0-9cc1-be8ffcc48566",
  "content_type": "audio/mpeg",
  "file_size_bytes": 524288,
  "duration_ms": 30000,
  "composition_plan": {
    "chunks": []
  },
  "song_metadata": {},
  "request_id": "uuid",
  "timestamp": "2026-07-29T10:32:00.000000"
}
```

Store `id` as the canonical render identifier. Always use the returned `stream_url` and `download_url`; do not construct paths from `filename`. Both returned URLs are relative to the REST base URL.

Rendering can take approximately 15-120 seconds or longer depending on duration. It is a side-effecting, potentially billable operation. The backend currently exposes no idempotency key. Do not automatically retry a timed-out or disconnected render request because the first attempt may still have completed. Ask the user before starting another render unless the application can prove the first call never reached the backend.

### `GET /render/stream/{identifier}`

Streams a rendered file for playback. Use the render `id` as the identifier and the returned `stream_url` rather than building this path manually.

Response characteristics:

- Audio MIME type from the stored render, normally `audio/mpeg`.
- `Content-Disposition: inline`.
- `Content-Length` is set.
- `Accept-Ranges: bytes` is set.
- `404` if the render row or stored audio object is missing.

The endpoint also accepts a legacy filename, but IDs are the stable interface.

### `GET /render/download/{identifier}`

Downloads a rendered file. Use the render `id` and returned `download_url`.

Response characteristics:

- Audio MIME type from the stored render, normally `audio/mpeg`.
- `Content-Disposition: attachment; filename=...`.
- `Content-Length` is set.
- `Accept-Ranges: bytes` is set.
- `404` if the render row or stored audio object is missing.

### `WS /render/ws`

Optional real-time render protocol.

1. Connect to `{MUSIC_API_WS_URL}/render/ws`.
2. Wait for the server's `connected` progress message.
3. Send one render message.
4. Receive progress messages.
5. Receive one terminal `result` or `error`; the server then closes the socket.

Client message:

```json
{
  "type": "render",
  "composition_plan": {
    "title": "Rainlit Anniversary",
    "chunks": [],
    "finetune_id": "aslj0pdvdods2agammwb",
    "force_instrumental": false
  }
}
```

Despite its name, `composition_plan` contains the entire `RenderRequest`, including all fields accepted by `POST /render` and even prompt mode.

Progress message:

```json
{
  "type": "progress",
  "stage": "generating",
  "progress_percent": 35,
  "message": "Generating music...",
  "timestamp": "2026-07-29T10:31:00.000000"
}
```

Terminal success:

```json
{
  "type": "result",
  "data": {
    "id": "beb37911-fc19-4cf0-9cc1-be8ffcc48566",
    "download_url": "/render/download/beb37911-fc19-4cf0-9cc1-be8ffcc48566",
    "stream_url": "/render/stream/beb37911-fc19-4cf0-9cc1-be8ffcc48566"
  }
}
```

Terminal error:

```json
{
  "type": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Provide either 'prompt' or 'chunks'.",
  "timestamp": "2026-07-29T10:31:00.000000"
}
```

Error codes are `INVALID_REQUEST`, `VALIDATION_ERROR`, and `SERVER_ERROR`.

Typical progress stages are `connected`, `validating`, `validated`, `generating`, `processing`, `saving`, `extracting`, and `complete`. Do not make business logic depend on receiving every intermediate stage.

## Health and Discovery Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Dependency-aware health response; returns `200` when healthy and `503` when degraded. |
| `GET /ready` | Lightweight readiness response. |
| `GET /alive` | Lightweight liveness response. |
| `GET /openapi.json` | Current machine-readable API schema. |
| `GET /docs` | Swagger UI. |

Use `/health` for deployment checks, not before every song operation.

## Error Handling and Correlation

Every HTTP response includes an `X-Request-ID` header. The agent may send its own UUID in `X-Request-ID`; the backend echoes it. Generate a different request ID for each pipeline stage and store it with the draft so support can trace failures.

The backend currently has multiple error shapes. Normalize all of them in `MusicApiClient`.

Global validation or unhandled error:

```json
{
  "error": "Validation Error",
  "message": "Invalid request parameters",
  "request_id": "uuid",
  "timestamp": "2026-07-29T10:30:00.000000"
}
```

Route-raised error with string detail:

```json
{
  "detail": "Music rendering failed: ..."
}
```

Route-raised error with object detail:

```json
{
  "detail": {
    "error": "Generation Error",
    "message": "Failed to generate prompt: ...",
    "request_id": "uuid"
  }
}
```

Recommended normalized client error:

```text
status
code
userMessage
technicalMessage
requestId
isRetryable
```

Status guidance:

| Status | Meaning | Agent behavior |
| --- | --- | --- |
| `200` | Success | Advance the draft state. |
| `404` | Render/audio missing | Explain that the file is unavailable; retain metadata. |
| `422` | Invalid request | Keep the draft, identify the invalid/missing choice, and ask for correction. Do not blind-retry. |
| `500` | Generation, upstream, or server failure | Show a concise failure with request ID. Retry prompt/plan only after user confirmation; be especially cautious with render. |
| `502` | Finetune upstream failure | Keep the draft and offer Retry. |
| `503` | Backend degraded | Ask the user to try later and retain the draft. |

Never send raw stack traces, credentials, internal storage URLs, or full upstream exception text to the conversation. Log technical detail in the agent service and show the correlation ID to the user.

## Long-Running Operations

Prompt, plan, and render calls can exceed the comfortable duration of a chat turn. Follow the long-running-operation pattern already established in the Agents SDK project:

1. Acknowledge the action promptly.
2. Persist the draft and pending stage before the external call.
3. Run the operation with explicit connect/read/overall timeouts appropriate to the stage.
4. Update an existing status activity when the channel permits; otherwise send a small number of meaningful stage messages.
5. Persist the successful response before posting the final activity.
6. Ensure duplicate card submissions do not start duplicate work.

Suggested user-facing stages are "Preparing your music brief," "Building the composition," and "Rendering your audio." Do not mirror every internal percentage as a new chat message.

There is currently no backend cancellation endpoint. A Cancel action can stop future agent stages and suppress or ignore delivery, but it cannot guarantee that an already-started `/render` operation stops or avoids cost. State this accurately in the UI if cancellation is offered during render.

## Security and Deployment Considerations

### Backend credentials

The FastAPI service keeps `OPENAI_API_KEY`, `ELEVENLABS_API_KEY`, database credentials, and Azure Storage credentials server-side. The M365 agent needs none of these.

### Authentication boundary

The backend routes shown here do not currently enforce caller authentication or per-user authorization. Do not imply that Microsoft 365 identity is being enforced by this API. Before a broad production rollout, place the backend behind an agreed service-to-service authentication boundary, such as an authenticated API gateway or equivalent platform control, and update the typed client accordingly.

Until that exists:

- Do not put secrets in query strings or card action data.
- Do not expose arbitrary backend-call functionality to model-generated tool arguments.
- Validate all tool arguments against the documented enums and constraints.
- Use finetune IDs only from `GET /finetunes`.
- Treat audio URLs as shareable links and avoid posting them into conversations broader than the user intended.

### CORS

CORS is a browser security control and does not normally affect server-to-server calls from an Agents SDK service. Do not request a CORS change merely because the agent service calls the backend. CORS matters only if a browser-hosted component calls the music API directly; the recommended architecture routes calls through the agent service.

### User content

The narrative may contain personal names, memories, and other user-provided content. Retain only what the product needs, avoid writing full narratives to routine logs, and follow the host application's privacy and retention requirements. Treat Adaptive Card submissions and model-extracted values as untrusted input.

### Outbound URLs

Only create playback/download links by resolving backend-returned relative paths against the configured backend origin. Reject absolute URLs returned unexpectedly and never let user text choose the host. This prevents turning the agent into an arbitrary URL fetcher when it fetches audio for attachment upload.

## Agent Behavior Rules

The coding agent should implement these product rules explicitly:

1. A finetune selection is mandatory before calling `/prompt`.
2. The same selected `finetune_id` must be sent to `/prompt` and `/render`.
3. `sound_profile` is an open-ended slug, not one of the retired fixed sound presets.
4. Genre comes from the selected finetune, not from narrative text.
5. `instrumental_only` and `force_instrumental` must stay consistent.
6. The default delivery choice is `balanced_studio` when the user expresses no preference.
7. The plan response is `{ "chunks": [...] }` directly, not `{ "plan": ... }`.
8. Unknown fields in chunks must survive the round trip to `/render`.
9. Render requests provide exactly one of `prompt` or `chunks`.
10. The returned render `id` is the canonical track handle.
11. Use returned stream/download paths and make them absolute; never use `file_path` for users.
12. Do not automatically retry an ambiguous render failure.
13. Do not claim an in-progress render can be cancelled at the backend.
14. Do not promise render history, delete, edit/inpaint, or list APIs; they do not currently exist.
15. Do not leak the words "finetune" or "style model" into generated track copy shown to end users. In the product UI, prefer "music style" or "sound."

## Suggested Card and Message Surfaces

Use Adaptive Cards only where structured choice or confirmation improves reliability. Keep ordinary conversational responses as normal activities.

Suggested surfaces:

- Start card: Create a song, Resume draft, Start over.
- Style card: genre filter plus finetune choices; submit the draft ID and finetune ID.
- Details card: blueprint, delivery mode, duration, instrumental toggle, and narrative input.
- Confirmation card: chosen style name, use case, duration, vocal/instrumental choice, and narrative summary.
- Progress activity: one updateable activity showing the current pipeline stage.
- Result card: title, description, duration, Listen, Download, and Create another.

Use stable action verbs in submitted card data, for example:

```json
{
  "action": "music.selectFinetune",
  "draftId": "uuid",
  "finetuneId": "aslj0pdvdods2agammwb"
}
```

Validate `action`, `draftId`, the submitting user, and all values server-side. Do not trust hidden card data solely because the card originated from the agent.

Design cards against the Adaptive Card schema and features supported by both Microsoft 365 Copilot Chat and Teams in the project's target environment. Provide a text fallback for unsupported card capabilities and accessibility.

## Implementation Checklist

- [ ] Add environment-based REST and optional WebSocket base URLs.
- [ ] Implement a typed `MusicApiClient` with centralized JSON, timeout, request-ID, and error handling.
- [ ] Persist per-user, per-conversation song draft state.
- [ ] Prevent duplicate action submissions from starting duplicate pipeline operations.
- [ ] Load all relevant `music_v2` finetune pages and retain the selected object.
- [ ] Require a style selection; do not provide a None option in the guided flow.
- [ ] Create a stable `sound_profile` slug from the selected finetune name.
- [ ] Collect and validate the exact blueprint and delivery enum values.
- [ ] Keep user narrative free of injected genre/tooling directives.
- [ ] Call `/prompt`, store prompt/title/description, and retain its request ID.
- [ ] Call `/plan` with duration in milliseconds and preserve unknown chunk fields.
- [ ] Call `/render` in plan mode with the same finetune ID and consistent instrumental setting.
- [ ] Persist the render response before sending the final activity.
- [ ] Resolve returned stream/download paths against the configured backend origin.
- [ ] Provide channel-compatible audio/link delivery with a plain HTTPS fallback.
- [ ] Normalize all backend error shapes and show correlation IDs on failures.
- [ ] Avoid automatic retries of ambiguous render failures.
- [ ] Test in both Microsoft 365 Copilot Chat and Teams, including card fallbacks.

## Acceptance Scenarios

### Happy path

1. User asks to create an anniversary song.
2. Agent presents current `music_v2` styles.
3. User selects a style and supplies details.
4. Agent confirms style, 30-second duration, and vocal choice.
5. Agent successfully calls `/prompt`, `/plan`, and `/render` in order.
6. The same finetune ID is visible in the first and third outbound request logs.
7. Result activity contains a working HTTPS playback link and download link based on the returned render ID.

### Instrumental path

`instrumental_only: true` is sent to `/prompt`, `force_instrumental: true` is sent to `/render`, and the confirmation tells the user the track is instrumental.

### Finetune outage

`GET /finetunes` returns `502`. The user's draft is retained, no genre is invented, and the agent offers Retry.

### Invalid card submission

A user submits an unknown finetune ID or modifies an enum value. The agent rejects it before calling the backend and reloads the relevant choices.

### Prompt validation failure

The backend returns `422`. The agent retains the draft, presents a concise correction prompt, and records `X-Request-ID`.

### Ambiguous render timeout

The HTTP client loses the response after `/render` may have started. The agent does not automatically send the same render again. It explains that completion is uncertain, logs the correlation ID, and asks before creating another render.

### Missing stored audio

The stream URL returns `404`. The agent does not expose `file_path`; it explains that the audio is unavailable and retains the render metadata/request ID for support.

### Cross-user isolation

Two users invoke the agent in one Teams channel. Their selected styles, narratives, cards, and results remain in separate user-scoped drafts.

## Current Backend Limitations

Account for these rather than inventing unsupported calls:

- No render history/list endpoint.
- No render status lookup endpoint.
- No render cancellation endpoint.
- No render delete endpoint.
- No backend idempotency key for render creation.
- No caller authentication or per-user authorization on the documented routes.
- Finetune selection is not echoed in the render response.
- A failed finetune lookup during `/prompt` can degrade silently to slug inference.
- The WebSocket is one request per connection and closes after the terminal result/error.

These limitations are important for the agent's retry, cancellation, privacy, and conversation-state design.

## Related Backend Documentation

- `docs/FRONTEND_HANDOFF_SOUND_PROFILE.md`: authoritative finetune-to-prompt behavior.
- `docs/FRONTEND_FINETUNES.md`: finetune listing and render steering details.
- `docs/FRONTEND_API_CHANGES_STORAGE.md`: stable render IDs and storage-backed audio URLs.
- `docs/PLAN_API.md`: composition plan endpoint.
- `docs/RENDER_API.md`: render endpoint.
- `docs/frontend-websocket-integration.md`: WebSocket render protocol.

## Microsoft 365 Agents SDK References

- Documentation: <https://learn.microsoft.com/en-us/microsoft-365/agents-sdk/>
- SDK repository and samples: <https://github.com/microsoft/Agents>

Use the language-specific SDK patterns and the existing project structure for activities, state, authentication, Adaptive Cards, deployment, and proactive updates. This document defines the music backend contract and the required product behavior; it does not replace the Agents SDK's current host-specific guidance.