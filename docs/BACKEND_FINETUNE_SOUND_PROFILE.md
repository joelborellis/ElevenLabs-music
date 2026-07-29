# Backend change — `sound_profile` becomes the finetune

**Target repo:** `d:\Projects\ElevenLabs-music`
**Driven by:** the Keepsong frontend (`d:\Projects\keepsong`), which is dropping its "Choose a sound" wizard step.
**Status:** the frontend cannot ship its side until this lands. Do this first.

---

## 1. What is changing

Today `POST /prompt` takes `sound_profile` as one of five hand-authored presets — `bright_pop_electro`, `dark_trap_night`, `lofi_cozy`, `epic_cinematic`, `indie_live_band` — each expanded by a static eleven-attribute mapping block in `prompts/generate_music_prompt.md`.

Those five values are being **deleted, not deprecated**. From now on `sound_profile` **always** carries a slug naming an ElevenLabs music finetune, and that finetune is what the render step actually uses:

```jsonc
// before
{ "sound_profile": "bright_pop_electro" }

// after
{ "sound_profile": "indie_dance", "finetune_id": "aslj0pdvdods2agammwb" }
```

The rationale: a finetune already encodes genre, groove, tempo, energy and vocal character — the exact job `sound_profile` was doing — but from a real trained model rather than a preset someone wrote by hand. Two sources of genre truth became one.

**Consequence for this file's authors:** the preset list is no longer a closed set you maintain. Finetunes appear and disappear in ElevenLabs without any code change here, so `generate_music_prompt.md` must stop *looking genres up* and start *deriving* them. That is the substance of this work — see §4.

---

## 2. Two hazards to design against

**A. The enum rejects it before anything runs.** `models/prompt.py:19` declares `SoundProfile(str, Enum)`, and `PromptGenerationRequest.sound_profile` is typed to it. Sending `indie_dance` today is a Pydantic `422` — the agent never executes. The type must be relaxed.

**B. The Defaults rule silently swallows it.** `prompts/generate_music_prompt.md:290-295` currently says:

> If any required key is missing **or unrecognized**, default to: … `sound_profile`: `lofi_cozy`

So the moment hazard A is fixed and unknown slugs start arriving, every single song silently becomes lo-fi. No error, no 422, no log line — just a quietly wrong genre on every render. **Fixing the model without fixing the system prompt is worse than shipping neither.**

---

## 3. Where the genre detail comes from

A slug is thin. `indie_dance` cannot tell the agent a tempo, a key, an instrumentation palette or a vocal character — but the finetune's own metadata largely can:

```jsonc
{ "name": "Indie Dance", "primary_genre": "Indie",
  "tags": ["Electronic", "House", "Nu-Disco", "Deep House", "Indie Dance"] }
```

**Resolve it server-side.** `services/finetune_service.py` already exposes `get_finetune_service()` as a singleton with a 300-second TTL cache (`CACHE_TTL_SECONDS`, line 27) and already filters to `status == "completed"` (line 146). Looking up one id is nearly always a cache hit — no added latency in the common case, and the backend stays the single source of truth rather than trusting genre metadata forwarded by a browser.

**Recommended contract:** `finetune_id` is **required** whenever `sound_profile` is present. If it is missing, return `422` rather than guessing. If lookup fails (deleted finetune, ElevenLabs unreachable), fall back to inferring from the slug alone and log a warning — degraded but not broken. Never substitute a generic profile.

---

## 4. `prompts/generate_music_prompt.md` — the load-bearing change

Four edits.

### 4a. Replace all of Section B (lines 85-151)

Delete the five `### bright_pop_electro` … `### indie_live_band` blocks entirely and replace with a derivation procedure:

````markdown
## B) Sound Profile — trained style models (dynamic)

`sound_profile` is **not** a fixed preset id. It is a slug naming an ElevenLabs music
finetune that the render step will actually use — e.g. `indie_dance`, `warm_tape_soul`,
`80s_synthwave`. There is no closed list; new finetunes appear without any change to
this file, so never treat an unfamiliar value as an error.

When available you will also receive `finetune_context`, resolved from that finetune:

- `name` — human name, e.g. "Indie Dance"
- `primary_genre` — e.g. "Indie"
- `tags` — e.g. ["Electronic", "House", "Nu-Disco", "Deep House"]

**Derive the eleven sound attributes from that context** — the same attributes the old
fixed presets specified, now inferred rather than looked up:

- primary_genre_family — from `primary_genre` and `tags`
- genre_fusion_accent — where the tags span more than one family
- mood_tonal_color — from the tags' emotional register
- energy_curve
- tempo_bpm — choose a specific BPM idiomatic to that genre
- key_tonality
- groove_feel
- harmony_complexity
- instrumentation_palette — the instruments the genre is actually made of
- lead_focus
- vocal_character

**Rules**

1. The finetune's genre is **authoritative** for instrumentation, tempo, groove and
   harmony. Never override it with a genre implied by the occasion in `user_narrative`.
2. `user_narrative` still governs lyrics, names, story and emotional intent, and may
   shape mood and dynamics — but not genre.
3. **Never name the finetune in your output.** Do not write its name, its slug, or the
   words "finetune" / "style model" / "trained model" into the prompt. The prompt
   describes music to a music model; it must not describe the tooling.
4. If `finetune_context` is absent, infer the genre from the slug alone
   (`warm_tape_soul` → warm vintage soul) and proceed. Do **not** fall back to a
   generic lo-fi or pop profile.
````

### 4b. Amend Defaults (lines 290-295)

```markdown
# Defaults

If `project_blueprint` or `delivery_and_control` is missing or unrecognized, default to:
- `project_blueprint`: `podcast_voiceover_loop`
- `delivery_and_control`: `balanced_studio`

`sound_profile` has **no default**. It always names a finetune. If it is missing
entirely, treat the request as invalid — never substitute a genre.
```

### 4c. Update the input description (lines 17-26)

Line 17 calls the payload "three preset IDs". It is now two preset ids plus a style reference. List `finetune_context` under the optional keys.

### 4d. Generalize conflict rule 4 (lines 219-224)

It maps *"electronic → synth lead, band → guitar lead, minimal → piano lead, cinematic → orchestral motif"* off the old fixed profiles. Reword to key off the derived `primary_genre_family` instead of the five retired ids.

---

## 5. Code changes

| File | Line | Change |
|---|---|---|
| `models/prompt.py` | 19-26 | **Delete** `class SoundProfile(str, Enum)` entirely |
| `models/prompt.py` | 46-49 | `sound_profile: str = Field(..., description="Slug naming the finetune used for rendering")` |
| `models/prompt.py` | after 53 | Add `finetune_id: str \| None = Field(default=None, description="Resolves sound_profile to real finetune metadata")` |
| `models/prompt.py` | 63-89 | Update the three `json_schema_extra` examples — they all carry retired values |
| `models/__init__.py` | 7, 15 | Remove `SoundProfile` from the import and `__all__` |
| `routers/prompt.py` | 106 | `request_data.sound_profile.value` → `request_data.sound_profile` (**AttributeError on a plain str**) |
| `routers/prompt.py` | 119 | same |
| `routers/prompt.py` | 33-51 | Update the OpenAPI docstring parameter list and example |
| `services/prompt_generator.py` | 125 | `request.sound_profile.value` → `request.sound_profile` (**same crash**) |
| `services/prompt_generator.py` | ~118-130 | Resolve `finetune_id` via `get_finetune_service()` and merge `finetune_context` into the JSON handed to the agent in `generate_prompt()` |

There is **no** `testing/test_agents.py` — `docs/ADDING_PRESET_GUIDE.md:31,140-159` claims there is and that it holds duplicate enum definitions. That file is gone; the guide is stale. Ignore those steps.

### Test and fixture files

| File | Change |
|---|---|
| `testing/test_service_direct.py:15,31,39` | Drops the `SoundProfile` import, the `SoundProfile.BRIGHT_POP_ELECTRO` argument, and a `.value` access |
| `testing/prompt_test_cases.json` | 6 occurrences — replace with real finetune slugs + ids |
| `prompts/sample_post_prompt.json` | 1 occurrence |

---

## 6. Documentation

| File | Notes |
|---|---|
| `CLAUDE.md:58` | Lists all five values on one line — the most important doc fix |
| `docs/PRESETS_GUIDE.md` | Largest surface: §"Choice 2: Sound Profile" (lines 125-230ish) plus the Quick Reference tables at 398-407. The three-choice framing itself is now a two-choice-plus-style framing |
| `docs/PROMPT_API.md` | 12 occurrences |
| `docs/QUICKSTART.md` | 2 occurrences |
| `docs/FRONTEND_API_GUIDE.md` | 4 occurrences — this is the contract the frontend reads; keep it accurate |
| `docs/ADDING_PRESET_GUIDE.md` | Its entire SoundProfile track is now obsolete. Either delete that section or retitle it "adding a Project Blueprint or Delivery preset" and note that sound profiles are no longer authored by hand |
| `README.md` | 3 occurrences |

---

## 7. Coordination with the frontend

The frontend today injects a `SOUND DIRECTION:` line into `user_narrative` describing the finetune in prose. **Once the backend resolves `finetune_id` itself, that line is removed** — it would otherwise duplicate `finetune_context`, and its current wording ("rendered through a trained style model") is exactly what rule 3 above forbids leaking into the prompt.

Ordering: ship the backend behind the tolerant contract first (accept `finetune_id`, keep accepting the old five values so nothing breaks mid-deploy), then land the frontend, then delete the five legacy values.

---

## 8. Acceptance

1. `POST /prompt` with `{"sound_profile": "indie_dance", "finetune_id": "<real id>", "project_blueprint": "standalone_song_mini", "delivery_and_control": "balanced_studio", "user_narrative": "Celebrate my wife dawn on her birthday."}` returns a brief describing **house / nu-disco / dance** music. If it comes back lo-fi, edit 4b did not take.
2. The returned `prompt` string contains no occurrence of `"Indie Dance"`, `indie_dance`, `finetune`, or `style model` (rule 3).
3. A slug for a finetune that does not exist → warning logged, brief still generated by inferring from the slug, no 500.
4. `sound_profile` present with no `finetune_id` → `422`, not a silent default.
5. A second call with a different finetune produces a materially different tempo/instrumentation for the same narrative — proof the derivation is actually reading the metadata rather than pattern-matching the occasion.
6. Existing `/render` and `/plan` paths are untouched: finetunes already work there via `finetune_id`, and this change adds nothing to them.
