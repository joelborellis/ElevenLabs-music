# Adding a New Preset Option - Implementation Guide

## Overview

Adding a new preset option to any of the three categories (ProjectBlueprint, SoundProfile, or DeliveryAndControl) requires updating **10 files** across the codebase.

---

## Files Requiring Modification

### Critical (Code Changes)

| File | Purpose |
|------|---------|
| `models/prompt.py` | **Primary enum definitions** - Add new enum value here first |
| `prompts/generate_music_prompt.md` | **AI system prompt** - Contains authoritative preset mappings the OpenAI Agent reads |

### Documentation Updates

| File | Purpose |
|------|---------|
| `docs/PRESETS_GUIDE.md` | User-friendly preset guide with detailed descriptions |
| `docs/PROMPT_API.md` | API documentation with parameter descriptions and examples |
| `README.md` | Project overview listing all preset options |
| `CLAUDE.md` | Developer instructions with preset system overview |

### Test Files

| File | Purpose |
|------|---------|
| `testing/test_agents.py` | Contains **duplicate** enum definitions (should import from models) |
| `testing/test_prompt_endpoint.py` | API endpoint test cases using preset combinations |
| `testing/test_service_direct.py` | Direct service layer tests |

### Optional (OpenAPI Examples)

| File | Purpose |
|------|---------|
| `routers/prompt.py` | May need to update OpenAPI example values in docstrings |

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

**For SoundProfile:**
```python
class SoundProfile(str, Enum):
    """Sound profile presets defining the genre and sonic characteristics."""

    BRIGHT_POP_ELECTRO = "bright_pop_electro"
    DARK_TRAP_NIGHT = "dark_trap_night"
    LOFI_COZY = "lofi_cozy"
    EPIC_CINEMATIC = "epic_cinematic"
    INDIE_LIVE_BAND = "indie_live_band"
    # ADD NEW PRESET HERE, e.g.:
    # ACOUSTIC_SINGER_SONGWRITER = "acoustic_singer_songwriter"
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

This is the **most important file** - it contains the authoritative mappings that the AI agent uses.

**For ProjectBlueprint (Section A):**
Add a new section following the existing format:
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

**For SoundProfile (Section B):**
```markdown
### `your_new_preset_id`
- primary_genre_family: [Genre category]
- genre_fusion_accent: [None or describe fusion]
- mood_tonal_color: [Describe mood]
- energy_curve: [Build → Drop / Steady / etc.]
- tempo_bpm: [BPM range]
- key_tonality: [Key or "Choose best-fitting key"]
- groove_feel: [Straight 4/4 / Swing / Half-time / etc.]
- harmony_complexity: [Simple pop / Modal / Jazz-leaning / etc.]
- instrumentation_palette: [Describe instruments]
- lead_focus: [What leads the melody]
- vocal_character: [If vocals enabled, describe voice style]
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

---

### Step 3: Update `testing/test_agents.py`

Add the same enum value to the duplicate definitions in this file:

```python
# Around line 28-50
class ProjectBlueprint(str, Enum):
    # ... existing values ...
    YOUR_NEW_PRESET = "your_new_preset_id"

class SoundProfile(str, Enum):
    # ... existing values ...
    YOUR_NEW_PRESET = "your_new_preset_id"

class DeliveryAndControl(str, Enum):
    # ... existing values ...
    YOUR_NEW_PRESET = "your_new_preset_id"
```

**Note:** Ideally, refactor this file to import from `models/prompt.py` instead of duplicating.

---

### Step 4: Update Documentation Files

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

#### `README.md`
- Add to the "Available Presets" section under the appropriate category

#### `CLAUDE.md`
- Add to the preset lists in "The Three-Choice Preset System" section

---

### Step 5: Update Test Files (Optional but Recommended)

#### `testing/test_prompt_endpoint.py`
Add a new test case using the preset:
```python
{
    "name": "Your New Test Case Name",
    "payload": {
        "project_blueprint": "your_blueprint",
        "sound_profile": "your_sound_profile",
        "delivery_and_control": "your_delivery",
        "instrumental_only": False,
        "user_narrative": "Your test narrative"
    }
}
```

#### `testing/test_service_direct.py`
No changes typically needed unless you want explicit test coverage.

---

### Step 6: Optional - Update Router Examples

#### `routers/prompt.py`
If desired, update the OpenAPI examples in the docstring to include the new preset.

---

## Files NOT Requiring Modification

- `models/__init__.py` - Auto-exports from prompt.py
- `services/prompt_generator.py` - Uses enum values dynamically
- `main.py` - No direct preset references

---

## Key Insight: Duplicate Enum Definitions

There are **two places** where presets are currently defined:
1. `models/prompt.py` - Canonical source (used by API)
2. `testing/test_agents.py` - Duplicate definitions (original CLI wizard)

**Recommended Refactor:** Update `test_agents.py` to import from `models/prompt.py`:
```python
from models.prompt import ProjectBlueprint, SoundProfile, DeliveryAndControl
```

This would eliminate the need to maintain two copies and reduce the files needing updates from 10 to 9.

---

## Validation Checklist

After making changes, verify:

- [ ] API accepts the new preset value (test with curl or /docs)
- [ ] Generated prompts correctly incorporate the preset mappings
- [ ] Documentation is consistent across all files
- [ ] Tests pass with the new preset

---

## Example: Adding `acoustic_singer_songwriter` to SoundProfile

### 1. `models/prompt.py` (line 26):
```python
ACOUSTIC_SINGER_SONGWRITER = "acoustic_singer_songwriter"
```

### 2. `prompts/generate_music_prompt.md` (after line 150):
```markdown
### `acoustic_singer_songwriter`
- primary_genre_family: Acoustic / Singer-Songwriter
- genre_fusion_accent: None (pure genre)
- mood_tonal_color: Intimate / Heartfelt
- energy_curve: Gentle dynamics (quiet verses, slightly bigger choruses)
- tempo_bpm: 80-100 BPM (choose a specific BPM)
- key_tonality: Choose best-fitting key (often G, C, or D major)
- groove_feel: Fingerpicking or gentle strumming
- harmony_complexity: Folk/pop (open chords, occasional suspensions)
- instrumentation_palette: Acoustic (acoustic guitar, light percussion, possibly strings or piano)
- lead_focus: Vocal lead with acoustic guitar accompaniment
- vocal_character: Warm & conversational
```

### 3. `testing/test_agents.py` (line 41):
```python
ACOUSTIC_SINGER_SONGWRITER = "acoustic_singer_songwriter"
```

### 4-6. Update all documentation files with user-friendly descriptions.

---

## Timeline Estimate

- Code changes (Steps 1-3): ~15 minutes
- Documentation updates (Steps 4-6): ~30 minutes
- Testing & validation: ~15 minutes
- Total: ~1 hour per new preset
