(function () {
  "use strict";
  var view = document.getElementById("canvas-view");
  if (!view) return;
  var world = view.querySelector(".canvas-world");
  var fitBtn = document.getElementById("canvas-fit");
  var scale = 1, tx = 0, ty = 0;

  function apply() {
    world.style.transform =
      "translate(" + tx + "px," + ty + "px) scale(" + scale + ")";
  }
  function fit() {
    var vw = view.clientWidth, vh = view.clientHeight;
    // A hidden container measures 0x0; a zero scale would poison every
    // later zoomAt (factor = next / scale). Keep the current transform.
    if (!vw || !vh) return;
    var w = world.offsetWidth || 1, h = world.offsetHeight || 1;
    scale = Math.min(vw / w, vh / h, 1);
    tx = (vw - w * scale) / 2;
    ty = (vh - h * scale) / 2;
    apply();
  }
  function zoomAt(mx, my, factor) {
    var next = Math.min(Math.max(scale * factor, 0.1), 3);
    factor = next / scale;
    tx = mx - (mx - tx) * factor;
    ty = my - (my - ty) * factor;
    scale = next;
    apply();
  }

  view.addEventListener("wheel", function (e) {
    e.preventDefault();
    var rect = view.getBoundingClientRect();
    zoomAt(e.clientX - rect.left, e.clientY - rect.top, Math.pow(1.0015, -e.deltaY));
  }, { passive: false });

  // pointer pan + two-finger pinch
  var pointers = {};
  var pinchDist = 0;
  function pointerCount() {
    var n = 0, k;
    for (k in pointers) if (pointers.hasOwnProperty(k)) n++;
    return n;
  }
  view.addEventListener("pointerdown", function (e) {
    if (e.target.closest("a, button")) return;
    if (e.target.closest(".canvas-embed-body")) return; // embedded notes scroll/select
    pointers[e.pointerId] = { x: e.clientX, y: e.clientY };
    if (pointerCount() === 2) {
      var pts = [], k;
      for (k in pointers) if (pointers.hasOwnProperty(k)) pts.push(pointers[k]);
      pinchDist = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
    }
    view.setPointerCapture(e.pointerId);
    e.preventDefault();
  });
  view.addEventListener("pointermove", function (e) {
    var p = pointers[e.pointerId];
    if (!p) return;
    if (pointerCount() === 2) {
      var pts = [], k;
      p.x = e.clientX; p.y = e.clientY;
      for (k in pointers) if (pointers.hasOwnProperty(k)) pts.push(pointers[k]);
      var d = Math.hypot(pts[0].x - pts[1].x, pts[0].y - pts[1].y);
      if (pinchDist > 0) {
        var rect = view.getBoundingClientRect();
        zoomAt((pts[0].x + pts[1].x) / 2 - rect.left,
               (pts[0].y + pts[1].y) / 2 - rect.top, d / pinchDist);
      }
      pinchDist = d;
      return;
    }
    tx += e.clientX - p.x;
    ty += e.clientY - p.y;
    p.x = e.clientX; p.y = e.clientY;
    apply();
  });
  function release(e) {
    delete pointers[e.pointerId];
    pinchDist = 0;
  }
  view.addEventListener("pointerup", release);
  view.addEventListener("pointercancel", release);

  if (fitBtn) fitBtn.addEventListener("click", fit);
  window.addEventListener("resize", fit);
  fit();
})();
