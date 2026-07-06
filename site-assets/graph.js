(function () {
  "use strict";
  var data = window.TWB_GRAPH;
  if (!data || !data.nodes) return;
  var root = document.documentElement;
  var base = root.getAttribute("data-root") || "";

  function palette() {
    var cs = getComputedStyle(root);
    function v(name) { return cs.getPropertyValue(name).trim(); }
    return {
      node: v("--twb-text-muted"),
      focus: v("--twb-accent"),
      dim: v("--twb-border"),
      edge: v("--twb-border-strong"),
      edgeHi: v("--twb-accent"),
      label: v("--twb-text-soft"),
      labelHi: v("--twb-text-normal")
    };
  }

  var REPULSION = 1400, REST = 70, SPRING = 0.03, GRAVITY = 0.012, DAMPING = 0.85;

  // One interactive force-directed graph on a canvas. nodes: [{title,url}];
  // links: [[i,j]] indices into nodes; opts: {labels:"auto"|"always",
  // focus:<index or -1>, maxFit:<cap for auto-fit zoom, optional>}.
  function createGraph(canvas, nodes, links, opts) {
    var ctx = canvas.getContext("2d");
    if (!ctx) return;
    var colors = palette();
    new MutationObserver(function () { colors = palette(); draw(); })
      .observe(root, { attributes: true, attributeFilter: ["data-theme"] });

    var deg = nodes.map(function () { return 0; });
    var adj = nodes.map(function () { return []; });
    links.forEach(function (l) {
      deg[l[0]]++; deg[l[1]]++;
      adj[l[0]].push(l[1]); adj[l[1]].push(l[0]);
    });

    // Deterministic golden-angle spiral start so layouts are repeatable.
    var sim = nodes.map(function (n, i) {
      var a = i * 2.39996, r = 16 * Math.sqrt(i + 1);
      return { x: Math.cos(a) * r, y: Math.sin(a) * r, vx: 0, vy: 0,
               r: Math.min(4 + 2.2 * Math.sqrt(deg[i]), 16) };
    });

    var width = 0, height = 0, dpr = window.devicePixelRatio || 1;
    var scale = 1, panX = 0, panY = 0, autoFit = true;
    var hover = -1, dragging = -1, panning = false, moved = false, alive = true;
    var pointers = {}, pinchDist = 0, raf = 0;

    function resize() {
      var box = canvas.getBoundingClientRect();
      width = Math.max(box.width, 1); height = Math.max(box.height, 1);
      canvas.width = Math.round(width * dpr);
      canvas.height = Math.round(height * dpr);
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      if (autoFit) fit();
      draw();
    }

    function fit() {
      var minX = Infinity, minY = Infinity, maxX = -Infinity, maxY = -Infinity;
      sim.forEach(function (p) {
        minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
        minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
      });
      var w = Math.max(maxX - minX, 40), h = Math.max(maxY - minY, 40);
      scale = Math.min(width / w, height / h) * 0.82;
      scale = Math.max(0.15, Math.min(scale, opts.maxFit || 1.6));
      panX = width / 2 - ((minX + maxX) / 2) * scale;
      panY = height / 2 - ((minY + maxY) / 2) * scale;
    }

    function toScreen(p) { return { x: p.x * scale + panX, y: p.y * scale + panY }; }
    function toWorld(x, y) { return { x: (x - panX) / scale, y: (y - panY) / scale }; }

    function tick() {
      var i, j;
      for (i = 0; i < sim.length; i++) {
        for (j = i + 1; j < sim.length; j++) {
          var dx = sim[j].x - sim[i].x, dy = sim[j].y - sim[i].y;
          var d2 = dx * dx + dy * dy + 1;
          var f = REPULSION / d2, inv = 1 / Math.sqrt(d2);
          dx *= inv; dy *= inv;
          sim[i].vx -= dx * f; sim[i].vy -= dy * f;
          sim[j].vx += dx * f; sim[j].vy += dy * f;
        }
      }
      links.forEach(function (l) {
        var a = sim[l[0]], b = sim[l[1]];
        var dx = b.x - a.x, dy = b.y - a.y;
        var d = Math.sqrt(dx * dx + dy * dy) || 1;
        var f = (d - REST) * SPRING;
        dx /= d; dy /= d;
        a.vx += dx * f; a.vy += dy * f;
        b.vx -= dx * f; b.vy -= dy * f;
      });
      var energy = 0;
      for (i = 0; i < sim.length; i++) {
        var p = sim[i];
        p.vx -= p.x * GRAVITY; p.vy -= p.y * GRAVITY;
        p.vx *= DAMPING; p.vy *= DAMPING;
        if (i !== dragging) { p.x += p.vx; p.y += p.vy; }
        energy += p.vx * p.vx + p.vy * p.vy;
      }
      return energy > 0.05 * sim.length || dragging >= 0;
    }

    function draw() {
      ctx.clearRect(0, 0, width, height);
      var hoverSet = null;
      if (hover >= 0) {
        hoverSet = {};
        hoverSet[hover] = true;
        adj[hover].forEach(function (n) { hoverSet[n] = true; });
      }
      ctx.lineWidth = 1;
      links.forEach(function (l) {
        var a = toScreen(sim[l[0]]), b = toScreen(sim[l[1]]);
        var hi = hover >= 0 && (l[0] === hover || l[1] === hover);
        ctx.strokeStyle = hi ? colors.edgeHi : colors.edge;
        ctx.globalAlpha = hi ? 0.9 : (hoverSet ? 0.15 : 0.5);
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      });
      ctx.globalAlpha = 1;
      var rScale = Math.min(scale, 1.4);
      nodes.forEach(function (n, i) {
        var p = toScreen(sim[i]);
        var lit = i === hover || i === opts.focus;
        ctx.fillStyle = lit ? colors.focus
          : (hoverSet && !hoverSet[i] ? colors.dim : colors.node);
        ctx.beginPath();
        ctx.arc(p.x, p.y, sim[i].r * rScale + (i === hover ? 1.5 : 0), 0, Math.PI * 2);
        ctx.fill();
      });
      var showAll = opts.labels === "always" || scale >= 1.1;
      ctx.font = '10px "JetBrains Mono", monospace';
      ctx.textAlign = "center";
      nodes.forEach(function (n, i) {
        var lit = hoverSet ? hoverSet[i] : false;
        if (!showAll && !lit) return;
        var p = toScreen(sim[i]);
        ctx.globalAlpha = hoverSet && !lit ? 0.3 : 1;
        ctx.fillStyle = lit ? colors.labelHi : colors.label;
        ctx.fillText(n.title, p.x, p.y + sim[i].r * rScale + 11);
      });
      ctx.globalAlpha = 1;
    }

    function frame() {
      raf = 0;
      var moving = alive && tick();
      if (autoFit) fit();
      draw();
      if (moving) schedule(); else alive = false;
    }
    function schedule() { if (!raf) raf = requestAnimationFrame(frame); }
    function wake() { alive = true; schedule(); }

    function nodeAt(x, y) {
      var w = toWorld(x, y), best = -1, bestD = Infinity;
      for (var i = 0; i < sim.length; i++) {
        var dx = w.x - sim[i].x, dy = w.y - sim[i].y;
        var d = Math.sqrt(dx * dx + dy * dy);
        if (d < sim[i].r + 6 / scale && d < bestD) { best = i; bestD = d; }
      }
      return best;
    }

    function local(e) {
      var box = canvas.getBoundingClientRect();
      return { x: e.clientX - box.left, y: e.clientY - box.top };
    }

    function zoomAt(x, y, factor) {
      var w = toWorld(x, y);
      scale = Math.max(0.15, Math.min(scale * factor, 4));
      panX = x - w.x * scale;
      panY = y - w.y * scale;
      autoFit = false;
      draw();
    }

    canvas.addEventListener("pointerdown", function (e) {
      canvas.setPointerCapture(e.pointerId);
      var p = local(e);
      pointers[e.pointerId] = p;
      var ids = Object.keys(pointers);
      if (ids.length === 2) {
        var a = pointers[ids[0]], b = pointers[ids[1]];
        pinchDist = Math.hypot(a.x - b.x, a.y - b.y);
        dragging = -1; panning = false;
        return;
      }
      moved = false;
      dragging = nodeAt(p.x, p.y);
      panning = dragging < 0;
    });

    canvas.addEventListener("pointermove", function (e) {
      var p = local(e);
      if (!pointers[e.pointerId]) {
        var h = nodeAt(p.x, p.y);
        if (h !== hover) {
          hover = h;
          canvas.style.cursor = h >= 0 ? "pointer" : "grab";
          draw();
        }
        return;
      }
      var prev = pointers[e.pointerId];
      pointers[e.pointerId] = p;
      var ids = Object.keys(pointers);
      if (ids.length === 2) {
        var a = pointers[ids[0]], b = pointers[ids[1]];
        var d = Math.hypot(a.x - b.x, a.y - b.y);
        if (pinchDist > 0) zoomAt((a.x + b.x) / 2, (a.y + b.y) / 2, d / pinchDist);
        pinchDist = d;
        return;
      }
      var dx = p.x - prev.x, dy = p.y - prev.y;
      if (dx !== 0 || dy !== 0) moved = true;
      if (dragging >= 0) {
        var w = toWorld(p.x, p.y);
        sim[dragging].x = w.x; sim[dragging].y = w.y;
        sim[dragging].vx = 0; sim[dragging].vy = 0;
        autoFit = false;
        wake();
      } else if (panning) {
        panX += dx; panY += dy;
        autoFit = false;
        draw();
      }
    });

    canvas.addEventListener("pointerup", function (e) {
      var wasDrag = dragging;
      delete pointers[e.pointerId];
      if (Object.keys(pointers).length < 2) pinchDist = 0;
      if (!moved && wasDrag >= 0) {
        location.href = base + encodeURI(nodes[wasDrag].url);
        return;
      }
      if (Object.keys(pointers).length === 0) { dragging = -1; panning = false; }
    });

    canvas.addEventListener("pointercancel", function (e) {
      delete pointers[e.pointerId];
      dragging = -1; panning = false; pinchDist = 0;
    });

    canvas.addEventListener("pointerleave", function () {
      if (hover >= 0 && Object.keys(pointers).length === 0) { hover = -1; draw(); }
    });

    canvas.addEventListener("wheel", function (e) {
      e.preventDefault();
      var p = local(e);
      zoomAt(p.x, p.y, Math.exp(-e.deltaY * 0.0012));
    }, { passive: false });

    window.addEventListener("resize", resize);
    resize();
    schedule();
  }

  var view = document.getElementById("graph-view");
  if (view) {
    var canvas = view.querySelector("canvas");
    if (canvas) createGraph(canvas, data.nodes, data.edges, { labels: "auto", focus: -1 });
  }

  var notePath = root.getAttribute("data-note");
  var aside = document.querySelector("aside.toc");
  if (notePath && aside) {
    var meId = -1;
    data.nodes.forEach(function (n) { if (n.url === notePath) meId = n.id; });
    if (meId >= 0) {
      var keep = {};
      keep[meId] = true;
      data.edges.forEach(function (l) {
        if (l[0] === meId) keep[l[1]] = true;
        if (l[1] === meId) keep[l[0]] = true;
      });
      var ids = Object.keys(keep).map(Number).sort(function (a, b) { return a - b; });
      if (ids.length > 1) {
        var remap = {};
        var subNodes = ids.map(function (id, i) { remap[id] = i; return data.nodes[id]; });
        var subLinks = [];
        data.edges.forEach(function (l) {
          if (keep[l[0]] && keep[l[1]]) subLinks.push([remap[l[0]], remap[l[1]]]);
        });
        var panel = document.createElement("details");
        panel.id = "local-graph";
        var label = document.createElement("summary");
        label.className = "manifest-label";
        label.textContent = "graph";
        panel.appendChild(label);
        var cv = document.createElement("canvas");
        panel.appendChild(cv);
        try {
          panel.open = localStorage.getItem("twb-local-graph") !== "closed";
        } catch (e) { panel.open = true; }
        panel.addEventListener("toggle", function () {
          try {
            if (panel.open) localStorage.removeItem("twb-local-graph");
            else localStorage.setItem("twb-local-graph", "closed");
          } catch (e) { /* private mode */ }
          // The canvas has zero size while collapsed; re-measure on expand.
          if (panel.open) window.dispatchEvent(new Event("resize"));
        });
        aside.appendChild(panel);
        createGraph(cv, subNodes, subLinks, {
          labels: "always", focus: remap[meId], maxFit: 1.1
        });
      }
    }
  }
})();
