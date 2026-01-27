# Frontend WebSocket Integration Guide

This document describes how to integrate with the `/render/ws` WebSocket endpoint for real-time music rendering with progress updates.

## Endpoint

```
ws://localhost:8000/render/ws
```

## Protocol Overview

```
Client                                Server
  |                                      |
  |-------- Connect ------------------->|
  |                                      |
  |<------- progress (connected, 0%) ---|
  |                                      |
  |-------- render request ------------>|
  |                                      |
  |<------- progress (validating, 5%) --|
  |<------- progress (validated, 10%) --|
  |<------- progress (generating, 15%) -|
  |<------- progress (processing, 70%) -|
  |<------- progress (saving, 85%) -----|
  |<------- progress (extracting, 95%) -|
  |<------- progress (complete, 100%) --|
  |<------- result --------------------|
  |                                      |
  |-------- Connection closes ----------|
```

## Message Types

All messages are JSON objects with a `type` field that determines the message structure.

### 1. Progress Message (Server → Client)

Sent during rendering to indicate current progress.

```typescript
interface ProgressMessage {
  type: "progress";
  stage: string;           // Current processing stage
  progress_percent: number; // 0-100
  message: string;         // Human-readable status
  timestamp: string;       // ISO 8601 timestamp
}
```

**Progress Stages:**

| Stage | Percent | Description |
|-------|---------|-------------|
| `connected` | 0% | WebSocket connection established |
| `validating` | 5% | Validating composition plan |
| `validated` | 10% | Validation complete |
| `generating` | 15% | ElevenLabs API call in progress |
| `processing` | 70% | API complete, processing response |
| `saving` | 85% | Writing audio file to disk |
| `extracting` | 95% | Extracting metadata |
| `complete` | 100% | Render finished |

**Example:**
```json
{
  "type": "progress",
  "stage": "generating",
  "progress_percent": 15,
  "message": "Generating music with ElevenLabs API...",
  "timestamp": "2026-01-27T22:04:31.660000"
}
```

### 2. Result Message (Server → Client)

Sent after successful rendering with the final result.

```typescript
interface ResultMessage {
  type: "result";
  data: {
    filename: string;           // e.g., "my_track_abc123.mp3"
    file_path: string;          // Server file path
    download_url: string;       // e.g., "/render/download/my_track_abc123.mp3"
    stream_url: string;         // e.g., "/render/stream/my_track_abc123.mp3"
    content_type: string;       // "audio/mpeg"
    file_size_bytes: number;    // File size in bytes
    composition_plan?: object;  // Returned composition plan (if available)
    song_metadata?: object;     // Song metadata (if available)
    request_id: string;         // Unique request ID
    timestamp: string;          // ISO 8601 timestamp
  };
}
```

**Example:**
```json
{
  "type": "result",
  "data": {
    "filename": "websocket_test_track_8fbdcf93.mp3",
    "file_path": "/output/music/websocket_test_track_8fbdcf93.mp3",
    "download_url": "/render/download/websocket_test_track_8fbdcf93.mp3",
    "stream_url": "/render/stream/websocket_test_track_8fbdcf93.mp3",
    "content_type": "audio/mpeg",
    "file_size_bytes": 1440580,
    "composition_plan": null,
    "song_metadata": null,
    "request_id": "8eab5bcb-1ad3-45b3-8cf8-727a26ca30e7",
    "timestamp": "2026-01-27T22:04:51"
  }
}
```

### 3. Error Message (Server → Client)

Sent when an error occurs during rendering.

```typescript
interface ErrorMessage {
  type: "error";
  error_code: string;  // Machine-readable code
  message: string;     // Human-readable description
  timestamp: string;   // ISO 8601 timestamp
}
```

**Error Codes:**

| Code | Description |
|------|-------------|
| `INVALID_REQUEST` | Malformed request message |
| `VALIDATION_ERROR` | Composition plan validation failed |
| `SERVER_ERROR` | Unexpected error during rendering |

**Example:**
```json
{
  "type": "error",
  "error_code": "VALIDATION_ERROR",
  "message": "Composition plan must have at least one section. Total duration must be between 3000ms and 600000ms.",
  "timestamp": "2026-01-27T22:05:00.000000"
}
```

### 4. Render Request (Client → Server)

Sent by the client to start rendering.

```typescript
interface RenderRequest {
  type: "render";
  composition_plan: {
    title?: string;                    // Optional title for output filename
    positive_global_styles: string[];  // Styles to include globally
    negative_global_styles: string[];  // Styles to avoid globally
    sections: Section[];               // Array of sections
  };
}

interface Section {
  section_name: string;
  positive_local_styles: string[];
  negative_local_styles: string[];
  duration_ms: number;          // Minimum 3000ms per section
  lines?: string[];             // Optional lyrics
  source_from?: string | null;  // Optional source reference
}
```

**Validation Rules:**
- Must have at least one section
- Total duration: 3,000ms - 600,000ms (3 seconds to 10 minutes)
- Each section must be at least 3,000ms

**Example:**
```json
{
  "type": "render",
  "composition_plan": {
    "title": "My Epic Track",
    "positive_global_styles": ["electronic pop", "uplifting", "122 bpm"],
    "negative_global_styles": ["vocals", "slow", "dark"],
    "sections": [
      {
        "section_name": "Intro",
        "positive_local_styles": ["energetic", "synth lead"],
        "negative_local_styles": ["sparse"],
        "duration_ms": 5000,
        "lines": []
      },
      {
        "section_name": "Main",
        "positive_local_styles": ["full energy", "driving beat"],
        "negative_local_styles": ["ambient"],
        "duration_ms": 10000,
        "lines": []
      }
    ]
  }
}
```

## JavaScript Example

```javascript
function renderWithWebSocket(compositionPlan, onProgress, onResult, onError) {
  const ws = new WebSocket('ws://localhost:8000/render/ws');

  ws.onopen = () => {
    console.log('Connected to render WebSocket');
  };

  ws.onmessage = (event) => {
    const message = JSON.parse(event.data);

    switch (message.type) {
      case 'progress':
        // Handle progress update
        if (message.stage === 'connected') {
          // Server is ready, send the render request
          ws.send(JSON.stringify({
            type: 'render',
            composition_plan: compositionPlan
          }));
        } else {
          onProgress?.(message.stage, message.progress_percent, message.message);
        }
        break;

      case 'result':
        // Render complete
        onResult?.(message.data);
        ws.close();
        break;

      case 'error':
        // Handle error
        onError?.(message.error_code, message.message);
        ws.close();
        break;
    }
  };

  ws.onerror = (error) => {
    console.error('WebSocket error:', error);
    onError?.('CONNECTION_ERROR', 'WebSocket connection failed');
  };

  ws.onclose = () => {
    console.log('WebSocket connection closed');
  };

  return ws;
}

// Usage
const compositionPlan = {
  title: "My Track",
  positive_global_styles: ["electronic", "upbeat"],
  negative_global_styles: ["slow"],
  sections: [
    {
      section_name: "Main",
      positive_local_styles: ["energetic"],
      negative_local_styles: [],
      duration_ms: 10000,
      lines: []
    }
  ]
};

renderWithWebSocket(
  compositionPlan,
  (stage, percent, message) => {
    console.log(`Progress: ${stage} (${percent}%) - ${message}`);
    // Update progress bar UI
  },
  (result) => {
    console.log('Render complete:', result.filename);
    // Play audio using stream_url
    const audio = new Audio(`http://localhost:8000${result.stream_url}`);
    audio.play();
  },
  (code, message) => {
    console.error(`Error [${code}]: ${message}`);
    // Show error to user
  }
);
```

## React Hook Example

```typescript
import { useState, useCallback } from 'react';

interface RenderProgress {
  stage: string;
  percent: number;
  message: string;
}

interface RenderResult {
  filename: string;
  download_url: string;
  stream_url: string;
  file_size_bytes: number;
}

export function useWebSocketRender() {
  const [isRendering, setIsRendering] = useState(false);
  const [progress, setProgress] = useState<RenderProgress | null>(null);
  const [result, setResult] = useState<RenderResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const render = useCallback((compositionPlan: any) => {
    setIsRendering(true);
    setProgress(null);
    setResult(null);
    setError(null);

    const ws = new WebSocket('ws://localhost:8000/render/ws');

    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);

      switch (message.type) {
        case 'progress':
          if (message.stage === 'connected') {
            ws.send(JSON.stringify({
              type: 'render',
              composition_plan: compositionPlan
            }));
          }
          setProgress({
            stage: message.stage,
            percent: message.progress_percent,
            message: message.message
          });
          break;

        case 'result':
          setResult(message.data);
          setIsRendering(false);
          ws.close();
          break;

        case 'error':
          setError(`${message.error_code}: ${message.message}`);
          setIsRendering(false);
          ws.close();
          break;
      }
    };

    ws.onerror = () => {
      setError('WebSocket connection failed');
      setIsRendering(false);
    };
  }, []);

  return { render, isRendering, progress, result, error };
}
```

## Audio Playback

After receiving the result, use the URLs to play or download the audio:

```javascript
// Stream for playback (supports seeking)
const streamUrl = `http://localhost:8000${result.stream_url}`;

// Download the file
const downloadUrl = `http://localhost:8000${result.download_url}`;
```

The stream endpoint returns proper headers for browser audio playback:
- `Content-Type: audio/mpeg`
- `Content-Length: <file_size>`
- `Accept-Ranges: bytes`

## Timing Expectations

The ElevenLabs API call (the `generating` stage at 15%) is the longest operation and typically takes 10-30 seconds depending on composition length. The other stages complete quickly.
