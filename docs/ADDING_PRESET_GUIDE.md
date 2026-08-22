# Adding a Project Blueprint or Delivery preset - Implementation Guide

## Overview

There are **two** hand-authored preset categories left: `ProjectBlueprint` (use case and structure) and
`DeliveryAndControl` (workflow and strictness). Adding a value to either means touching a handful of
files, listed below.

> **Sound profiles are no longer authored by hand.** `sound_profile` names an ElevenLabs music
> finetune, and the AI derives genre, tempo, groove and instrumentation from that finetune's own
> metadata. New styles become available the moment a finetune is created in ElevenLabs — there is
> nothing to add to this codebase, and no enum to extend. See
> [`PRESETS_GUIDE.md`](./PRESETS_GUIDE.md) and [`FRONTEND_FINETUNES.md`](./FRONTEND_FINETUNES.md).

---

## Files Requiring Modification

### Critical (Code Changes)

| File | Purpose |
|------|---------|
| `models/prompt.py` | **Primary enum definitions** - Add the new enum value here first |
| `prompts/generate_music_prompt.md` | **AI system prompt** - Contains the authoritative preset mappings the OpenAI Agent reads |

### Documentation Updates

| File | Purpose |
|------|---------|
| `docs/PRESETS_GUIDE.md` | User-friendly preset guide with detailed descriptions |
| `docs/PROMPT_API.md` | API documentation with parameter descriptions and examples |
| `docs/FRONTEND_API_GUIDE.md` | The contract the frontend builds its wizard from |
| `README.md` | Project overview listing all preset options |
| `CLAUDE.md` | Developer instructions with preset system overview |

### Test Files

| File | Purpose |
|------|---------|
| `testing/prompt_test_cases.json` | Payloads driving `testing/test_prompt_endpoint.py` |
| `testing/test_service_direct.py` | Direct service layer test |

### Optional (OpenAPI Examples)

| File | Purpose |
|------|---------|
| `routers/prompt.py` | May need updated OpenAPI example values in the endpoint description |

---

## Step-by-Step Implementation

### Step 1: Add to `models/prompt.py`

Add the new enum value to the appropriate class:

**For ProjectBlueprint:**
```python
class ProjectBlueprint(str, Enum):
    """Project blueprint presets defining the use case and structure."""

    AD_BRAND_FAST_HOOK = "ad_brand_fast_hook"
    PODCAST_VOICEOVER_LOOP = "podcast_voiceover_loop"
    VIDEO_GAME_ACTION_LOOP = "video_game_action_loop"
    MEDITATION_SLEEP = "meditation_sleep"
    STANDALONE_SONG_MINI = "standalone_song_mini"
    # ADD NEW PRESET HERE, e.g.:
    # CORPORATE_PRESENTATION = "corporate_presentation"
```

**For DeliveryAndControl:**
```python
class DeliveryAndControl(str, Enum):
    """Delivery and control presets defining workflow and output preferences."""

    EXPLORATORY_ITERATE = "exploratory_iterate"
    BALANCED_STUDIO = "balanced_studio"
    BLUEPRINT_PLAN_FIRST = "blueprint_plan_first"
    LIVE_ONE_TAKE = "live_one_take"
    ISOLATION_STEMS = "isolation_stems"
    # ADD NEW PRESET HERE, e.g.:
    # REMIX_READY = "remix_ready"
```

---

### Step 2: Add to `prompts/generate_music_prompt.md`

This is the **most important file** — it contains the authoritative mappings that the AI agent uses.
Sections A and C are closed-set mappings; Section B is a derivation procedure and is not edited when
adding a preset.

**For ProjectBlueprint (Section A):**
```markdown
### `your_new_preset_id`
- use_case_intent: [Describe the use case]
- duration: [Duration in seconds or "Auto length"]
- looping_behavior: [Stinger ending / Loopable / Fade out / Linear]
- structure_template: [Describe the structure]
- vocal_mode: [Instrumental only / Sung lyrics / Flexible]
- lyrics_plan: [If vocals, describe lyrics approach]
- lyric_language: [Language, usually English]
- vocal_timing_cue: [When vocals start, or "(ignored)" if instrumental]
```

**For DeliveryAndControl (Section C):**
```markdown
### `your_new_preset_id`
- prompt_style_mode: [Exploratory / Balanced / Blueprint / etc.]
- strictness: [Describe constraint level]
- transition_style: [Seamless / Risers & impacts / Hard cuts / etc.]
- mix_production_aesthetic: [Lo-fi warmth / Radio polished / Cinematic wide / etc.]
- balance_priority: [Atmosphere-forward / Balanced / Melody-forward]
- isolation_intent: [None / Strong]
```

**Keep the mapping genre-neutral.** The finetune owns genre, tempo, groove, harmony and
instrumentation (Section B, rule 1). A blueprint or delivery preset that prescribes a genre will fight
whatever style the user picked. Describe *structure, duration, strictness and production stance* only.

---

### Step 3: Update Documentation Files

#### `docs/PRESETS_GUIDE.md`
Add a new section following the existing format with:
- Friendly name and description
- "What You Get" table
- "When to choose this" bullet points
- "What this does to your music" explanation
- Update the "Quick Reference" tables at the end

#### `docs/PROMPT_API.md`
- Add the new preset to the parameter descriptions list
- Add example usage if relevant

#### `docs/FRONTEND_API_GUIDE.md`
- Add the value to the preset enum table in §3.1 and to the TypeScript union in §5

#### `README.md`
- Add to the "Available Presets" section under the appropriate category

#### `CLAUDE.md`
- Add to the preset lists in "The Preset System" section

---

### Step 4: Update Test Files (Optional but Recommended)

#### `testing/prompt_test_cases.json`
Add a new case exercising the preset. Every payload needs a real `sound_profile` + `finetune_id` pair —
grab one from `testing/finetunes.json` or a live `GET /finetunes` call:

```json
{
    "name": "Your New Test Case Name",
    "payload": {
        "project_blueprint": "your_blueprint",
        "sound_profile": "lofi_pulse",
        "finetune_id": "sqwy9yr9rgik4fjq83lq",
        "delivery_and_control": "your_delivery",
        "instrumental_only": false,
        "user_narrative": "Your test narrative"
    }
}
```

#### `testing/test_service_direct.py`
No changes typically needed unless you want explicit test coverage.

---

### Step 5: Optional - Update Router Examples

#### `routers/prompt.py`
If desired, update the OpenAPI examples in the endpoint description to include the new preset.

---

## Files NOT Requiring Modification

- `models/__init__.py` - Only re-exports the enum classes, not their members
- `services/prompt_generator.py` - Uses enum values dynamically
- `services/finetune_service.py` - Concerns finetunes, not presets
- `main.py` - No direct preset references

---

## Validation Checklist

After making changes, verify:

- [ ] API accepts the new preset value (test with curl or /docs)
- [ ] Generated prompts correctly incorporate the preset mappings
- [ ] The preset does not override the finetune's genre — generate with two very different finetunes
      and confirm both still sound like their style
- [ ] Documentation is consistent across all files
- [ ] `uv run python testing/test_prompt_endpoint.py` passes

---

## Example: Adding `corporate_presentation` to ProjectBlueprint

### 1. `models/prompt.py`:
```python
CORPORATE_PRESENTATION = "corporate_presentation"
```

### 2. `prompts/generate_music_prompt.md` (Section A):
```markdown
### `corporate_presentation`
- use_case_intent: Corporate deck / Conference presentation bed
- duration: 120 seconds
- looping_behavior: Loopable
- structure_template: Ambient Evolution (steady, unobtrusive; no hard cuts)
- vocal_mode: Instrumental only
- vocal_timing_cue: (ignored)
```

### 3. Update the documentation files with user-friendly descriptions.

---

## Timeline Estimate

- Code changes (Steps 1-2): ~15 minutes
- Documentation updates (Step 3): ~30 minutes
- Testing & validation: ~15 minutes
- Total: ~1 hour per new preset
