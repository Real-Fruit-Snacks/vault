# Pet enhancements + management panel — design

**Status:** approved (brainstorm)
**Date:** 2026-07-07

## Goal

Bring the four portable enhancements from the standalone
`Real-Fruit-Snacks/terminal-workbench-pet` Obsidian plugin into the vault
website's ghost pet, and add a dedicated pet-management popover to control the
now-larger feature set. React-to-writing is intentionally excluded (the site is
read-only, so there is no typing to react to).

## Approach

Keep the site's existing, hand-tuned `site-assets/pet.js` engine (slow jellyfish
drift with pauses, edge fade / pop-in, peek-a-boo, read-along, spook, bored spin,
nap, boop-to-recolor) and **add the missing delta into it**. The plugin's browser
build, `docs/pet-demo.js` in the pet repo, is the reference implementation for the
new-feature code (drag/fling, speech bubbles). We are **not** replacing our engine
with the plugin's — that would discard the pacing tuned in this codebase. This
work is additive.

## Features

### Drag & fling
- `mousedown` / `touchstart` on the ghost sprite begins a grab. A small movement
  threshold distinguishes a drag from a boop-click (a click that never crosses the
  threshold still triggers the existing boop/recolor; a drag suppresses it).
- While held, the ghost tracks the pointer and records recent pointer velocity.
- On release:
  - **Roam mode:** the ghost keeps the release velocity and sails with momentum,
    bouncing off the viewport edges with damping until speed decays, then rejoins
    the drift state machine.
  - **Cursor / off:** it simply drops (no momentum).
- Under `prefers-reduced-motion`, drag still repositions the ghost but fling
  momentum is suppressed (it drops in place).

### Speech bubbles
- A small CSS bubble anchored above the ghost showing brief terminal-style quips:
  `zzz` (napping), `reading…` (read-along), `boop me?` (idle but awake), and a
  short cheer on boop.
- Rate-limited so it is occasional, not chatty. Only appears when the Speech
  bubbles quirk is enabled (off by default).

### Size & opacity
- Driven by CSS custom properties on the pet root (e.g. `--pet-scale` and a base
  opacity variable). The engine's geometry math (size, clamping, perch/anchor
  targets) reads the scaled size so drift and edge-clamping remain correct at any
  size.

### Per-quirk toggles
- Each quirk — nap, flee (spook), read-along, tricks (bored spin), speech — is
  gated by a boolean flag. A disabled quirk is skipped in the state machine
  (e.g. flee off means the proximity check never triggers a spook; nap off means
  the idle timer never naps).

## Pet management panel (anchored popover)

The top-bar settings cog menu gains a **"Pet"** row. Instead of cycling the mode
inline (today's behavior), clicking it opens a **second anchored popover** beneath
the cog, using the same visual language as the settings menu. The whole panel —
like the current pet row — renders only when `pet_enabled` is true in
`site.config.json`.

Contents, in **two labeled groups**:

- **Appearance**
  - Mode — segmented control: Roam / Cursor / Off
  - Size — slider
  - Opacity — slider
  - Color — 6 theme-palette swatches (green, cyan, amber, violet, orange, red)
- **Behavior**
  - Nap when idle — toggle
  - Flee from cursor — toggle
  - Read along — toggle
  - Do tricks — toggle
  - Speech bubbles — toggle

## State & persistence

localStorage, following the existing `twb-*` convention, all read by the pre-paint
head script like the other settings:

| Key | Meaning | Status |
|---|---|---|
| `twb-pet` | mode (cursor/float/off) | exists |
| `twb-pet-color` | palette index | exists |
| `twb-pet-size` | size (slider value) | new |
| `twb-pet-opacity` | opacity (slider value) | new |
| `twb-pet-nap` | nap quirk on/off | new |
| `twb-pet-flee` | flee quirk on/off | new |
| `twb-pet-read` | read-along quirk on/off | new |
| `twb-pet-tricks` | tricks quirk on/off | new |
| `twb-pet-speech` | speech quirk on/off | new |

The panel writes these keys and dispatches the existing `twb:pet` event; the engine
re-reads its live configuration on that event (as it already does for mode).

## Defaults & reduced motion

- Quirks default **on**, except **speech off** (matches the plugin).
- Mode default stays **Roam**; size/opacity default to the current appearance.
- `prefers-reduced-motion`: static ghost as today; drag repositions but fling
  momentum is suppressed.

## Architecture / boundaries

- `site-assets/pet.js` — behavior engine; gains drag/fling, speech, size/opacity
  scaling, and quirk-gating. Stays a single ES5 IIFE.
- `site-assets/site.css` — pet panel styles, speech-bubble styles, size/opacity
  variables.
- `site-assets/app.js` — wires the settings "Pet" row to open/close the pet
  popover and binds the panel controls (sliders/toggles/swatches) to their
  localStorage keys + `twb:pet` dispatch, mirroring how existing settings rows
  work.
- `tools/ssg/pages.py` — emits the Pet row + panel markup, gated on `pet_enabled`;
  the pre-paint head script gains the new keys.

## Testing

- Python (`tests/test_pages.py`): assert the Pet row and panel container (with the
  new control IDs) render when `pet_enabled=True` and are absent when false; assert
  the pre-paint script references the new keys.
- JS behavior (drag/fling, speech, sliders, toggles) is verified live in the
  browser preview, consistent with how the current pet is validated (the engine is
  not covered by the Python unit suite).

## Out of scope

- React-to-writing (no editing surface on a static site).
- Replacing the tuned engine with the plugin's engine.
- Any networked / telemetry behavior (the site loads no external resources).
