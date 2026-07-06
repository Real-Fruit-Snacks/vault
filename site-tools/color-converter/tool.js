(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var input = $("cc-input"), picker = $("cc-picker"), error = $("cc-error"),
      results = $("cc-results"), swatch = $("cc-swatch"),
      hexEl = $("cc-hex"), rgbEl = $("cc-rgb"), hslEl = $("cc-hsl"), contrast = $("cc-contrast");
  if (!input || !swatch) return;

  function clamp(n, lo, hi) { return Math.min(hi, Math.max(lo, n)); }
  function round2(n) { return Math.round(n * 100) / 100; }
  function hex2(c) { return ("0" + Math.round(c).toString(16)).slice(-2); }

  function parseAlpha(a) {
    if (a == null || a === "") return 1;
    return clamp(a.indexOf("%") !== -1 ? parseFloat(a) / 100 : parseFloat(a), 0, 1);
  }

  function hslToRgb(h, s, l) {
    h = ((h % 360) + 360) % 360; s = clamp(s, 0, 100) / 100; l = clamp(l, 0, 100) / 100;
    var c = (1 - Math.abs(2 * l - 1)) * s;
    var x = c * (1 - Math.abs((h / 60) % 2 - 1));
    var m = l - c / 2, r, g, b;
    if (h < 60) { r = c; g = x; b = 0; }
    else if (h < 120) { r = x; g = c; b = 0; }
    else if (h < 180) { r = 0; g = c; b = x; }
    else if (h < 240) { r = 0; g = x; b = c; }
    else if (h < 300) { r = x; g = 0; b = c; }
    else { r = c; g = 0; b = x; }
    return { r: Math.round((r + m) * 255), g: Math.round((g + m) * 255), b: Math.round((b + m) * 255) };
  }

  function rgbToHsl(r, g, b) {
    r /= 255; g /= 255; b /= 255;
    var max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min;
    var h = 0, s = 0, l = (max + min) / 2;
    if (d) {
      s = d / (1 - Math.abs(2 * l - 1));
      if (max === r) h = ((g - b) / d) % 6;
      else if (max === g) h = (b - r) / d + 2;
      else h = (r - g) / d + 4;
      h *= 60; if (h < 0) h += 360;
    }
    return { h: Math.round(h), s: Math.round(s * 100), l: Math.round(l * 100) };
  }

  function parse(str) {
    var s = str.trim().toLowerCase(), m;
    if ((m = s.match(/^#?([0-9a-f]{3,8})$/))) {
      var h = m[1], len = h.length;
      if (len !== 3 && len !== 4 && len !== 6 && len !== 8) return null;
      function p(x) { return parseInt(x, 16); }
      if (len === 3 || len === 4) {
        return { r: p(h[0] + h[0]), g: p(h[1] + h[1]), b: p(h[2] + h[2]),
                 a: len === 4 ? p(h[3] + h[3]) / 255 : 1 };
      }
      return { r: p(h.slice(0, 2)), g: p(h.slice(2, 4)), b: p(h.slice(4, 6)),
               a: len === 8 ? p(h.slice(6, 8)) / 255 : 1 };
    }
    if ((m = s.match(/^rgba?\(\s*([\d.]+)[\s,]+([\d.]+)[\s,]+([\d.]+)(?:[\s,\/]+([\d.%]+))?\s*\)$/))) {
      return { r: clamp(Math.round(+m[1]), 0, 255), g: clamp(Math.round(+m[2]), 0, 255),
               b: clamp(Math.round(+m[3]), 0, 255), a: parseAlpha(m[4]) };
    }
    if ((m = s.match(/^hsla?\(\s*([\d.]+)(?:deg)?[\s,]+([\d.]+)%[\s,]+([\d.]+)%(?:[\s,\/]+([\d.%]+))?\s*\)$/))) {
      var rgb = hslToRgb(+m[1], +m[2], +m[3]);
      return { r: rgb.r, g: rgb.g, b: rgb.b, a: parseAlpha(m[4]) };
    }
    return null;
  }

  function fmtHex(c) {
    var base = "#" + hex2(c.r) + hex2(c.g) + hex2(c.b);
    return c.a < 1 ? base + hex2(Math.round(c.a * 255)) : base;
  }
  function fmtRgb(c) {
    return c.a < 1 ? "rgba(" + c.r + ", " + c.g + ", " + c.b + ", " + round2(c.a) + ")"
                   : "rgb(" + c.r + ", " + c.g + ", " + c.b + ")";
  }
  function fmtHsl(c) {
    var h = rgbToHsl(c.r, c.g, c.b);
    return c.a < 1 ? "hsla(" + h.h + ", " + h.s + "%, " + h.l + "%, " + round2(c.a) + ")"
                   : "hsl(" + h.h + ", " + h.s + "%, " + h.l + "%)";
  }

  function luminance(c) {
    function ch(v) { v /= 255; return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
    return 0.2126 * ch(c.r) + 0.7152 * ch(c.g) + 0.0722 * ch(c.b);
  }
  function ratio(l1, l2) { var hi = Math.max(l1, l2), lo = Math.min(l1, l2); return (hi + 0.05) / (lo + 0.05); }
  function badge(ok) { return '<span class="cc-badge ' + (ok ? "cc-pass" : "cc-fail") + '">' + (ok ? "pass" : "fail") + "</span>"; }

  function card(label, bg, fg, r) {
    return '<div class="cc-cc-card">' +
      '<div class="cc-cc-sample" style="background:' + bg + ';color:' + fg + '">Aa</div>' +
      '<div class="cc-cc-meta">' +
        '<div class="cc-cc-ratio">' + round2(r) + ":1</div>" +
        '<div class="cc-cc-label">vs ' + label + "</div>" +
        '<div class="cc-badges">AA ' + badge(r >= 4.5) + " AAA " + badge(r >= 7) +
          " large " + badge(r >= 3) + "</div>" +
      "</div></div>";
  }

  function update(fromPicker) {
    var c = parse(input.value);
    if (!c) {
      error.hidden = false;
      error.textContent = "Unrecognized color — try #ff6e7a, rgb(255,110,122), or hsl(354,100%,72%).";
      results.classList.add("cc-dim");
      contrast.innerHTML = "";
      return;
    }
    error.hidden = true;
    results.classList.remove("cc-dim");
    var opaque = "#" + hex2(c.r) + hex2(c.g) + hex2(c.b);
    swatch.style.background = fmtRgb(c);
    hexEl.textContent = fmtHex(c);
    rgbEl.textContent = fmtRgb(c);
    hslEl.textContent = fmtHsl(c);
    if (!fromPicker) picker.value = opaque;

    var L = luminance(c);
    contrast.innerHTML = card("white", "#ffffff", opaque, ratio(L, 1)) +
                         card("black", "#000000", opaque, ratio(L, 0));
  }

  input.addEventListener("input", function () { update(false); });
  picker.addEventListener("input", function () { input.value = picker.value; update(true); });
  update(false);
})();
