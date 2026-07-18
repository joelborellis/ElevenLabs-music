# Testing

Ad-hoc test and debug scripts for the ElevenLabs music generation API. These are standalone scripts (not a `pytest` suite) — each is run directly and prints human-readable results.

## Prerequisites

- A running API server for the HTTP/WebSocket tests: `uv run python main.py` (defaults to `http://localhost:8000`).
- A populated `.env` with `OPENAI_API_KEY` and `ELEVENLABS_API_KEY` — required for the scripts that call OpenAI/ElevenLabs directly.
- Run scripts from the project root, e.g. `uv run python testing/test_prompt_endpoint.py`.

## End-to-end pipeline (prompt → plan → render)

The three endpoint tests mirror the app's three-stage pipeline and chain together automatically via generated JSON files, so you can run the whole thing hands-free without copy-pasting data between steps.

### How the chaining works

Each test **writes** its result to a `generated_*.json` file, and the next test **reads** that file as its input. Every reader prefers the generated file when it exists and otherwise falls back to its own static input JSON — so any test still runs on its own.

```
                         writes                         reads / writes                       reads
test_prompt_endpoint.py ────────► generated_prompt.json ────────► test_plan_endpoint.py ────────► generated_comp_plan.json ────────► test_render_endpoint.py ────────► rendered .mp3
   (POST /prompt)                {prompt,                          (POST /plan)                  {title, chunks}                     (POST /render)
                                  music_length_ms}
```

| Step | Reads | Calls | Writes |
| --- | --- | --- | --- |
| 1. `test_prompt_endpoint.py` | `prompt_test_cases.json` (`default`) | `POST /prompt` | `generated_prompt.json` = `{prompt, music_length_ms}` (duration parsed from the prompt text, else 30000) |
| 2. `test_plan_endpoint.py` | `generated_prompt.json` if present, else `plan_test_input.json` | `POST /plan` | `generated_comp_plan.json` = `{title, chunks}` |
| 3. `test_render_endpoint.py` | `generated_comp_plan.json` if present, else `render_test_input.json` → `plan_mode` | `POST /render` | the rendered `.mp3` (+ a downloaded copy in `testing/music/`) |

Each generated file is already in the *exact request shape* the next endpoint expects, which is what makes the handoff automatic (e.g. `/plan` returns `chunks` in the same `Chunk` shape that `/render` accepts).

### Running the full chain

Start the server (`uv run python main.py`), then run the three tests in order:

```bash
uv run python testing/test_prompt_endpoint.py   # writes generated_prompt.json
uv run python testing/test_plan_endpoint.py     # reads it, writes generated_comp_plan.json
uv run python testing/test_render_endpoint.py   # reads it, renders the audio
```

To change what flows through the chain, edit the *static* input at the stage you want to start from and delete the downstream `generated_*.json` files. Deleting **all** `generated_*.json` files resets every test to its static inputs (each then runs fully standalone).

> **Backend required?** = whether the script needs the local API server (`uv run python main.py`) running. Scripts marked **No** either call the OpenAI/ElevenLabs SDKs and services directly, or hit an external service, so they only need the relevant API keys / connectivity — not the local server.

Each entry below lists **Inputs** (what you must provide or what the script reads) and **Outputs** (what it prints or writes).

---

## HTTP endpoint tests (require the server running)

### [test_prompt_endpoint.py](test_prompt_endpoint.py)
Tests `POST /prompt` — generates a music prompt from preset selections.
- **Backend required?** Yes.
- **Inputs:** Request payloads are read from [prompt_test_cases.json](prompt_test_cases.json) — edit that file to change the variations without touching the script. It holds a `default` payload (used for the single request) and a `cases` list (used by `--all`). Optional CLI flag `--all` runs every combination in `cases` instead of the single default request.
- **Outputs:** Prints the generated `prompt`, `title`, `description`, request ID, and full JSON response to stdout. On the single (default) run, **writes `generated_prompt.json`** — the prompt in plan-ready `{prompt, music_length_ms}` form (duration parsed from the prompt text, else defaulted to 30000), which `test_plan_endpoint.py` then plans directly. (`--all` does not write the file.)

### [test_plan_endpoint.py](test_plan_endpoint.py)
Tests `POST /plan` — generates a composition plan from a prompt.
- **Backend required?** Yes.
- **Inputs:** The `prompt` and `music_length_ms` are read from [plan_test_input.json](plan_test_input.json) by default — edit that file to change them without touching the script. If `generated_prompt.json` exists (from running `test_prompt_endpoint.py` first), that prompt is used instead. No CLI arguments. (The validation checks use intentionally-invalid values that remain hardcoded.)
- **Outputs:** Prints the composition-plan JSON and asserts the response contains a `chunks` list. Also verifies invalid input (missing prompt, out-of-range `music_length_ms`) is rejected with `422`. **Writes `generated_comp_plan.json`** — the returned plan in render-ready `{title, chunks}` form, which `test_render_endpoint.py` then renders directly.

### [test_render_endpoint.py](test_render_endpoint.py)
Tests `POST /render` and its file-serving endpoints end to end.
- **Backend required?** Yes.
- **Inputs:** Request payloads are read from [render_test_input.json](render_test_input.json) (keys: `plan_mode`, `with_title`, `prompt_mode`) — edit that file to change variations without touching the script. Covers both render modes: a `music_v2` composition plan (chunks) and a text `prompt` with `music_length_ms` plus the extra pass-through params (`model_id`, `force_instrumental`, `output_format`, etc.). If `generated_comp_plan.json` exists (from running `test_plan_endpoint.py` first), the plan-mode render uses that exact plan instead of the static `plan_mode` fallback. No CLI arguments. (Validation cases use intentionally-invalid values that remain hardcoded.)
- **Outputs:** Prints render responses and pass/fail lines. Downloads the rendered file to `testing/music/downloaded_{filename}`. Exercises `GET /render/download/{filename}`, `GET /render/stream/{filename}`, custom-title filenames, 404 handling for missing files, and `422` validation for the prompt/chunks mutual-exclusivity rules (empty request, both provided, and `music_length_ms` without a prompt).

### [test_render_websocket.py](test_render_websocket.py)
Tests the `ws://localhost:8000/render/ws` WebSocket render endpoint.
- **Backend required?** Yes. Also requires the `websockets` library (`pip install websockets`).
- **Inputs:** No arguments. Uses the **same composition-plan source as `test_render_endpoint.py`**: prefers `generated_comp_plan.json` (from running `test_plan_endpoint.py`), else the static `plan_mode` entry in [render_test_input.json](render_test_input.json).
- **Outputs:** Prints the streamed `progress` updates through to the final `result` (filename, size, download/stream URLs). A second case sends an empty-chunks plan and asserts an `error` message is returned. (The audio file itself is written server-side to `output/music/`, not by this script.)

### [test_endpoints.py](test_endpoints.py)
General FastAPI smoke test for the infrastructure endpoints.
- **Backend required?** Yes.
- **Inputs:** Optional base-URL argument (defaults to `http://localhost:8000`), e.g. `uv run python testing/test_endpoints.py http://localhost:8000`.
- **Outputs:** Prints a colorized pass/fail table for `/`, `/health`, `/ready`, `/alive`, `/stream-example`, 404 handling, and custom `X-Request-ID` headers, plus a summary. Exits non-zero if any test fails.

---

## Service / direct-call tests (bypass the HTTP layer)

### [test_service_direct.py](test_service_direct.py)
Calls the `PromptGeneratorService` directly (no HTTP) to debug prompt generation in isolation.
- **Backend required?** No — needs `OPENAI_API_KEY`.
- **Inputs:** No arguments (the `PromptGenerationRequest` is hardcoded in the script).
- **Outputs:** Prints the generated prompt and its character count. Exits `0` on success, `1` on failure.

### [test_create_comp_plan.py](test_create_comp_plan.py)
Calls the ElevenLabs SDK directly: `music.composition_plan.create` (`model_id="music_v2"`).
- **Backend required?** No — needs `ELEVENLABS_API_KEY`.
- **Inputs:** Reads the prompt text from [../prompts/user_prompt.txt](../prompts/user_prompt.txt); `music_length_ms` is hardcoded (10000).
- **Outputs:** Prints the raw composition-plan JSON to stdout. Writes no files.

### [test_render_music.py](test_render_music.py)
Calls the ElevenLabs SDK directly: `music.compose_detailed` (`model_id="music_v2"`).
- **Backend required?** No — needs `ELEVENLABS_API_KEY`.
- **Inputs:** Reads the composition plan from [../prompts/sample_comp_plan.json](../prompts/sample_comp_plan.json); the output title is set via the `TRACK_TITLE` constant in the script.
- **Outputs:** Prints the track JSON and filename, saves the audio to `testing/music/`, and plays it back through the speakers.

---

## Utilities

### [debug_env.py](debug_env.py)
Diagnostic script for environment/SDK setup.
- **Backend required?** No.
- **Inputs:** Reads the `.env` file; no arguments.
- **Outputs:** Prints whether `OPENAI_API_KEY` loaded (with length and masked preview) and whether the OpenAI Agents SDK imports and an `Agent` can be constructed.
