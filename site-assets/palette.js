(function () {
  "use strict";
  var root = document.documentElement;
  var base = root.getAttribute("data-root") || "";
  var overlay = null, input = null, listEl = null, rows = [], sel = 0;

  function go(url) { location.href = base + url; }
  function press(id) { var b = document.getElementById(id); if (b) b.click(); }
  function notes() {
    return (window.TWB_SEARCH_INDEX || []).filter(function (e) { return e.type !== "tool"; });
  }
  function randomNote() {
    var n = notes();
    if (n.length) go(n[Math.floor(Math.random() * n.length)].url);
  }

  // Fixed commands always available in the palette.
  function commands() {
    return [
      { label: "Toggle theme", hint: "light / dark", run: function () { press("theme-toggle"); } },
      { label: "Pet settings", hint: "open panel", run: function () { press("pet-open"); } },
      { label: "Toggle folder colors", run: function () { press("nav-colors"); } },
      { label: "Toggle full-width notes", run: function () { press("width-toggle"); } },
      { label: "Toggle CRT mode", hint: "retro", run: function () { press("crt-toggle"); } },
      { label: "Toggle reading progress", run: function () { press("progress-toggle"); } },
      { label: "Cycle text size", hint: "S / M / L", run: function () { press("text-size"); } },
      { label: "Cycle accent color", run: function () { press("accent-color"); } },
      { label: "Random note", hint: "shuffle", run: randomNote },
      { label: "Go: Home", run: function () { go("index.html"); } },
      { label: "Go: Notes", run: function () { go("notes.html"); } },
      { label: "Go: Tags", run: function () { go("_tags/index.html"); } },
      { label: "Go: Graph", run: function () { go("graph.html"); } }
    ];
  }

  // Subsequence match with a light score (earlier / contiguous hits rank higher).
  function score(text, q) {
    text = text.toLowerCase();
    var ti = 0, qi = 0, s = 0, run = 0, first = -1;
    for (; ti < text.length && qi < q.length; ti++) {
      if (text.charAt(ti) === q.charAt(qi)) {
        if (first < 0) first = ti;
        run++; s += run; qi++;
      } else { run = 0; }
    }
    if (qi < q.length) return -1;
    return s - first * 0.1;
  }

  function candidates(q) {
    var pool = commands().map(function (c) { return { label: c.label, hint: c.hint || "", run: c.run, kind: "cmd" }; });
    notes().forEach(function (n) {
      pool.push({ label: n.title, hint: "note", run: (function (u) { return function () { go(u); }; })(n.url), kind: "note" });
    });
    if (!q) return pool.slice(0, 12);
    q = q.toLowerCase();
    var scored = [];
    pool.forEach(function (item) {
      var sc = score(item.label, q);
      if (sc >= 0) scored.push({ item: item, sc: sc });
    });
    scored.sort(function (a, b) { return b.sc - a.sc; });
    return scored.slice(0, 12).map(function (x) { return x.item; });
  }

  function render() {
    var q = input.value.trim();
    rows = candidates(q);
    sel = 0;
    listEl.innerHTML = "";
    rows.forEach(function (item, i) {
      var li = document.createElement("li");
      li.className = "cmdk-row" + (i === 0 ? " active" : "");
      li.setAttribute("role", "option");
      li.innerHTML = '<span class="cmdk-kind cmdk-kind-' + item.kind + '"></span>' +
        '<span class="cmdk-label"></span>' +
        (item.hint ? '<span class="cmdk-hint"></span>' : "");
      li.querySelector(".cmdk-label").textContent = item.label;
      if (item.hint) li.querySelector(".cmdk-hint").textContent = item.hint;
      li.addEventListener("mousemove", function () { move(i); });
      li.addEventListener("click", function () { runAt(i); });
      listEl.appendChild(li);
    });
    if (!rows.length) {
      var empty = document.createElement("li");
      empty.className = "cmdk-empty";
      empty.textContent = "No commands or notes match";
      listEl.appendChild(empty);
    }
  }

  function move(i) {
    var kids = listEl.querySelectorAll(".cmdk-row");
    if (!kids.length) return;
    sel = ((i % kids.length) + kids.length) % kids.length;
    Array.prototype.forEach.call(kids, function (el, n) {
      el.classList.toggle("active", n === sel);
      if (n === sel && el.scrollIntoView) el.scrollIntoView({ block: "nearest" });
    });
  }
  function runAt(i) {
    if (i >= 0 && i < rows.length) { var r = rows[i]; close(); r.run(); }
  }

  function open() {
    if (overlay) return;
    overlay = document.createElement("div");
    overlay.id = "cmdk";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    var box = document.createElement("div");
    box.className = "cmdk-box";
    input = document.createElement("input");
    input.className = "cmdk-input";
    input.type = "text";
    input.setAttribute("placeholder", "Type a command or note…");
    input.setAttribute("aria-label", "Command palette");
    listEl = document.createElement("ul");
    listEl.className = "cmdk-list";
    listEl.setAttribute("role", "listbox");
    box.appendChild(input);
    box.appendChild(listEl);
    overlay.appendChild(box);
    document.body.appendChild(overlay);
    overlay.addEventListener("mousedown", function (e) { if (e.target === overlay) close(); });
    input.addEventListener("input", render);
    input.addEventListener("keydown", onKey);
    render();
    input.focus();
  }
  function close() {
    if (!overlay) return;
    if (overlay.parentNode) overlay.parentNode.removeChild(overlay);
    overlay = input = listEl = null; rows = []; sel = 0;
  }
  function onKey(e) {
    if (e.key === "ArrowDown") { e.preventDefault(); move(sel + 1); }
    else if (e.key === "ArrowUp") { e.preventDefault(); move(sel - 1); }
    else if (e.key === "Enter") { e.preventDefault(); runAt(sel); }
    else if (e.key === "Escape") { e.preventDefault(); close(); }
  }

  document.addEventListener("keydown", function (e) {
    if ((e.ctrlKey || e.metaKey) && (e.key === "k" || e.key === "K")) {
      e.preventDefault(); overlay ? close() : open(); return;
    }
    if (e.key === "`" || e.key === "~") {
      var t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
                t.tagName === "SELECT" || t.isContentEditable)) return;
      e.preventDefault(); overlay ? close() : open();
    }
  });
  var btn = document.getElementById("cmd-toggle");
  if (btn) btn.addEventListener("click", function () { overlay ? close() : open(); });
})();
