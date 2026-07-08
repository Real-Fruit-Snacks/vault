(function () {
  "use strict";
  var root = document.documentElement;

  var themeToggle = document.getElementById("theme-toggle");
  if (themeToggle) {
    themeToggle.addEventListener("click", function () {
      var prefersLight = window.matchMedia("(prefers-color-scheme: light)").matches;
      var effective = root.getAttribute("data-theme") || (prefersLight ? "light" : "dark");
      var next = effective === "light" ? "dark" : "light";
      root.setAttribute("data-theme", next);
      try { localStorage.setItem("twb-theme", next); } catch (e) { /* private mode */ }
    });
  }

  var navToggle = document.querySelector(".nav-toggle");
  var sidebar = document.getElementById("sidebar");
  if (navToggle && sidebar) {
    navToggle.addEventListener("click", function () {
      if (window.matchMedia("(max-width: 800px)").matches) {
        sidebar.classList.toggle("open");
        return;
      }
      var collapsed = root.getAttribute("data-sidebar") === "collapsed";
      if (collapsed) {
        root.removeAttribute("data-sidebar");
      } else {
        root.setAttribute("data-sidebar", "collapsed");
      }
      try {
        if (collapsed) localStorage.removeItem("twb-sidebar");
        else localStorage.setItem("twb-sidebar", "collapsed");
      } catch (e) { /* private mode */ }
    });
  }

  var railToggle = document.getElementById("rail-toggle");
  if (railToggle) {
    railToggle.addEventListener("click", function () {
      var collapsed = root.getAttribute("data-rail") === "collapsed";
      if (collapsed) {
        root.removeAttribute("data-rail");
        // Canvases in the rail were zero-sized while hidden; re-measure.
        window.dispatchEvent(new Event("resize"));
      } else {
        root.setAttribute("data-rail", "collapsed");
      }
      try {
        // Collapsed is the built-in default, so both states are stored
        // explicitly; an absent key means "use the default".
        localStorage.setItem("twb-rail", collapsed ? "expanded" : "collapsed");
      } catch (e) { /* private mode */ }
    });
  }

  function setAllFolders(open) {
    if (!sidebar) return;
    Array.prototype.forEach.call(sidebar.querySelectorAll("details"), function (d) {
      d.open = open;
    });
  }
  var expandAll = document.getElementById("nav-expand-all");
  var collapseAll = document.getElementById("nav-collapse-all");
  if (expandAll) expandAll.addEventListener("click", function () { setAllFolders(true); });
  if (collapseAll) collapseAll.addEventListener("click", function () { setAllFolders(false); });

  var widthToggle = document.getElementById("width-toggle");
  if (widthToggle) {
    widthToggle.addEventListener("click", function () {
      var full = root.getAttribute("data-width") === "full";
      if (full) root.removeAttribute("data-width");
      else root.setAttribute("data-width", "full");
      // Re-fit anything that measures its container (canvas pages).
      window.dispatchEvent(new Event("resize"));
      try {
        if (full) localStorage.removeItem("twb-width");
        else localStorage.setItem("twb-width", "full");
      } catch (e) { /* private mode */ }
    });
  }

  // Pet management panel: opens from the cog's "Pet" opener, reflects stored
  // state into its controls, and on each change writes the localStorage key +
  // dispatches "twb:pet" so pet.js re-reads config live.
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
      var q = [["nap", true], ["flee", true], ["read", true], ["tricks", true], ["speech", false]];
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

  var navColors = document.getElementById("nav-colors");
  if (navColors) {
    // The head script already applied the stored state before paint.
    if (root.getAttribute("data-nav-colors") === "on") {
      navColors.classList.add("active");
    }
    navColors.addEventListener("click", function () {
      var on = root.getAttribute("data-nav-colors") === "on";
      if (on) root.removeAttribute("data-nav-colors");
      else root.setAttribute("data-nav-colors", "on");
      navColors.classList.toggle("active", !on);
      try {
        if (on) localStorage.removeItem("twb-nav-colors");
        else localStorage.setItem("twb-nav-colors", "on");
      } catch (e) { /* private mode */ }
    });
  }

  var crtToggle = document.getElementById("crt-toggle");
  if (crtToggle) {
    if (root.getAttribute("data-crt") === "on") crtToggle.classList.add("active");
    crtToggle.addEventListener("click", function () {
      var on = root.getAttribute("data-crt") === "on";
      if (on) root.removeAttribute("data-crt");
      else root.setAttribute("data-crt", "on");
      crtToggle.classList.toggle("active", !on);
      try {
        if (on) localStorage.removeItem("twb-crt");
        else localStorage.setItem("twb-crt", "on");
      } catch (e) { /* private mode */ }
    });
  }

  var textSize = document.getElementById("text-size");
  if (textSize) {
    var SIZES = ["m", "l", "s"];  // cycle order from the default medium
    textSize.addEventListener("click", function () {
      var cur = root.getAttribute("data-textsize") || "m";
      var next = SIZES[(SIZES.indexOf(cur) + 1) % SIZES.length];
      if (next === "m") root.removeAttribute("data-textsize");
      else root.setAttribute("data-textsize", next);
      try {
        if (next === "m") localStorage.removeItem("twb-textsize");
        else localStorage.setItem("twb-textsize", next);
      } catch (e) { /* private mode */ }
    });
  }

  var accentColor = document.getElementById("accent-color");
  if (accentColor) {
    accentColor.addEventListener("click", function () {
      var cur = parseInt(root.getAttribute("data-accent"), 10) || 0;
      var next = (cur + 1) % 6;  // 0 = default accent, 1-5 = palette
      if (next === 0) root.removeAttribute("data-accent");
      else root.setAttribute("data-accent", String(next));
      try {
        if (next === 0) localStorage.removeItem("twb-accent");
        else localStorage.setItem("twb-accent", String(next));
      } catch (e) { /* private mode */ }
    });
  }

  var progressToggle = document.getElementById("progress-toggle");
  if (progressToggle) {
    progressToggle.addEventListener("click", function () {
      var on = root.getAttribute("data-progress") === "on";
      if (on) root.removeAttribute("data-progress");
      else root.setAttribute("data-progress", "on");
      try {
        if (on) localStorage.removeItem("twb-progress");
        else localStorage.setItem("twb-progress", "on");
      } catch (e) { /* private mode */ }
    });
  }

  var randomBtn = document.getElementById("random-note");
  if (randomBtn) {
    randomBtn.addEventListener("click", function () {
      var idx = window.TWB_SEARCH_INDEX || [];
      var pool = idx.filter(function (e) { return e.type !== "tool"; });
      if (!pool.length) return;
      var base = root.getAttribute("data-root") || "";
      location.href = base + pool[Math.floor(Math.random() * pool.length)].url;
    });
  }

  var settingsToggle = document.getElementById("settings-toggle");
  var settingsMenu = document.getElementById("settings-menu");
  if (settingsToggle && settingsMenu) {
    var closeSettings = function () {
      settingsMenu.hidden = true;
      settingsToggle.setAttribute("aria-expanded", "false");
    };
    settingsToggle.addEventListener("click", function (e) {
      e.stopPropagation();
      var open = !settingsMenu.hidden;
      settingsMenu.hidden = open;
      settingsToggle.setAttribute("aria-expanded", open ? "false" : "true");
    });
    // Adjusting a setting shouldn't dismiss the menu; keep it open.
    settingsMenu.addEventListener("click", function (e) { e.stopPropagation(); });
    document.addEventListener("click", function () {
      if (!settingsMenu.hidden) closeSettings();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape" && !settingsMenu.hidden) closeSettings();
    });
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  var input = document.getElementById("search-input");
  var results = document.getElementById("search-results");
  var mini = null;

  function ensureIndex() {
    if (mini || !window.TWB_SEARCH_INDEX || !window.MiniSearch) return;
    mini = new MiniSearch({
      fields: ["title", "headings", "text"],
      storeFields: ["title", "url", "hs", "type"],
      searchOptions: { boost: { title: 3, headings: 2 }, prefix: true, fuzzy: 0.15 }
    });
    mini.addAll(window.TWB_SEARCH_INDEX);
  }

  if (input && results) {
    var activeIndex = -1;
    function resultLinks() { return results.querySelectorAll("a"); }
    function setActiveResult(idx) {
      var links = resultLinks();
      if (!links.length) return;
      if (activeIndex >= 0 && activeIndex < links.length) {
        links[activeIndex].classList.remove("active");
      }
      activeIndex = ((idx % links.length) + links.length) % links.length;
      links[activeIndex].classList.add("active");
      if (links[activeIndex].scrollIntoView) {
        links[activeIndex].scrollIntoView({ block: "nearest" });
      }
    }
    input.addEventListener("input", function () {
      ensureIndex();
      var q = input.value.trim();
      if (!mini || !q) {
        results.hidden = true;
        results.innerHTML = "";
        return;
      }
      var hits = mini.search(q);
      var noteHits = [], toolHits = [];
      hits.forEach(function (h) {
        if (h.type === "tool") {
          if (toolHits.length < 5) toolHits.push(h);
        } else if (noteHits.length < 8) {
          noteHits.push(h);
        }
      });
      activeIndex = -1;
      var base = root.getAttribute("data-root") || "";
      var tokens = q.toLowerCase().split(/\s+/).filter(Boolean);
      tokens = tokens.filter(function (t, i) { return tokens.indexOf(t) === i; });
      function headingHit(h) {
        var title = (h.title || "").toLowerCase();
        for (var i = 0; i < tokens.length; i++) {
          if (title.indexOf(tokens[i]) !== -1) return null; // title match wins
        }
        var best = null, bestScore = 0;
        (h.hs || []).forEach(function (pair) {
          var text = pair[0].toLowerCase(), score = 0;
          tokens.forEach(function (t) { if (text.indexOf(t) !== -1) score++; });
          if (score > bestScore) { best = pair; bestScore = score; }
        });
        return best;
      }
      function renderHit(h) {
        var hit = headingHit(h);
        var href = base + encodeURI(h.url) + (hit ? "#" + encodeURIComponent(hit[1]) : "");
        var extra = hit ? '<span class="hit-context"># ' + escapeHtml(hit[0]) + "</span>" : "";
        return '<a href="' + href + '">' + escapeHtml(h.title) + extra + "</a>";
      }
      function section(label, list) {
        if (!list.length) return "";
        return '<div class="search-section">' + label + "</div>" + list.map(renderHit).join("");
      }
      if (noteHits.length + toolHits.length === 0) {
        results.innerHTML = '<div class="search-empty">No matches for &ldquo;' +
          escapeHtml(q) + '&rdquo;</div>';
      } else {
        results.innerHTML = section("Notes", noteHits) + section("Tools", toolHits);
      }
      results.hidden = false;
    });
    input.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        results.hidden = true;
        results.innerHTML = "";
        activeIndex = -1;
        input.blur();
        return;
      }
      if (results.hidden) return;
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setActiveResult(activeIndex + 1);
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setActiveResult(activeIndex < 0 ? -1 : activeIndex - 1);
      } else if (e.key === "Enter") {
        var links = resultLinks();
        if (!links.length) return;
        e.preventDefault();
        location.href = links[activeIndex >= 0 ? activeIndex : 0].href;
      }
    });
    document.addEventListener("keydown", function (e) {
      if (e.key !== "/") return;
      if (e.ctrlKey || e.metaKey || e.altKey) return;
      var t = e.target;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" ||
                t.tagName === "SELECT" || t.isContentEditable)) return;
      e.preventDefault();
      input.focus();
    });
    document.addEventListener("click", function (e) {
      if (!e.target.closest(".search")) results.hidden = true;
    });
  }

  function legacyCopy(text) {
    // Works on plain-http internal hosts where the Clipboard API is unavailable.
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        if (document.execCommand("copy")) { resolve(); } else { reject(new Error("copy failed")); }
      } catch (err) {
        reject(err);
      } finally {
        document.body.removeChild(ta);
      }
    });
  }

  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () {
        return legacyCopy(text);
      });
    }
    return legacyCopy(text);
  }

  document.querySelectorAll("figure.code-block").forEach(function (block) {
    var caption = block.querySelector(".code-lang");
    var code = block.querySelector("pre code");
    if (!caption || !code) return;
    var btn = document.createElement("button");
    btn.type = "button";
    btn.className = "copy-code";
    btn.textContent = "copy";
    btn.setAttribute("aria-label", "Copy code to clipboard");
    btn.addEventListener("click", function () {
      copyText(code.textContent).then(function () {
        btn.textContent = "copied";
        btn.classList.add("copied");
        setTimeout(function () {
          btn.textContent = "copy";
          btn.classList.remove("copied");
        }, 1600);
      }, function () {
        btn.textContent = "failed";
        setTimeout(function () { btn.textContent = "copy"; }, 1600);
      });
    });
    caption.appendChild(btn);
  });

  var lightboxReturn = null;
  function onLightboxKey(e) {
    if (e.key === "Escape") closeLightbox();
  }
  function closeLightbox() {
    var overlay = document.querySelector(".lightbox");
    if (!overlay) return;
    document.removeEventListener("keydown", onLightboxKey);
    overlay.remove();
    if (lightboxReturn && lightboxReturn.focus) lightboxReturn.focus();
    lightboxReturn = null;
  }
  function openLightbox(img) {
    lightboxReturn = document.activeElement;
    var overlay = document.createElement("div");
    overlay.className = "lightbox";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");
    var big = document.createElement("img");
    big.src = img.currentSrc || img.src;
    big.alt = img.alt;
    overlay.appendChild(big);
    if (img.alt) {
      var cap = document.createElement("div");
      cap.className = "lightbox-caption";
      cap.textContent = img.alt;
      overlay.appendChild(cap);
    }
    var close = document.createElement("button");
    close.type = "button";
    close.className = "lightbox-close";
    close.setAttribute("aria-label", "Close image");
    close.textContent = "×";
    overlay.appendChild(close);
    overlay.addEventListener("click", closeLightbox);
    document.addEventListener("keydown", onLightboxKey);
    document.body.appendChild(overlay);
    close.focus();
  }
  document.addEventListener("click", function (e) {
    if (!e.target || !e.target.closest) return;
    var img = e.target.closest("article.note img");
    if (img && !img.closest("a")) openLightbox(img);
  });

  var tocList = document.querySelector(".toc-list");
  if (tocList && window.IntersectionObserver) {
    var tocLinks = {};
    Array.prototype.forEach.call(tocList.querySelectorAll("a"), function (a) {
      var hash = a.getAttribute("href");
      if (hash && hash.charAt(0) === "#") tocLinks[hash.slice(1)] = a;
    });
    var spied = [];
    var noteBody = document.querySelector("article.note");
    if (noteBody) {
      Array.prototype.forEach.call(
        noteBody.querySelectorAll("h1[id], h2[id], h3[id], h4[id], h5[id], h6[id]"),
        function (h) { if (tocLinks[h.id]) spied.push(h); });
    }
    if (spied.length) {
      var currentSection = null;
      var markSection = function (id) {
        if (currentSection === id) return;
        if (currentSection && tocLinks[currentSection]) {
          tocLinks[currentSection].classList.remove("active");
        }
        currentSection = id;
        tocLinks[id].classList.add("active");
      };
      // The observer only supplies wake-ups as headings cross the band;
      // the active section is recomputed from geometry each time, so the
      // answer is deterministic regardless of event order.
      var spy = new IntersectionObserver(function () {
        var active = spied[0].id;
        for (var i = 0; i < spied.length; i++) {
          if (spied[i].getBoundingClientRect().top <= 100) active = spied[i].id;
          else break;
        }
        markSection(active);
      }, { rootMargin: "-100px 0px -60% 0px", threshold: [0, 1] });
      spied.forEach(function (h) { spy.observe(h); });
      markSection(spied[0].id);
    }
  }

  // Back-to-top button: appears once the page has scrolled a screenful.
  var toTop = document.createElement("button");
  toTop.id = "back-to-top";
  toTop.type = "button";
  toTop.setAttribute("aria-label", "Back to top");
  toTop.innerHTML = "<span></span>";
  document.body.appendChild(toTop);
  function syncToTop() { toTop.classList.toggle("show", window.pageYOffset > 600); }
  window.addEventListener("scroll", syncToTop, { passive: true });
  syncToTop();
  toTop.addEventListener("click", function () {
    window.scrollTo({ top: 0, behavior: "smooth" });
    var main = document.getElementById("main");
    if (main) { main.setAttribute("tabindex", "-1"); main.focus({ preventScroll: true }); }
  });

  // Click a heading's # anchor to copy its deep link (instead of just jumping).
  document.addEventListener("click", function (e) {
    var a = e.target.closest && e.target.closest("a.h-anchor");
    if (!a) return;
    e.preventDefault();
    var id = a.getAttribute("href").slice(1);
    if (window.history && history.replaceState) history.replaceState(null, "", "#" + id);
    else location.hash = id;
    var target = document.getElementById(id);
    if (target && target.scrollIntoView) target.scrollIntoView();
    copyText(location.href).then(function () {
      a.classList.add("copied");
      setTimeout(function () { a.classList.remove("copied"); }, 1200);
    }, function () { /* clipboard blocked */ });
  });

  // Reading progress: a thin bar that fills as the note scrolls.
  if (document.querySelector("article.note")) {
    var progress = document.createElement("div");
    progress.id = "read-progress";
    var fill = document.createElement("span");
    progress.appendChild(fill);
    document.body.appendChild(progress);
    function syncProgress() {
      var h = document.documentElement.scrollHeight - window.innerHeight;
      var frac = h > 0 ? Math.min(1, Math.max(0, window.pageYOffset / h)) : 0;
      fill.style.width = (frac * 100).toFixed(1) + "%";
    }
    window.addEventListener("scroll", syncProgress, { passive: true });
    window.addEventListener("resize", syncProgress);
    syncProgress();
  }

  // Mobile outline: the right rail is hidden on small screens, so clone its
  // table of contents into a collapsible panel above the note.
  var tocSource = document.querySelector(".toc .toc-list");
  var articleEl = document.querySelector("article.note");
  if (tocSource && articleEl && articleEl.parentNode) {
    var details = document.createElement("details");
    details.className = "toc-mobile";
    var summary = document.createElement("summary");
    summary.textContent = "On this page";
    details.appendChild(summary);
    var clone = tocSource.cloneNode(true);
    details.appendChild(clone);
    articleEl.parentNode.insertBefore(details, articleEl);
    clone.addEventListener("click", function (e) {
      if (e.target.closest("a")) details.open = false;
    });
  }
})();
