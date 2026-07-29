# Frontend handoff — `sound_profile` is now the finetune

**Audience:** the coding agent maintaining the Keepsong frontend (`d:\Projects\keepsong`).
**Status:** the backend change is **shipped and verified**. The frontend is now the blocker.
**Companions:** [`FRONTEND_FINETUNES.md`](./FRONTEND_FINETUNES.md) (the `GET /finetunes` picker) and
[`FRONTEND_API_GUIDE.md`](./FRONTEND_API_GUIDE.md) (the full contract).

---

## 1. TL;DR

`POST /prompt` no longer takes one of five hand-authored sound presets. It takes the **finetune the
user picked**, and the backend resolves that finetune's real genre metadata to write the brief.

```jsonc
// before                                  // after
{                                          {
  "project_blueprint": "standalone_song_mini",  "project_blueprint": "standalone_song_mini",
  "sound_profile": "bright_pop_electro",        "sound_profile": "indie_dance",
                                                "finetune_id": "aslj0pdvdods2agammwb",
  "delivery_and_control": "balanced_studio",    "delivery_and_control": "balanced_studio",
  "user_narrative": "...SOUND DIRECTION: ..."   "user_narrative": "...no sound direction..."
}                                          }
```

Three things to do:

1. **Send `finetune_id` on `/prompt`.** It is **required** — omitting it is a `422`.
2. **Delete the "Choose a sound" wizard step** and the five preset values behind it. They no longer
   exist server-side.
3. **Remove the `SOUND DIRECTION:` line** you currently inject into `user_narrative`.

**This is a breaking change.** The old five values (`bright_pop_electro`, `dark_trap_night`,
`lofi_cozy`, `epic_cinematic`, `indie_live_band`) still parse as strings, but nothing maps them to
music any more — send one and you get whatever the AI infers from the words, with no finetune behind
it. There is no transitional mode; ship this together with the backend deploy.

---

## 2. Why

Genre used to have two sources of truth that could disagree: the `sound_profile` preset (what the
*prompt* described) and `finetune_id` on `/render` (what actually *generated the audio*). You were
papering over the gap by injecting a prose `SOUND DIRECTION:` line into `user_narrative`.

Now there is one source. A finetune already encodes genre, groove, tempo, energy and vocal character —
from a real trained model rather than a preset someone wrote by hand — so the backend reads that
metadata directly and the AI derives the musical specifics from it.

---

## 3. The new `/prompt` contract

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `project_blueprint` | enum | ✅ | **Unchanged.** Still the same five values. |
| `sound_profile` | **string** | ✅ | A slug naming the finetune, e.g. `indie_dance`. **No longer an enum** — any non-empty string is accepted. |
| `finetune_id` | **string** | ✅ **new** | The finetune's `id` from `GET /finetunes`. Missing → `422`. |
| `delivery_and_control` | enum | ✅ | **Unchanged.** Still the same five values. |
| `instrumental_only` | boolean | ❌ | Unchanged. |
| `user_narrative` | string \| null | ❌ | Unchanged field, **changed usage** — see §5. |

### Where the two values come from

One picker call feeds both:

```ts
const finetunes = await listFinetunes(baseUrl);   // GET /finetunes?model_id=music_v2
const chosen = finetunes.find(f => f.id === selectedId)!;

const body = {
  project_blueprint: blueprint,
  sound_profile: slugify(chosen.name ?? chosen.id),  // "Indie Dance" -> "indie_dance"
  finetune_id: chosen.id,
  delivery_and_control: delivery,
  instrumental_only: instrumentalOnly,
  user_narrative: narrative,
};
```

`sound_profile` is a **human-readable label for logs and traces**, not a lookup key — the backend
resolves genre from `finetune_id`, so a slightly-off slug is harmless. Keep the slugify simple:
lowercase, non-alphanumerics to `_`, collapse repeats. `'80s Nu-Disco Revival` → `80s_nu_disco_revival`
is fine.

### What the backend does with it

Resolves `finetune_id` against ElevenLabs (through a ~5-minute cache, so it usually adds no latency)
and hands the AI the finetune's real `name`, `primary_genre` and `tags`. The AI derives BPM, key,
groove, harmony, instrumentation and vocal character from those. Picking a different finetune genuinely
changes the music — the same narrative through Golden Hour Indie Guitar gives 112 BPM indie rock with
live drums, and through Indie Dance gives 120 BPM four-on-the-floor nu-disco.

---

## 4. Carry `finetune_id` through to `/render`

Unchanged mechanically, but now it matters more: send the **same** `finetune_id` to `/prompt` and to
`/render`. The prompt is written *for* that style; rendering with a different finetune (or none)
produces a track that doesn't match its own brief.

Keep one `finetune_id` in wizard state from the picker all the way to render. The composition plan
does **not** carry it and the render response does **not** echo it — see
[`FRONTEND_FINETUNES.md` §1](./FRONTEND_FINETUNES.md).

---

## 5. Remove the `SOUND DIRECTION:` injection

You currently build `user_narrative` like this:

```
OCCASION: This is a joyful celebration song — a birthday, achievement, or milestone. ...
SOUND DIRECTION: classic 1980s pop anthem: big analog synths, gated-reverb drums, soaring
anthemic chorus. Keep this sonic direction even where it differs from the base profile.
THE MEMORIES, in the sender's own words:
"""
Celebrate my wife dawn on her birthday.
"""
```

**Delete the `SOUND DIRECTION:` sentence entirely.** Two reasons:

1. It duplicates what the backend now supplies from the finetune's own metadata, and the two can
   disagree.
2. Its wording ("rendered through a trained style model", "base profile") is exactly the tooling
   language the system prompt is instructed never to leak into the output.

Everything else in that narrative — `OCCASION:`, `THE MEMORIES`, the target-length line — stays.

**The narrative no longer influences genre at all.** It governs lyrics, names, story and emotional
intent; the finetune governs instrumentation, tempo, groove and harmony. If a user writes "make it a
soft lullaby" but picked a metal finetune, they get metal. Surface the style choice prominently in the
UI so this isn't a surprise.

---

## 6. TypeScript changes

```ts
// DELETE this type — the values no longer exist server-side.
export type SoundProfile =
  | "bright_pop_electro" | "dark_trap_night" | "lofi_cozy"
  | "epic_cinematic" | "indie_live_band";

// ProjectBlueprint and DeliveryAndControl are UNCHANGED.

export interface PromptRequest {
  project_blueprint: ProjectBlueprint;
  sound_profile: string;            // finetune slug — open-ended, not a union
  finetune_id: string;              // NEW, required
  delivery_and_control: DeliveryAndControl;
  instrumental_only?: boolean;      // default false
  user_narrative?: string | null;   // default null
}
```

`PromptResponse.input_parameters` echoes the request, so it now includes `finetune_id` too. The
resolved finetune metadata is **not** returned — if you want to show "rendered in Indie Dance" in your
own UI, keep the picker object client-side.

---

## 7. Error handling

| Status | Cause | Handling |
| --- | --- | --- |
| `422` | `finetune_id` missing or empty | Shouldn't reach the server — disable Generate until a style is picked. |
| `422` | `project_blueprint` / `delivery_and_control` outside its enum | As before. |
| `500` | Agent or config failure | As before. |

Two non-errors worth knowing:

- **An unfamiliar `sound_profile` slug is not an error.** Any string is accepted; new finetunes work
  immediately with no backend change.
- **An unresolvable `finetune_id` still returns `200`.** If the finetune was deleted or ElevenLabs is
  unreachable, the backend logs a warning and the AI infers the genre from the slug alone. The brief is
  degraded but usable. You won't be told this happened — so prefer ids that came from a recent
  `GET /finetunes`, and don't cache them for days.

---

## 8. UI implications

The wizard goes from three preset steps to **two presets plus a style picker**:

| Step | Before | After |
| --- | --- | --- |
| 1 | Project Blueprint (5 fixed options) | **Unchanged** |
| 2 | Choose a sound (5 fixed options) | **Style picker** — populated from `GET /finetunes?model_id=music_v2` |
| 3 | Delivery & Control (5 fixed options) | **Unchanged** |

The style list is **dynamic and grows** — currently ~37 finetunes (Indie Dance, Deep House Groove,
Relaxing Ambient, Emotional Piano, 18th Century Symphony, Reggaeton, Metal, Country, …). Design for
search/grouping rather than five cards:

- Group by `primary_genre`, label with `name`, show `tags` as badges.
- Make it searchable — a fixed grid stops working past ~15 entries.
- **No "None" option here.** Unlike the render-time picker described in `FRONTEND_FINETUNES.md`, a
  style is mandatory for `/prompt`.
- If `GET /finetunes` fails (`502`), the wizard cannot proceed — show a retry rather than silently
  falling back, since there's no default genre any more.

---

## 9. Acceptance checklist

- [ ] Style picker populated from `GET /finetunes?model_id=music_v2`; Generate disabled until one is chosen.
- [ ] `/prompt` body includes both `sound_profile` (slug) and `finetune_id`.
- [ ] The five old preset values appear nowhere in the codebase.
- [ ] No `SOUND DIRECTION:` text in `user_narrative`.
- [ ] The same `finetune_id` reaches `/render` (or `/render/ws`).
- [ ] Picking two different styles with the same narrative produces audibly different tracks.
- [ ] The generated `prompt`, `title` and `description` never contain the words "finetune",
      "style model", or the raw slug. (Genre words that happen to match the finetune's name — "dark
      cinematic" for the Dark Cinematic style — are correct and expected.)
- [ ] A user who never opens the style picker cannot submit.

---

## 10. Quick reference

| Thing | Value |
| --- | --- |
| Style list | `GET /finetunes?model_id=music_v2` |
| New required field on `/prompt` | `finetune_id` |
| Changed field on `/prompt` | `sound_profile` — enum → free string (finetune slug) |
| Retired values | `bright_pop_electro`, `dark_trap_night`, `lofi_cozy`, `epic_cinematic`, `indie_live_band` |
| Removed from narrative | the `SOUND DIRECTION:` line |
| Also send to | `POST /render` / `WS /render/ws` — same `finetune_id` |
| Missing `finetune_id` | `422` |
| Unknown `finetune_id` | `200`, degraded brief, warning logged server-side |
| Interactive schema | `GET /docs` → **Prompt Generation** |
