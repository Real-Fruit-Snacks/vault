(function () {
  "use strict";
  var input = document.getElementById("ca-input");
  var summary = document.getElementById("ca-summary");
  var truncated = document.getElementById("ca-truncated");
  var tableWrap = document.getElementById("ca-table-wrap");
  var tbody = document.getElementById("ca-body");
  var view = document.getElementById("ca-view");
  var viewCaption = document.getElementById("ca-view-caption");
  var viewTruncated = document.getElementById("ca-view-truncated");
  var md5Block = document.getElementById("ca-md5-block");
  var md5Raw = document.getElementById("ca-md5-raw");
  var md5Lf = document.getElementById("ca-md5-lf");
  var md5Crlf = document.getElementById("ca-md5-crlf");
  if (!input || !summary || !tableWrap || !tbody || !view) return;

  var MAX_ROWS = 5000;
  var VIEW_MAX = 10000;

  var CATEGORIES = [
    { name: "uppercase", cls: "upper", re: /^\p{Lu}$/u },
    { name: "lowercase", cls: "lower", re: /^\p{Ll}$/u },
    { name: "letter (other)", cls: "letter-other", re: /^\p{L}$/u },
    { name: "digit", cls: "digit", re: /^\p{Nd}$/u },
    { name: "number (other)", cls: "digit", re: /^\p{N}$/u },
    { name: "punctuation", cls: "punct", re: /^\p{P}$/u },
    { name: "symbol", cls: "symbol", re: /^\p{S}$/u },
    { name: "mark", cls: "other", re: /^\p{M}$/u }
  ];
  var CHIP_ORDER = ["total", "uppercase", "lowercase", "letter (other)", "digit",
    "number (other)", "punctuation", "symbol", "whitespace", "mark", "control", "other"];
  var VISIBLE = { " ": "␣", "\t": "⇥", "\n": "⏎", "\r": "␍" };
  var NAMED = { " ": "space", "\t": "tab", "\n": "newline", "\r": "carriage return" };

  function classify(ch) {
    if (VISIBLE[ch] || /^\p{Z}$/u.test(ch)) return { name: "whitespace", cls: "space" };
    if (/^\p{C}$/u.test(ch)) return { name: "control", cls: "control" };
    for (var i = 0; i < CATEGORIES.length; i++) {
      if (CATEGORIES[i].re.test(ch)) return CATEGORIES[i];
    }
    return { name: "other", cls: "other" };
  }

  function display(ch, cls) {
    if (VISIBLE[ch]) return VISIBLE[ch];
    if (cls === "control" || cls === "space") return "·";
    return ch;
  }

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function codePointLabel(cp) {
    var hex = cp.toString(16).toUpperCase();
    while (hex.length < 4) hex = "0" + hex;
    return "U+" + hex;
  }

  function tileTitle(ch, cat, cp) {
    var parts = [];
    if (NAMED[ch]) {
      parts.push(NAMED[ch]);
    } else if (cat.cls !== "control" && cat.cls !== "space") {
      parts.push(ch);
    }
    parts.push(cat.name);
    parts.push(codePointLabel(cp));
    return parts.join(" · ");
  }

  function analyze() {
    var text = input.value;
    if (!text) {
      summary.hidden = true;
      tableWrap.hidden = true;
      truncated.hidden = true;
      view.hidden = true;
      viewCaption.hidden = true;
      viewTruncated.hidden = true;
      if (md5Block) md5Block.hidden = true;
      view.innerHTML = "";
      tbody.innerHTML = "";
      return;
    }
    if (md5Block && window.md5Bytes) {
      var encoder = new TextEncoder();
      md5Raw.textContent = window.md5Bytes(encoder.encode(text));
      md5Lf.textContent = window.md5Bytes(encoder.encode(text + "\n"));
      md5Crlf.textContent = window.md5Bytes(encoder.encode(text + "\r\n"));
      md5Block.hidden = false;
    }
    var counts = { total: 0 };
    var rows = [];
    var viewParts = [];
    var iter = text[Symbol.iterator]();
    for (var step = iter.next(); !step.done; step = iter.next()) {
      var ch = step.value;
      var cat = classify(ch);
      counts.total += 1;
      counts[cat.name] = (counts[cat.name] || 0) + 1;
      if (rows.length < MAX_ROWS) {
        var cp = ch.codePointAt(0);
        rows.push("<tr><td>" + counts.total + "</td>" +
          '<td class="ca-char">' + escapeHtml(display(ch, cat.cls)) + "</td>" +
          '<td><span class="ca-badge ca-' + cat.cls + '">' + cat.name + "</span></td>" +
          '<td class="ca-cp">' + codePointLabel(cp) + "</td>" +
          '<td class="ca-cp">' + cp + "</td></tr>");
      }
      if (counts.total <= VIEW_MAX) {
        viewParts.push('<span class="ca-cell ca-' + cat.cls + '" title="' +
          escapeHtml(tileTitle(ch, cat, ch.codePointAt(0))) + '">' +
          escapeHtml(display(ch, cat.cls)) + "</span>");
        if (ch === "\n") viewParts.push('<span class="ca-break"></span>');
      }
    }
    view.innerHTML = viewParts.join("");
    view.hidden = false;
    viewCaption.hidden = false;
    viewTruncated.hidden = counts.total <= VIEW_MAX;
    summary.innerHTML = CHIP_ORDER.filter(function (k) { return counts[k]; })
      .map(function (k) {
        return '<span class="ca-chip"><span class="manifest-label">' + k + "</span>" +
          counts[k] + "</span>";
      }).join("");
    summary.hidden = false;
    tbody.innerHTML = rows.join("");
    tableWrap.hidden = false;
    truncated.hidden = counts.total <= MAX_ROWS;
  }

  input.addEventListener("input", analyze);
  Array.prototype.forEach.call(document.querySelectorAll(".ca-example"), function (btn) {
    btn.addEventListener("click", function () {
      input.value = btn.getAttribute("data-text");
      analyze();
      input.focus();
    });
  });
  analyze();
})();
