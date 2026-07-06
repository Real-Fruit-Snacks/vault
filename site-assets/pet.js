(function () {
  "use strict";
  var root = document.documentElement;
  var pet = document.getElementById("site-pet");
  if (!pet) return;
  function petOn() { return root.getAttribute("data-pet") !== "off"; }
  function petMode() {
    var a = root.getAttribute("data-pet");
    return a === "off" ? "off" : (a === "float" ? "float" : "cursor");
  }
  var tilt = pet.querySelector(".pet-tilt");
  var sprite = pet.querySelector(".pet-sprite");
  var reduced = window.matchMedia &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  var SIZE = 28, MARGIN = 8, TOP_CLAMP = 88;
  var TRAIL = 44;          // resting distance behind the cursor
  var EASE = 0.06;         // lerp factor per frame
  var FLOAT_EASE = 0.045;  // gentler drift while roaming
  var NAP_AFTER = 45000;   // ms of stillness before napping

  var x = window.innerWidth - SIZE - 16;
  var y = window.innerHeight - SIZE - 16;
  var mx = null, my = null;
  var lastMove = Date.now();
  var lastZ = 0;
  var napping = false;
  var petting = false;
  var lean = 0;
  var raf = null;
  // Float mode: the element currently being perched on, a stable horizontal
  // offset along it, and the timestamp until which the pet rests there.
  var perch = null, perchAt = 0.5, perchUntil = 0;
  // Body color: an index into the six-token theme palette (0 = accent, the
  // default). Petting the ghost advances it; the choice is remembered.
  var COLOR_COUNT = 6;
  var petColor = 0;
  try { petColor = parseInt(localStorage.getItem("twb-pet-color"), 10) || 0; }
  catch (e) { /* private mode */ }
  if (!(petColor >= 1 && petColor < COLOR_COUNT)) petColor = 0;
  function applyPetColor() {
    if (petColor) pet.setAttribute("data-color", petColor);
    else pet.removeAttribute("data-color");
  }
  function cyclePetColor() {
    petColor = (petColor + 1) % COLOR_COUNT;
    applyPetColor();
    try {
      if (petColor) localStorage.setItem("twb-pet-color", String(petColor));
      else localStorage.removeItem("twb-pet-color");
    } catch (e) { /* private mode */ }
  }

  function clamp() {
    var maxX = window.innerWidth - SIZE - MARGIN;
    var maxY = window.innerHeight - SIZE - MARGIN;
    if (x < MARGIN) x = MARGIN;
    if (y < TOP_CLAMP) y = TOP_CLAMP;
    if (x > maxX) x = maxX;
    if (y > maxY) y = maxY;
  }
  function apply() {
    pet.style.transform = "translate(" + x.toFixed(1) + "px," + y.toFixed(1) + "px)";
    tilt.style.transform = "rotate(" + lean.toFixed(1) + "deg)";
  }

  function spawnParticle(ch, cls) {
    var s = document.createElement("span");
    s.className = "pet-particle " + cls;
    s.textContent = ch;
    pet.appendChild(s);
    setTimeout(function () {
      if (s.parentNode) s.parentNode.removeChild(s);
    }, 1400);
  }

  function setNap(on) {
    if (napping === on) return;
    napping = on;
    if (on) pet.className = "pet-nap";
    else pet.className = "";
  }

  function scheduleBlink() {
    setTimeout(function () {
      if (!napping && !petting) {
        sprite.className = "pet-sprite pet-blink";
        setTimeout(function () {
          if (!petting) sprite.className = "pet-sprite";
        }, 160);
      }
      scheduleBlink();
    }, 4000 + Math.random() * 3000);
  }

  document.addEventListener("mousemove", function (e) {
    mx = e.clientX;
    my = e.clientY;
    lastMove = Date.now();
    if (napping) setNap(false);
    schedule();
  });

  sprite.addEventListener("click", function () {
    cyclePetColor();       // every pet nudges the ghost to the next color
    if (petting) return;   // but the happy bounce only plays one at a time
    petting = true;
    setNap(false);
    lastMove = Date.now();
    sprite.className = "pet-sprite pet-happy";
    spawnParticle("♥", "pet-heart");
    setTimeout(function () {
      sprite.className = "pet-sprite";
      petting = false;
    }, 1500);
  });

  // --- float mode: roam the page and perch on the note's text blocks ---
  function perchCandidates() {
    var note = document.querySelector("article.note");
    if (!note) return [];
    var els = note.querySelectorAll("h1,h2,h3,h4,h5,h6,p,li,blockquote");
    var out = [];
    for (var i = 0; i < els.length; i++) {
      var r = els[i].getBoundingClientRect();
      // Wide enough to sit on and currently within the visible band.
      if (r.width > SIZE && r.height > 0 &&
          r.bottom > TOP_CLAMP + 8 && r.top < window.innerHeight - MARGIN) {
        out.push(els[i]);
      }
    }
    return out;
  }
  function pickPerch() {
    var pool = perchCandidates();
    perch = pool.length ? pool[Math.floor(Math.random() * pool.length)] : null;
    perchAt = 0.15 + Math.random() * 0.7;  // where along the block to land
    perchUntil = 0;
  }
  function floatTarget() {
    if (!perch || !document.contains(perch)) pickPerch();
    var maxX = window.innerWidth - SIZE - MARGIN;
    var maxY = window.innerHeight - SIZE - MARGIN;
    var idle = { x: Math.min(maxX, window.innerWidth - SIZE - 40), y: maxY - 20 };
    if (!perch) return idle;  // no note to land on — drift to a resting corner
    var r = perch.getBoundingClientRect();
    if (r.bottom < TOP_CLAMP || r.top > window.innerHeight) {  // scrolled away
      pickPerch();
      if (!perch) return idle;
      r = perch.getBoundingClientRect();
    }
    // Sit on top of the text line, like perching on a shelf.
    var tx = r.left + perchAt * (r.width - SIZE);
    var ty = r.top - SIZE + 2;
    tx = Math.max(MARGIN, Math.min(maxX, tx));
    ty = Math.max(TOP_CLAMP, Math.min(maxY, ty));
    return { x: tx, y: ty };
  }
  function stepFloat(now) {
    if (napping) setNap(false);  // roaming never naps
    var t = floatTarget();
    var vx = (t.x - x) * FLOAT_EASE, vy = (t.y - y) * FLOAT_EASE;
    x += vx;
    y += vy;
    lean += (vx * 1.6 - lean) * 0.1;
    if (lean > 10) lean = 10;
    if (lean < -10) lean = -10;
    clamp();
    apply();
    // Landed: rest a beat, then choose the next block to visit.
    if (Math.abs(t.x - x) < 2 && Math.abs(t.y - y) < 2) {
      if (!perchUntil) perchUntil = now + 2600 + Math.random() * 2600;
      else if (now > perchUntil) pickPerch();
    }
  }

  function tick() {
    raf = null;
    var now = Date.now();
    if (petMode() === "float") {
      if (!reduced) stepFloat(now);
      schedule();
      return;
    }
    if (!napping && now - lastMove > NAP_AFTER) setNap(true);
    if (napping && now - lastZ > 3000) {
      lastZ = now;
      spawnParticle("z", "pet-z");
    }
    if (!reduced && !napping && mx !== null) {
      // Ease toward a point TRAIL px behind the cursor, along the line
      // from the cursor to the pet, so it follows without covering it.
      var cx = x + SIZE / 2, cy = y + SIZE / 2;
      var dx = cx - mx, dy = cy - my;
      var d = Math.sqrt(dx * dx + dy * dy) || 1;
      var txp = mx + (dx / d) * TRAIL - SIZE / 2;
      var typ = my + (dy / d) * TRAIL - SIZE / 2;
      var vx = (txp - x) * EASE, vy = (typ - y) * EASE;
      if (Math.abs(vx) > 0.05 || Math.abs(vy) > 0.05) {
        x += vx;
        y += vy;
      }
      lean += (vx * 1.6 - lean) * 0.1;
      if (lean > 10) lean = 10;
      if (lean < -10) lean = -10;
      clamp();
      apply();
    }
    schedule();
  }
  function schedule() {
    if (!document.hidden && petOn() && raf === null) {
      raf = window.requestAnimationFrame(tick);
    }
  }

  document.addEventListener("visibilitychange", function () {
    if (!document.hidden) {
      lastMove = Date.now();
      schedule();
    }
  });
  // The top-bar toggle flips data-pet; re-arm the loop for the new mode.
  window.addEventListener("twb:pet", function () {
    if (!petOn()) return;  // hidden: schedule() parks itself
    setNap(false);
    if (petMode() === "float") pickPerch();
    else lastMove = Date.now();
    schedule();
  });
  window.addEventListener("resize", function () {
    clamp();
    apply();
  });

  clamp();
  apply();
  applyPetColor();
  scheduleBlink();
  if (petMode() === "float") pickPerch();
  schedule();
})();
