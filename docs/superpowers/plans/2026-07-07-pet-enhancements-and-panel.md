# Pet Enhancements + Management Panel — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add drag/fling, speech bubbles, size/opacity, and per-quirk toggles to the site's ghost pet, plus an anchored pet-management popover to control them.

**Architecture:** Extend the existing `site-assets/pet.js` ES5 IIFE engine in place (it already contains the drift/peek/read/spook/spin/nap/vanish behaviors). Port the four new capabilities from the plugin's browser build (reference: the pet repo's `docs/pet-demo.js`, saved locally at `SCRATCH/pet-demo.js`), adapting names to our conventions (`#site-pet`, `data-pet`, `twb-pet-*` localStorage, `article.note` targets, `TOP_CLAMP = 88`). The pet panel markup is emitted by `tools/ssg/pages.py` gated on `pet_enabled`; `site-assets/app.js` wires the controls to localStorage + the existing `twb:pet` event.

**Tech Stack:** Pure-Python SSG (`tools/ssg`, stdlib + `string.Template`), vanilla ES5 browser JS, CSS with `--twb-*` tokens. Tests: stdlib `unittest`.

## Global Constraints

- Pet JS stays a **single ES5 IIFE** in `site-assets/pet.js` — `var` only, no `let`/`const`/arrow/template-literals (matches the existing file).
- All persisted state uses **`localStorage` `twb-*` keys**, read by the pre-paint head `<script>` in `tools/ssg/pages.py` like every other setting.
- The entire pet feature (element, panel row, panel) renders **only when `config.pet_enabled` is true**.
- **No external resources** — no network, no CDNs; assets stay local relative paths.
- **`prefers-reduced-motion`**: ghost holds still (no drift/fling momentum/animation); drag still repositions.
- **Reference for verbatim engine code:** the pet repo `docs/pet-demo.js` — but it is an Obsidian build. Do **not** copy its Obsidian bits: `noteEl()` (use our `article.note` selectors, already in `pet.js`), `onKey`/`cheer`/`reactions` (excluded — read-only site), the standalone bootstrap, or `#tw-pet`/`--ta-*`/`tw-pet-color` names.
- **Defaults:** mode `float` (Roam, unchanged); quirks nap/flee/read/tricks **on**, speech **off**; size 28, opacity 70.
- Commit authored as `Real-Fruit-Snacks`; **no AI attribution** in messages.
- `SCRATCH` in this plan = `C:/Users/Matt/AppData/Local/Temp/claude/C--Users-Matt-Documents-Obsidian---Website/4722cae0-c5bb-4f05-a0b6-01f52924f363/scratchpad`.

## File Structure

- `site-assets/pet.js` — behavior engine. Gains: `readCfg()` (reads new keys), `applySize()`/`applyOpacity()` (CSS vars), `say()`+`QUIPS` (speech), pointer-based drag/fling, quirk gates, and a `lastMode`-guarded `twb:pet` handler so slider changes don't teleport the ghost.
- `site-assets/site.css` — `#site-pet` size/opacity via CSS vars; `.pet-bubble` styles; `.pet-panel` styles (two groups, sliders, toggles, swatches); sprite `cursor: grab` + `touch-action: none`.
- `site-assets/app.js` — opens/closes the pet popover from the settings "Pet" row and binds panel controls to `twb-pet-*` keys + `twb:pet` dispatch.
- `tools/ssg/pages.py` — pre-paint head script gains the new keys + `--pet-size`/`--pet-base-opacity`; the settings menu's pet row becomes a "Pet" opener; new `pet_panel` markup slot, gated on `pet_enabled`.
- `tests/test_pages.py` — assert head-script keys and gated panel markup.

**Current facts to rely on (verified):**
- Head pre-paint script is one line at `tools/ssg/pages.py:26`; it sets `data-pet` via `var pm=localStorage.getItem("twb-pet");if(pm!=="cursor")document.documentElement.setAttribute("data-pet",pm==="off"?"off":"float");`
- Settings menu rows are at `pages.py:45-52`; the pet row is injected via the `$pet_toggle` slot (`pages.py:52`, built at `pages.py:249-258`, substituted at `pages.py:274`).
- Pet element markup `PET_HTML` is at `pages.py:106-108`: `<div id="site-pet" aria-hidden="true"><div class="pet-tilt"><div class="pet-sprite" title="pet the ghost to recolor it">…svg…</div></div></div>`.
- `#site-pet` CSS is at `site-assets/site.css:65-72` (`width:28px;height:28px; … opacity:0.7; transition:opacity .9s ease`). Color rules `.pet-body{fill:var(--twb-accent)}` + `#site-pet[data-color="N"] .pet-body` exist below it.
- `pet.js` geometry already uses a `SIZE` value, `MARGIN`, `TOP_CLAMP=88`, `maxX/maxY`, `clampX/clampY`, `renderAt`, `roamPhase`, `enterDrift`, `stepRoam`, `tick`, `schedule`, and a `twb:pet` listener + `sprite.addEventListener("click", …)` boop handler + `setBoopable`.

---

### Task 1: Size & opacity (CSS vars, config, pre-paint)

**Files:**
- Modify: `site-assets/site.css:65-72` (`#site-pet` block)
- Modify: `tools/ssg/pages.py:26` (head script) and `tools/ssg/pages.py:106-108` if needed
- Modify: `site-assets/pet.js` (SIZE→live, `readCfg`, `applySize`, `applyOpacity`, `twb:pet` guard)
- Test: `tests/test_pages.py`

**Interfaces:**
- Produces (pet.js): `readCfg()` populates module vars `cfgNap, cfgFlee, cfgRead, cfgTricks, cfgSpeech` (booleans) and calls `applySize()`/`applyOpacity()`; `SIZE` becomes a `var` updated by `applySize()`. Later tasks read those cfg vars.
- Produces (localStorage): keys `twb-pet-size` (int px, 16–64, default 28), `twb-pet-opacity` (int %, 15–100, default 70).

- [ ] **Step 1: Failing test — head script exposes size/opacity**

In `tests/test_pages.py`, inside `class RenderTests` (near the existing `test_pet_toggle_tracks_pet_enabled`), add:

```python
def test_pet_head_script_has_appearance_keys(self):
    on = pages.render_page(config=SiteConfig(pet_enabled=True), output_path="x.html",
                           page_title="X", content_html="", nav_html="")
    self.assertIn("twb-pet-size", on)
    self.assertIn("twb-pet-opacity", on)
    self.assertIn("--pet-size", on)
    self.assertIn("--pet-base-opacity", on)
```

- [ ] **Step 2: Run it — expect FAIL**

Run: `python -m unittest tests.test_pages -v`
Expected: FAIL (`twb-pet-size` not found).

- [ ] **Step 3: Extend the pre-paint head script**

In `tools/ssg/pages.py:26`, find the pet segment inside the `<script>`:

```js
var pm=localStorage.getItem("twb-pet");if(pm!=="cursor")document.documentElement.setAttribute("data-pet",pm==="off"?"off":"float");
```

Immediately after it (still inside the same `(function(){…})()`), append:

```js
var ps=parseInt(localStorage.getItem("twb-pet-size"),10);if(ps>=16&&ps<=64)document.documentElement.style.setProperty("--pet-size",ps+"px");var po=parseInt(localStorage.getItem("twb-pet-opacity"),10);if(po>=15&&po<=100)document.documentElement.style.setProperty("--pet-base-opacity",(po/100).toFixed(3));
```

(Do not use a regex literal or an unescaped `$` — the file is a `string.Template`; `$` must be `$$` if ever needed. The code above has none.)

- [ ] **Step 4: Point `#site-pet` at the vars**

In `site-assets/site.css:65-72`, change the two lines:

```css
  position: fixed; left: 0; top: 0; width: 28px; height: 28px;
```
to
```css
  position: fixed; left: 0; top: 0;
  width: var(--pet-size, 28px); height: var(--pet-size, 28px);
```
and change
```css
  opacity: 0.7;  /* translucent, ghostly; dims further while napping */
```
to
```css
  opacity: var(--pet-base-opacity, 0.7);  /* translucent; dims further while napping */
```

- [ ] **Step 5: Make `SIZE` live + add config/appearance in `pet.js`**

In `site-assets/pet.js`, near the top constants, replace the fixed `SIZE`/geometry seed. Find the line that sets `SIZE` (currently `var SIZE = 28,` inside the constants, or `var SIZE = 28;`). Introduce bounded read + live var:

```js
var SIZE_MIN = 16, SIZE_MAX = 64, SIZE_DEFAULT = 28;
function readSize() {
  var s = parseInt(localStorage.getItem("twb-pet-size"), 10);
  if (!(s >= SIZE_MIN && s <= SIZE_MAX)) s = SIZE_DEFAULT;
  return s;
}
var SIZE = readSize();
```

Add appearance + config readers (place them beside the existing color helpers):

```js
// Per-quirk flags + appearance, read from localStorage (default on; speech off).
var cfgNap = true, cfgFlee = true, cfgRead = true, cfgTricks = true, cfgSpeech = false;
function boolKey(k, dflt) {
  try {
    var v = localStorage.getItem(k);
    if (v === "on") return true;
    if (v === "off") return false;
  } catch (e) { /* private mode */ }
  return dflt;
}
function applySize() {
  SIZE = readSize();
  document.documentElement.style.setProperty("--pet-size", SIZE + "px");
  clampCore();
  apply();
}
function applyOpacity() {
  var o = parseInt(localStorage.getItem("twb-pet-opacity"), 10);
  if (!(o >= 15 && o <= 100)) o = 70;
  document.documentElement.style.setProperty("--pet-base-opacity", (o / 100).toFixed(3));
}
function readCfg() {
  cfgNap = boolKey("twb-pet-nap", true);
  cfgFlee = boolKey("twb-pet-flee", true);
  cfgRead = boolKey("twb-pet-read", true);
  cfgTricks = boolKey("twb-pet-tricks", true);
  cfgSpeech = boolKey("twb-pet-speech", false);
  applySize();
  applyOpacity();
}
```

- [ ] **Step 6: Guard the `twb:pet` handler so appearance changes don't teleport**

In `pet.js`, replace the existing `window.addEventListener("twb:pet", …)` body with a `lastMode`-guarded version (add `var lastMode = petMode();` near the other state vars first):

```js
window.addEventListener("twb:pet", function () {
  readCfg();                         // apply size/opacity/quirks live
  var m = petMode();
  if (m === "off") { lastMode = m; return; }   // schedule() parks itself
  // If a quirk toggle turned napping off mid-nap, wake up.
  if (!cfgNap && (napping || roamPhase === "nap")) {
    setNap(false);
    if (roamPhase === "nap") wakeFromNap();
  }
  if (m !== lastMode) {              // only reset the machine on a real mode change
    setNap(false);
    if (m === "float") enterRoam();
    else { pet.style.opacity = ""; lastMode2LeaveCursor(); }
  }
  lastMode = m;
  schedule();
});
```

Where the previous handler called `leaveRoam()`/reset for cursor: keep the existing cursor-restore logic you already have (rename the inline block to a small helper `function lastMode2LeaveCursor(){ clearPeek(); sprite.style.pointerEvents=""; lastMove = Date.now(); }` if the current code did those inline). Preserve current behavior exactly — the only new thing is: (a) call `readCfg()` first, (b) gate the enter/leave on `m !== lastMode`.

At init (bottom of the IIFE, where it currently reads color/schedules), add a `readCfg();` call before `schedule();`.

- [ ] **Step 7: Verify (Python test + live)**

Run: `python -m unittest tests.test_pages -v` → PASS.
Run: `python tools/build.py` → 0 warnings.
Live: start the preview, in the console run
`localStorage.setItem('twb-pet-size','48'); localStorage.setItem('twb-pet-opacity','100'); dispatchEvent(new Event('twb:pet'))`
Expected: ghost grows to 48px and becomes fully opaque **without** jumping/teleporting. Reset with `localStorage.removeItem('twb-pet-size'); localStorage.removeItem('twb-pet-opacity'); dispatchEvent(new Event('twb:pet'))`.

- [ ] **Step 8: Commit**

```bash
git add site-assets/pet.js site-assets/site.css tools/ssg/pages.py tests/test_pages.py
git commit -m "Pet: size and opacity controls via CSS vars"
```

---

### Task 2: Per-quirk gating

**Files:** Modify `site-assets/pet.js`.

**Interfaces:** Consumes `cfgNap/cfgFlee/cfgRead/cfgTricks` from Task 1. Produces: gated behavior — a disabled quirk is skipped.

- [ ] **Step 1: Gate flee (spook)**

In `maybeSpook()`, add the flag to the early-return guard. Find:
```js
if (reduced || mx === null) return;
```
change to:
```js
if (reduced || mx === null || !cfgFlee) return;
```

- [ ] **Step 2: Gate read-along**

In `maybeRead()`, find the leading guard (currently `if (reduced || petMode() !== "float" || roamPhase !== "drift") return;`) and add `|| !cfgRead`:
```js
if (reduced || !cfgRead || petMode() !== "float" || roamPhase !== "drift") return;
```

- [ ] **Step 3: Gate tricks (bored spin)**

In `driftStep()`, find:
```js
if (!spinning && now - lastStartle > BORED_AFTER) doSpin(now);
```
change to:
```js
if (cfgTricks && !spinning && now - lastStartle > BORED_AFTER) doSpin(now);
```

- [ ] **Step 4: Gate nap (roam + cursor)**

In `stepRoam()`, find the nap trigger:
```js
if ((roamPhase === "drift" || roamPhase === "peek" || roamPhase === "read") &&
    now - lastActive > NAP_AFTER)
  enterNap(now);
```
prefix with `cfgNap &&`:
```js
if (cfgNap && (roamPhase === "drift" || roamPhase === "peek" || roamPhase === "read") &&
    now - lastActive > NAP_AFTER)
  enterNap(now);
```
In the cursor-mode branch of `tick()`, find:
```js
if (!napping && now - lastMove > NAP_AFTER) setNap(true);
```
change to:
```js
if (cfgNap && !napping && now - lastMove > NAP_AFTER) setNap(true);
```

- [ ] **Step 5: Verify (live)**

Run `python tools/build.py`. In the preview console:
`localStorage.setItem('twb-pet-flee','off'); dispatchEvent(new Event('twb:pet'))` then move the cursor onto the ghost in Roam mode — it must **not** zip away. Repeat for `twb-pet-tricks='off'` (no spins), `twb-pet-read='off'`, `twb-pet-nap='off'`. Reset each with `removeItem` + dispatch.

- [ ] **Step 6: Commit**

```bash
git add site-assets/pet.js
git commit -m "Pet: per-quirk toggles (nap, flee, read-along, tricks)"
```

---

### Task 3: Speech bubbles

**Files:** Modify `site-assets/pet.js`, `site-assets/site.css`.

**Interfaces:** Consumes `cfgSpeech`, `reduced`, `pet`, `pick`. Produces: `say(text, kind, force)`.

- [ ] **Step 1: Add QUIPS + say() to pet.js**

Near the top of the IIFE (after the constants), add:

```js
var QUIPS = {
  idle:  ["> idle", "$ _", "hi", "just vibing", "boop me?", "^_^", "> uptime"],
  peek:  ["whatcha reading?", "ooh", "> peek", "nice note"],
  read:  ["reading...", "go on", "> tail -f", "good line"],
  nap:   ["zzz", "> sleep 60", "afk", "5 more min"],
  boop:  ["boop!", "yay", "<3", "again!", ":D"],
  spook: ["!", "eek", "> ^C", "yikes"],
  fling: ["wheee", "whoa", "> yeet"]
};
function pick(a) { return a[(Math.random() * a.length) | 0]; }
var lastQuip = 0, QUIP_GAP = 12000;
function say(text, kind, force) {
  if (!cfgSpeech) return;
  if (reduced && !force) return;
  var now = Date.now();
  if (!force && now - lastQuip < QUIP_GAP) return;
  lastQuip = now;
  var old = pet.querySelector(".pet-bubble");
  if (old && old.parentNode) old.parentNode.removeChild(old);
  var b = document.createElement("div");
  b.className = "pet-bubble" + (kind ? " pet-bubble-" + kind : "");
  b.textContent = text;
  pet.appendChild(b);
  setTimeout(function () { if (b.parentNode) b.parentNode.removeChild(b); }, 2600);
}
```

(If `pet.js` already defines a `pick`, reuse it — don't declare twice.)

- [ ] **Step 2: Emit quips at the behavior points**

Add these calls (match the reference `SCRATCH/pet-demo.js`):
- In `enterNap(now)`: after it sets `pet.className = "pet-nap"`, add `say(pick(QUIPS.nap));`
- In `driftStep()` resting branch (`if (holdUntil && now < holdUntil)`), add `if (Math.random() < 0.02) say(pick(QUIPS.idle));`
- In the peek entry (`enterPeek`, after it commits the perch), add `say(pick(QUIPS.peek));`
- In the read entry (`enterRead`/where `roamPhase` becomes `"read"`), add `say(pick(QUIPS.read));`
- In `zipAway(scared)` inside the `if (scared){…}` block, add `say(pick(QUIPS.spook), "boop");`
- In the boop handler (the click/pointer boop), add `say(pick(QUIPS.boop), "boop", true);`

- [ ] **Step 3: Add bubble CSS**

In `site-assets/site.css`, in the pet section (after the particle rules), add — using our `--twb-*` tokens:

```css
.pet-bubble {
  position: absolute; left: 50%; bottom: 100%; margin-bottom: 6px;
  transform: translateX(-50%);
  padding: 3px 7px; font-family: var(--twb-font-mono); font-size: 11px; line-height: 1.2;
  white-space: nowrap; color: var(--twb-text-normal);
  background: var(--twb-bg-2); border: 1px solid var(--twb-border);
  border-radius: 6px; box-shadow: 0 2px 8px rgba(0,0,0,.28);
  pointer-events: none; animation: pet-bubble-in 2.6s ease forwards;
}
.pet-bubble::after {
  content: ""; position: absolute; top: 100%; left: 50%; transform: translateX(-50%);
  border: 4px solid transparent; border-top-color: var(--twb-bg-2);
}
.pet-bubble-boop, .pet-bubble-good { color: var(--twb-accent); }
@keyframes pet-bubble-in {
  0% { opacity: 0; transform: translateX(-50%) translateY(4px); }
  12%, 82% { opacity: 1; transform: translateX(-50%) translateY(0); }
  100% { opacity: 0; transform: translateX(-50%) translateY(-2px); }
}
```

Add `.pet-bubble` to the reduced-motion `animation: none` rule already present in the pet section.

- [ ] **Step 4: Verify (live)**

`python tools/build.py`. In preview console: `localStorage.setItem('twb-pet-speech','on'); dispatchEvent(new Event('twb:pet'))`. Boop the ghost → a `boop!`/`<3` bubble appears above it. Leave it idle → occasional quips. Turn off with `removeItem` + dispatch → no bubbles.

- [ ] **Step 5: Commit**

```bash
git add site-assets/pet.js site-assets/site.css
git commit -m "Pet: optional speech bubbles"
```

---

### Task 4: Drag & fling

**Files:** Modify `site-assets/pet.js`, `site-assets/site.css`.

**Interfaces:** Consumes `sprite`, `clampX/clampY`, `MARGIN/TOP_CLAMP/maxX/maxY`, `enterDrift`, `renderAt`, `lean`, `roamPhase`, `setBoopable`, `clearPeek`, `wakeFromNap`, `spawnParticle`, `cyclePetColor`, `say`. Produces: pointer-driven drag/boop; `roamPhase` values `"drag"`, `"fling"`.

- [ ] **Step 1: Replace the click boop with a `boop()` function**

Find the existing `sprite.addEventListener("click", function () { … })` boop handler. Extract its body into a named function and delete the click listener (pointerup will call it):

```js
function boop() {
  markActivity();
  cyclePetColor();
  if (petting) return;
  petting = true;
  setNap(false);
  sprite.className = "pet-sprite pet-happy";
  if (Math.random() < 0.5) spawnParticle("♥", "pet-heart");
  else spawnParticle("!", "pet-bang");
  say(pick(QUIPS.boop), "boop", true);
  if (petMode() === "float") { wakeFromNap(); zipAway(false); }
  setTimeout(function () {
    if (!spinning) sprite.className = "pet-sprite";
    petting = false;
  }, 1100);
}
```
(Keep the exact particle/timeout logic the current handler used; the above matches `SCRATCH/pet-demo.js` lines 302–317.)

- [ ] **Step 2: Add drag/fling state + functions**

Near the other state vars add:
```js
var drag = null, flingVX = 0, flingVY = 0;
```
Add (bodies verbatim from `SCRATCH/pet-demo.js` lines 319–356, names already match ours):
```js
function beginDrag() {
  clearPeek(); pet.style.opacity = ""; pet.className = "";
  napping = false; readEl = null; roamPhase = "drag";
  sprite.style.cursor = "grabbing"; setBoopable(true);
}
function endDrag(vx, vy) {
  sprite.style.cursor = ""; markActivity();
  if (petMode() === "float" && !reduced) {
    flingVX = Math.max(-42, Math.min(42, vx));
    flingVY = Math.max(-42, Math.min(42, vy));
    if (Math.abs(flingVX) + Math.abs(flingVY) > 6) say(pick(QUIPS.fling), "good", true);
    roamPhase = "fling";
  } else if (petMode() === "float") {
    enterDrift(Date.now());
  } else {
    lastMove = Date.now();
  }
  schedule();
}
function flingStep(now) {
  x += flingVX; y += flingVY;
  flingVX *= 0.90; flingVY *= 0.90;
  if (x < MARGIN) { x = MARGIN; flingVX = -flingVX * 0.5; }
  if (x > maxX()) { x = maxX(); flingVX = -flingVX * 0.5; }
  if (y < TOP_CLAMP) { y = TOP_CLAMP; flingVY = -flingVY * 0.5; }
  if (y > maxY()) { y = maxY(); flingVY = -flingVY * 0.5; }
  lean += (flingVX * 1.2 - lean) * 0.2;
  if (lean > 16) lean = 16;
  if (lean < -16) lean = -16;
  renderAt(x, y);
  if (Math.abs(flingVX) + Math.abs(flingVY) < 1.2) { lean = 0; enterDrift(now); }
}
```

- [ ] **Step 3: Add pointer handlers (drag-or-boop)**

Add (verbatim from `SCRATCH/pet-demo.js` lines 358–395):
```js
sprite.addEventListener("pointerdown", function (e) {
  if (e.button != null && e.button !== 0) return;
  markActivity();
  drag = { sx: e.clientX, sy: e.clientY, moved: false,
           gx: e.clientX - x, gy: e.clientY - y,
           lx: e.clientX, ly: e.clientY,
           lt: (window.performance ? performance.now() : Date.now()), vx: 0, vy: 0 };
  try { sprite.setPointerCapture(e.pointerId); } catch (err) {}
});
window.addEventListener("pointermove", function (e) {
  if (!drag) return;
  var dx = e.clientX - drag.sx, dy = e.clientY - drag.sy;
  if (!drag.moved && (dx * dx + dy * dy) > 25) { drag.moved = true; beginDrag(); }
  if (!drag.moved) return;
  x = clampX(e.clientX - drag.gx);
  y = clampY(e.clientY - drag.gy);
  var t = (window.performance ? performance.now() : Date.now());
  var dt = Math.max(1, t - drag.lt);
  drag.vx = (e.clientX - drag.lx) / dt * 16;
  drag.vy = (e.clientY - drag.ly) / dt * 16;
  drag.lx = e.clientX; drag.ly = e.clientY; drag.lt = t;
  lean = Math.max(-16, Math.min(16, drag.vx * 0.5));
  renderAt(x, y);
  schedule();
});
function endPointer(e) {
  if (!drag) return;
  var moved = drag.moved, vx = drag.vx, vy = drag.vy;
  try { sprite.releasePointerCapture(e.pointerId); } catch (err) {}
  drag = null;
  if (moved) endDrag(vx, vy); else boop();
}
window.addEventListener("pointerup", endPointer);
window.addEventListener("pointercancel", endPointer);
```

- [ ] **Step 4: Wire the new phases into the loop**

In `stepRoam()`'s `switch (roamPhase)`, add two cases:
```js
    case "fling":  flingStep(now);  break;
    case "drag":   /* positioned by pointermove */ break;
```
In `tick()`, right after `var now = Date.now();`, add the drag guard:
```js
if (drag && drag.moved) { schedule(); return; }
```

- [ ] **Step 5: CSS — grab cursor + touch**

In `site-assets/site.css`, in the `.pet-sprite` rule, change `cursor: pointer;` to `cursor: grab;` and add `touch-action: none;`. Add:
```css
.pet-sprite:active { cursor: grabbing; }
```

- [ ] **Step 6: Verify (live)**

`python tools/build.py`. In the preview (Roam mode): click the ghost without moving → it still recolors (boop). Press and drag → it follows the pointer; release with a flick → it sails and bounces off the edges, then resumes drifting. Switch to Cursor mode → drag drops it (no fling). Test a touch drag via device emulation.

- [ ] **Step 7: Commit**

```bash
git add site-assets/pet.js site-assets/site.css
git commit -m "Pet: drag and fling"
```

---

### Task 5: Pet panel markup + head keys (pages.py) — Python-tested

**Files:** Modify `tools/ssg/pages.py`; Test `tests/test_pages.py`.

**Interfaces:** Produces DOM the panel wiring (Task 6) binds to. Control IDs (stable contract):
`pet-panel` (container), `pet-mode` (segmented wrapper) with buttons `data-mode="float|cursor|off"`, `pet-size` (`<input type=range>`), `pet-opacity` (range), `pet-color` (swatch wrapper) with buttons `data-color="0..5"`, and toggle buttons `pet-q-nap`, `pet-q-flee`, `pet-q-read`, `pet-q-tricks`, `pet-q-speech`. A `pet-open` button replaces today's inline mode row.

- [ ] **Step 1: Failing tests**

In `tests/test_pages.py`, extend the pet section:
```python
def test_pet_panel_renders_when_enabled(self):
    on = pages.render_page(config=SiteConfig(pet_enabled=True), output_path="x.html",
                           page_title="X", content_html="", nav_html="")
    for needle in ['id="pet-panel"', 'id="pet-open"', 'id="pet-size"', 'id="pet-opacity"',
                   'id="pet-color"', 'data-mode="float"', 'id="pet-q-nap"', 'id="pet-q-speech"']:
        self.assertIn(needle, on)

def test_pet_panel_absent_when_disabled(self):
    off = pages.render_page(config=SiteConfig(), output_path="x.html",
                            page_title="X", content_html="", nav_html="")
    self.assertNotIn('id="pet-panel"', off)
    self.assertNotIn('id="pet-open"', off)
```

- [ ] **Step 2: Run — expect FAIL.** `python -m unittest tests.test_pages -v`

- [ ] **Step 3: Booleans in the head script**

In `pages.py:26`, after the size/opacity additions from Task 1, append boolean pre-reads so the panel's initial toggle state matches without a flash (the engine also reads them, but the panel markup is static so app.js will sync on load — no attribute needed here). Add just the key names to the script by pre-touching them (keeps the Task-1 test's `twb-pet-size` present and documents the keys):

```js
["twb-pet-nap","twb-pet-flee","twb-pet-read","twb-pet-tricks","twb-pet-speech"].forEach(function(k){});
```

(That no-op `forEach` is intentional: it keeps all key names discoverable in the emitted HTML for tests/tooling without changing runtime behavior. If you prefer, instead add a comment string — but the test in Step 1 does not require these keys, so this step is optional documentation. Skip if the reviewer objects to a no-op.)

- [ ] **Step 4: Replace the pet row with a "Pet" opener + panel**

In `pages.py:249-258`, the `pet_toggle` currently builds an inline mode-cycling row. Replace that block so it builds **two** pieces: the opener row (kept in `$pet_toggle`) and the panel (a new `$pet_panel` slot). Build:

```python
    pet_toggle = ""
    pet_panel = ""
    if config.pet_enabled:
        pet_toggle = ('<button id="pet-open" class="settings-row" aria-haspopup="true" '
                      'aria-expanded="false"><span class="settings-label">Pet</span>'
                      '<span class="settings-val"></span></button>')
        pet_panel = (
            '<div id="pet-panel" class="settings-menu pet-panel" hidden>'
            '<div class="settings-head">Pet</div>'
            '<div class="pet-group-label manifest-label">Appearance</div>'
            '<div id="pet-mode" class="pet-seg" role="group" aria-label="Pet mode">'
            '<button data-mode="float">Roam</button>'
            '<button data-mode="cursor">Cursor</button>'
            '<button data-mode="off">Off</button></div>'
            '<label class="pet-slider"><span>Size</span>'
            '<input id="pet-size" type="range" min="16" max="64" step="2"></label>'
            '<label class="pet-slider"><span>Opacity</span>'
            '<input id="pet-opacity" type="range" min="15" max="100" step="5"></label>'
            '<div id="pet-color" class="pet-swatches" role="group" aria-label="Pet color">'
            + "".join('<button data-color="%d" style="--sw:var(%s)"></button>' % (i, tok)
                      for i, tok in enumerate(
                          ["--twb-accent", "--twb-accent-alt", "--twb-warm",
                           "--twb-violet", "--twb-orange", "--twb-red"]))
            + '</div>'
            '<div class="pet-group-label manifest-label">Behavior</div>'
            + "".join(
                '<button id="pet-q-%s" class="settings-row pet-quirk">'
                '<span class="settings-label">%s</span><span class="settings-val"></span></button>'
                % (qid, label) for qid, label in [
                    ("nap", "Nap when idle"), ("flee", "Flee from cursor"),
                    ("read", "Read along"), ("tricks", "Do tricks"),
                    ("speech", "Speech bubbles")])
            + '</div>')
```

- [ ] **Step 5: Add the `$pet_panel` slot to the template + substitution**

In `_PAGE` (`pages.py:10`+), add `$pet_panel` immediately **after** the `settings-wrap` closing `</div>` (so the panel is a sibling popover anchored under the cog area). Find the `</header>` region and place `$pet_panel` just before `</header>`. In `render_page`'s `_PAGE.substitute(…)` call (around `pages.py:259-274`), add `pet_panel=pet_panel,` next to `pet_toggle=pet_toggle,`.

- [ ] **Step 6: Run tests — expect PASS.** `python -m unittest tests.test_pages -v`
Then `python tools/build.py` → 0 warnings. Grep the built page: `grep -c 'id="pet-panel"' public/index.html` → 1.

- [ ] **Step 7: Commit**

```bash
git add tools/ssg/pages.py tests/test_pages.py
git commit -m "Pet: settings 'Pet' opener and management panel markup"
```

---

### Task 6: Pet panel wiring (app.js) + styles (site.css)

**Files:** Modify `site-assets/app.js`, `site-assets/site.css`.

**Interfaces:** Consumes the Task-5 DOM IDs; writes `twb-pet*` keys and dispatches `twb:pet`; toggles `data-pet` for mode (mirroring the existing pet toggle logic).

- [ ] **Step 1: Panel open/close + control wiring in app.js**

In `site-assets/app.js`, after the existing settings/pet-toggle block, add a self-contained wiring block (ES5, matching the file's style). It: opens `#pet-panel` from `#pet-open` (and closes on outside-click / Esc, like the settings menu), reflects current state into the controls on open, and on each control change writes the key and dispatches `twb:pet`.

```js
(function () {
  var open = document.getElementById("pet-open");
  var panel = document.getElementById("pet-panel");
  if (!open || !panel) return;
  var root = document.documentElement;

  function getMode() {
    var a = root.getAttribute("data-pet");
    return a === "off" || a === "float" ? a : "cursor";
  }
  function setMode(m) {
    if (m === "cursor") root.removeAttribute("data-pet");
    else root.setAttribute("data-pet", m);
    try { if (m === "float") localStorage.removeItem("twb-pet"); else localStorage.setItem("twb-pet", m); } catch (e) {}
    sync(); fire();
  }
  function num(k, dflt) { var v = parseInt(localStorage.getItem(k), 10); return isNaN(v) ? dflt : v; }
  function onq(k, dflt) { var v = localStorage.getItem(k); return v === "on" ? true : v === "off" ? false : dflt; }
  function setKey(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }

  function sync() {
    var m = getMode();
    var segs = panel.querySelectorAll("#pet-mode button");
    for (var i = 0; i < segs.length; i++) segs[i].classList.toggle("on", segs[i].getAttribute("data-mode") === m);
    panel.querySelector("#pet-size").value = num("twb-pet-size", 28);
    panel.querySelector("#pet-opacity").value = num("twb-pet-opacity", 70);
    var col = num("twb-pet-color", 0);
    var sw = panel.querySelectorAll("#pet-color button");
    for (var j = 0; j < sw.length; j++) sw[j].classList.toggle("on", (+sw[j].getAttribute("data-color")) === col);
    var q = [["nap",true],["flee",true],["read",true],["tricks",true],["speech",false]];
    for (var n = 0; n < q.length; n++) {
      var b = panel.querySelector("#pet-q-" + q[n][0]);
      if (b) b.classList.toggle("on", onq("twb-pet-" + q[n][0], q[n][1]));
    }
  }
  function fire() { window.dispatchEvent(new Event("twb:pet")); }

  open.addEventListener("click", function (e) {
    e.stopPropagation();
    var show = panel.hasAttribute("hidden");
    if (show) { sync(); panel.removeAttribute("hidden"); } else panel.setAttribute("hidden", "");
    open.setAttribute("aria-expanded", show ? "true" : "false");
  });
  document.addEventListener("click", function (e) {
    if (!panel.hasAttribute("hidden") && !panel.contains(e.target) && e.target !== open) {
      panel.setAttribute("hidden", ""); open.setAttribute("aria-expanded", "false");
    }
  });
  document.addEventListener("keydown", function (e) {
    if (e.key === "Escape" && !panel.hasAttribute("hidden")) {
      panel.setAttribute("hidden", ""); open.setAttribute("aria-expanded", "false"); open.focus();
    }
  });

  panel.querySelector("#pet-mode").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-mode]"); if (b) setMode(b.getAttribute("data-mode"));
  });
  panel.querySelector("#pet-size").addEventListener("input", function () { setKey("twb-pet-size", this.value); fire(); });
  panel.querySelector("#pet-opacity").addEventListener("input", function () { setKey("twb-pet-opacity", this.value); fire(); });
  panel.querySelector("#pet-color").addEventListener("click", function (e) {
    var b = e.target.closest("button[data-color]"); if (!b) return;
    var c = b.getAttribute("data-color");
    try { if (c === "0") localStorage.removeItem("twb-pet-color"); else localStorage.setItem("twb-pet-color", c); } catch (er) {}
    sync(); fire();
  });
  var quirks = ["nap", "flee", "read", "tricks", "speech"];
  for (var i = 0; i < quirks.length; i++) (function (id) {
    var b = panel.querySelector("#pet-q-" + id);
    if (!b) return;
    b.addEventListener("click", function () {
      var cur = onq("twb-pet-" + id, id === "speech" ? false : true);
      setKey("twb-pet-" + id, cur ? "off" : "on");
      sync(); fire();
    });
  })(quirks[i]);
})();
```

Note: the pet engine reads `twb-pet-color` as an int and recolors on boop already; the swatch writes the same key, and `readCfg()`→`twb:pet` path plus the engine's existing color read applies it. Confirm the engine applies color on `twb:pet` (Task 1's `readCfg` should call the existing `applyPetColor()` after setting `petColor` from storage — if it doesn't, add `petColor = num; applyPetColor();` into `readCfg`).

- [ ] **Step 2: Panel + control styles**

In `site-assets/site.css`, add (reusing existing `.settings-menu` popover styling; only the pet-specific bits are new):

```css
.pet-panel { right: 8px; }                 /* anchor near the cog, like #settings-menu */
.pet-group-label { display:block; padding: 2px 12px; margin-top: 6px; font-size: 10px; color: var(--twb-text-faint); }
.pet-seg { display:flex; margin: 4px 10px 8px; border:1px solid var(--twb-border); border-radius:6px; overflow:hidden; }
.pet-seg button { flex:1; background:none; border:none; color:var(--twb-text-soft); font: inherit; font-size:12px; padding:5px 0; cursor:pointer; }
.pet-seg button.on { background: color-mix(in srgb, var(--twb-accent) 18%, transparent); color: var(--twb-accent); }
.pet-slider { display:flex; align-items:center; justify-content:space-between; gap:10px; padding: 4px 12px; font-size:12px; color: var(--twb-text-soft); }
.pet-slider input[type="range"] { flex:1; accent-color: var(--twb-accent); }
.pet-swatches { display:flex; gap:8px; padding: 6px 12px 8px; }
.pet-swatches button { width:16px; height:16px; border-radius:50%; border:1px solid var(--twb-border); background: var(--sw); cursor:pointer; padding:0; }
.pet-swatches button.on { outline:2px solid var(--twb-accent); outline-offset:2px; }
.pet-quirk .settings-val::after { content: "Off"; }
.pet-quirk.on .settings-val::after { content: "On"; }
.pet-quirk.on .settings-val { color: var(--twb-accent); }
```

(If the existing `#settings-menu` uses a specific absolute-position/right offset, mirror it for `.pet-panel` so both anchor consistently under the cog. Verify against the current `.settings-menu` rule.)

- [ ] **Step 3: Verify (live, end-to-end)**

`python tools/build.py`. In the preview: open the cog → click **Pet** → panel opens with two groups. Drag the **Size** slider → ghost resizes live (no teleport). **Opacity** slider → fades. Click a **color** swatch → ghost recolors. Toggle **Speech bubbles** on → boop shows a bubble. Toggle **Flee** off → cursor proximity no longer spooks. Switch **Mode** to Cursor/Off → behaves correctly. Reload → all choices persist. Press **Esc** / click outside → panel closes.

- [ ] **Step 4: Commit**

```bash
git add site-assets/app.js site-assets/site.css
git commit -m "Pet: wire the management panel controls"
```

---

### Task 7: README + full QA pass

**Files:** Modify `README.md`.

- [ ] **Step 1: Document the panel**

In `README.md`, in the section describing the pet (search for "pet"), add a short paragraph: the ghost has a management panel under the settings cog's **Pet** row — mode, size, opacity, color, and per-quirk toggles (nap, flee, read-along, tricks, speech). Mention drag-to-move / fling. Keep the professional, emoji-free tone.

- [ ] **Step 2: Full suite + build**

Run: `python -m unittest discover -s tests -t .` → all pass.
Run: `python tools/build.py` → 0 warnings.

- [ ] **Step 3: Reduced-motion + mobile check (live)**

In the preview, emulate `prefers-reduced-motion: reduce` → ghost holds still; dragging still repositions but no fling momentum; no speech unless forced (boop). Emulate a mobile viewport → panel usable, touch-drag works (`touch-action: none`).

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "Pet: document the management panel and drag/fling"
```

---

## Self-Review

**Spec coverage:**
- Drag & fling → Task 4. Speech bubbles → Task 3. Size & opacity → Task 1. Per-quirk toggles → Task 2 (+ speech gate in Task 3). Panel (anchored popover, two groups, from settings "Pet" row) → Tasks 5–6. `twb-pet-*` keys read pre-paint → Task 1 (size/opacity) + engine `readCfg` (booleans). `pet_enabled` gating → Task 5. Reduced-motion → Tasks 3/4/7. Defaults (quirks on, speech off) → Tasks 1–2 readers + panel `sync()`. Python tests for gated markup → Tasks 1 & 5. JS verified live → every JS task. React-to-writing excluded → not ported (noted in constraints). ✅ all covered.

**Placeholder scan:** No TBD/TODO. Every code step shows real code; verbatim-from-reference blocks cite exact `SCRATCH/pet-demo.js` line ranges and are reproduced inline. The one optional no-op in Task 5 Step 3 is explicitly marked optional. ✅

**Type/name consistency:** `readCfg`, `applySize`, `applyOpacity`, `cfgNap/cfgFlee/cfgRead/cfgTricks/cfgSpeech`, `say`, `QUIPS`, `pick`, `boop`, `beginDrag/endDrag/flingStep`, `drag/flingVX/flingVY`, `roamPhase "drag"/"fling"` — used consistently. Panel IDs (`pet-open`, `pet-panel`, `pet-mode`, `pet-size`, `pet-opacity`, `pet-color`, `pet-q-*`) match between Task 5 (markup) and Task 6 (wiring). localStorage keys (`twb-pet-size/opacity/nap/flee/read/tricks/speech`) consistent across pages.py, pet.js, app.js. ✅

**Note for executor:** `pet.js` is not covered by the Python unit suite (consistent with the current pet). JS tasks (2, 3, 4, 6) use live preview verification with concrete expected observations instead of a failing-test-first cycle; this is intentional and matches how the existing pet was built. Confirm each JS task's observation before marking complete.
