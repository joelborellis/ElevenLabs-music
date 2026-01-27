# Frontend WebSocket Integration Guide

This document explains how to integrate the new WebSocket-based render endpoint (`/render/ws`) into the ElevenLabs Music UI frontend to provide real-time progress updates during music generation.

## Overview

The backend now supports a WebSocket endpoint that provides real-time progress updates during music rendering, replacing the need to show a generic spinner while waiting for the REST API response.

### Benefits
- Real-time progress feedback (0-100%)
- Stage-by-stage status messages
- Better user experience during long render operations
- Same final result data as the REST endpoint

## WebSocket Endpoint

**URL:** `ws://localhost:8000/render/ws` (development)

## Protocol

### Connection Flow

```
1. Frontend connects to WebSocket
2. Backend sends "connected" message (progress: 0%)
3. Frontend sends composition plan
4. Backend sends progress updates (5% → 10% → 15% → 70% → 85% → 95% → 100%)
5. Backend sends final result
6. Connection closes
```

### Message Types

#### 1. Progress Message (Server → Client)

Sent during rendering to update progress.

```typescript
interface ProgressMessage {
  type: "progress";
  stage: string;      // Current stage name
  progress_percent: number;  // 0-100
  message: string;    // Human-readable status
  timestamp: string;  // ISO 8601
}
```

**Progress Stages:**

| Stage | Percent | Message |
|-------|---------|---------|
| `connected` | 0 | "Connected. Send composition plan to begin rendering." |
| `validating` | 5 | "Validating composition plan..." |
| `validated` | 10 | "Composition plan validated successfully" |
| `generating` | 15 | "Starting music generation with ElevenLabs API..." |
| `processing` | 70 | "API call complete, processing response..." |
| `saving` | 85 | "Saving audio file to disk..." |
| `extracting` | 95 | "Extracting metadata..." |
| `complete` | 100 | "Render complete!" |

#### 2. Result Message (Server → Client)

Sent when rendering completes successfully.

```typescript
interface ResultMessage {
  type: "result";
  data: {
    filename: string;
    file_path: string;
    download_url: string;   // e.g., "/render/download/track_abc123.mp3"
    stream_url: string;     // e.g., "/render/stream/track_abc123.mp3"
    content_type: string;   // "audio/mpeg"
    file_size_bytes: number;
    composition_plan: object | null;
    song_metadata: object | null;
    request_id: string;
    timestamp: string;
  };
}
```

#### 3. Error Message (Server → Client)

Sent when an error occurs.

```typescript
interface ErrorMessage {
  type: "error";
  error_code: "INVALID_REQUEST" | "VALIDATION_ERROR" | "SERVER_ERROR";
  message: string;
  timestamp: string;
}
```

#### 4. Render Request (Client → Server)

Sent by the frontend to start rendering.

```typescript
interface RenderWebSocketRequest {
  type: "render";
  composition_plan: {
    title?: string;
    positive_global_styles: string[];
    negative_global_styles: string[];
    sections: Section[];
  };
}
```

## Implementation Guide

### 1. Update Types (`src/types/index.ts`)

Add WebSocket message types:

```typescript
// WebSocket message types
export interface WSProgressMessage {
  type: "progress";
  stage: string;
  progress_percent: number;
  message: string;
  timestamp: string;
}

export interface WSResultMessage {
  type: "result";
  data: AudioResult & {
    file_path: string;
    content_type: string;
    composition_plan: object | null;
    song_metadata: object | null;
    request_id: string;
    timestamp: string;
  };
}

export interface WSErrorMessage {
  type: "error";
  error_code: string;
  message: string;
  timestamp: string;
}

export type WSMessage = WSProgressMessage | WSResultMessage | WSErrorMessage;
```

### 2. Create WebSocket Service (`src/services/websocket.ts`)

```typescript
const WS_URL = "ws://localhost:8000/render/ws";

export interface RenderProgress {
  stage: string;
  percent: number;
  message: string;
}

export async function renderWithWebSocket(
  compositionPlan: CompositionPlanData,
  onProgress: (progress: RenderProgress) => void
): Promise<AudioResult> {
  return new Promise((resolve, reject) => {
    const ws = new WebSocket(WS_URL);

    ws.onopen = () => {
      console.log("WebSocket connected");
    };

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case "progress":
          onProgress({
            stage: message.stage,
            percent: message.progress_percent,
            message: message.message,
          });

          // Send composition plan after receiving "connected" message
          if (message.stage === "connected") {
            ws.send(JSON.stringify({
              type: "render",
              composition_plan: compositionPlan,
            }));
          }
          break;

        case "result":
          const data = message.data;
          resolve({
            url: `http://localhost:8000${data.stream_url}`,
            filename: data.filename,
            mimeType: data.content_type,
            downloadUrl: `http://localhost:8000${data.download_url}`,
            fileSizeBytes: data.file_size_bytes,
          });
          ws.close();
          break;

        case "error":
          reject(new Error(`${message.error_code}: ${message.message}`));
          ws.close();
          break;
      }
    };

    ws.onerror = (error) => {
      reject(new Error("WebSocket connection failed"));
    };

    ws.onclose = (event) => {
      if (!event.wasClean) {
        reject(new Error("WebSocket connection closed unexpectedly"));
      }
    };
  });
}
```

### 3. Update Wizard Store (`src/state/wizardStore.ts`)

Add progress state:

```typescript
interface WizardState {
  // ... existing state ...

  // New progress state
  renderProgress: {
    stage: string;
    percent: number;
    message: string;
  } | null;
}

interface WizardActions {
  // ... existing actions ...

  setRenderProgress: (progress: { stage: string; percent: number; message: string } | null) => void;
}

// In the store implementation:
setRenderProgress: (progress) => set({ renderProgress: progress }),
```

### 4. Update Step2Editors Component

Replace the REST API call with WebSocket:

```typescript
import { renderWithWebSocket } from "../services/websocket";

// In the render handler:
const handleRenderMusic = async () => {
  setIsCreatingMusic(true);
  setRenderProgress(null);

  try {
    const result = await renderWithWebSocket(
      compositionPlanObject,
      (progress) => {
        setRenderProgress(progress);
      }
    );

    setAudioResult(result);
    nextStep();
  } catch (error) {
    console.error("Render failed:", error);
    // Handle error
  } finally {
    setIsCreatingMusic(false);
    setRenderProgress(null);
  }
};
```

### 5. Update Progress UI

Replace the generic spinner with a progress indicator:

```tsx
{isCreatingMusic && renderProgress && (
  <div className="flex flex-col items-center gap-4">
    {/* Progress bar */}
    <div className="w-full bg-gray-200 rounded-full h-2.5">
      <div
        className="bg-accent h-2.5 rounded-full transition-all duration-300"
        style={{ width: `${renderProgress.percent}%` }}
      />
    </div>

    {/* Progress text */}
    <div className="text-center">
      <p className="font-medium">{renderProgress.message}</p>
      <p className="text-sm text-muted-foreground">
        {renderProgress.percent}% complete
      </p>
    </div>
  </div>
)}
```

## Example: Complete Flow

```typescript
// User clicks "Render Music"

// 1. Connect to WebSocket
const ws = new WebSocket("ws://localhost:8000/render/ws");

// 2. Receive: {"type": "progress", "stage": "connected", "progress_percent": 0, ...}
//    → Show: "Ready to render"

// 3. Send composition plan
ws.send(JSON.stringify({
  type: "render",
  composition_plan: { title: "My Song", sections: [...] }
}));

// 4. Receive progress updates
//    → {"type": "progress", "stage": "validating", "progress_percent": 5, ...}
//    → {"type": "progress", "stage": "validated", "progress_percent": 10, ...}
//    → {"type": "progress", "stage": "generating", "progress_percent": 15, ...}
//    → {"type": "progress", "stage": "processing", "progress_percent": 70, ...}
//    → {"type": "progress", "stage": "saving", "progress_percent": 85, ...}
//    → {"type": "progress", "stage": "extracting", "progress_percent": 95, ...}
//    → {"type": "progress", "stage": "complete", "progress_percent": 100, ...}

// 5. Receive result
//    → {"type": "result", "data": { filename: "...", stream_url: "...", ... }}

// 6. Navigate to Step 3 with audio player
```

## Fallback Strategy

Keep the existing REST API call as a fallback:

```typescript
async function renderMusic(compositionPlan: CompositionPlanData, onProgress?: (p: RenderProgress) => void) {
  // Try WebSocket first
  if (onProgress && "WebSocket" in window) {
    try {
      return await renderWithWebSocket(compositionPlan, onProgress);
    } catch (wsError) {
      console.warn("WebSocket render failed, falling back to REST:", wsError);
    }
  }

  // Fallback to REST API
  return await createMusicFromPlan(compositionPlan);
}
```

## Testing

1. Start the backend: `uvicorn main:app --reload`
2. Open browser DevTools → Network → WS tab
3. Trigger a render and observe WebSocket messages
4. Verify progress updates appear in the UI

## Error Handling

Handle these error scenarios:

| Error Code | Cause | User Action |
|------------|-------|-------------|
| `INVALID_REQUEST` | Malformed JSON or missing fields | Fix request format |
| `VALIDATION_ERROR` | Invalid composition plan | Check sections, durations |
| `SERVER_ERROR` | ElevenLabs API or server issue | Retry or contact support |

```typescript
ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  if (msg.type === "error") {
    switch (msg.error_code) {
      case "VALIDATION_ERROR":
        toast.error(`Validation failed: ${msg.message}`);
        break;
      case "SERVER_ERROR":
        toast.error("Server error. Please try again.");
        break;
      default:
        toast.error(msg.message);
    }
  }
};
```
