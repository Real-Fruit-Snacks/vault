(function () {
  "use strict";
  var root = document.documentElement;
  // The pre-paint head script sets data-boot once per tab session.
  // No flag: nothing to do.
  if (root.getAttribute("data-boot") !== "1") return;

  // The build emits the true note count; fall back to the search index
  // (which also includes canvases and bases) only if it is missing.
  var n = (typeof window.TWB_NOTE_COUNT === "number")
    ? window.TWB_NOTE_COUNT
    : (window.TWB_SEARCH_INDEX || []).filter(function (e) { return e.type !== "tool"; }).length;
  var lines = [
    "terminal-workbench :: boot",
    "mounting vault … ok",
    "indexing " + n + (n === 1 ? " note" : " notes") + " … ok",
    "loading search index … ok",
    "spawning ghost … ok",
    "ready."
  ];

  var overlay = document.createElement("div");
  overlay.id = "boot-screen";
  overlay.setAttribute("aria-hidden", "true");
  var pre = document.createElement("pre");
  pre.className = "boot-log";
  overlay.appendChild(pre);
  document.body.appendChild(overlay);

  var stopped = false;
  function finish() {
    if (stopped) return;
    stopped = true;
    root.removeAttribute("data-boot");
    overlay.classList.add("boot-done");
    setTimeout(function () {
      if (overlay && overlay.parentNode) overlay.parentNode.removeChild(overlay);
      overlay = null;
    }, 480);
    document.removeEventListener("keydown", skip, true);
  }
  function skip() { finish(); }

  var printed = "", li = 0, ch = 0;
  function tick() {
    if (stopped) return;
    var line = lines[li];
    ch++;
    pre.textContent = printed + line.slice(0, ch) + "█";
    if (ch >= line.length) {
      printed += line + "\n";
      li++; ch = 0;
      if (li >= lines.length) {
        pre.textContent = printed.replace(/\n$/, "");
        setTimeout(finish, 520);
        return;
      }
      setTimeout(tick, 210);
    } else {
      setTimeout(tick, 22 + Math.random() * 30);
    }
  }

  document.addEventListener("keydown", skip, true);
  overlay.addEventListener("click", skip);
  tick();
})();
