(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var input = $("ts-input");
  var error = $("ts-error");
  var note = $("ts-note");
  var tableWrap = $("ts-table-wrap");
  var tbody = $("ts-body");
  var nowS = $("ts-now-s");
  var nowMs = $("ts-now-ms");
  if (!input || !tbody) return;

  var DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"];

  function pad(n, w) {
    var s = String(Math.abs(n));
    while (s.length < (w || 2)) s = "0" + s;
    return (n < 0 ? "-" : "") + s;
  }

  function isoUTC(d) {
    return pad(d.getUTCFullYear(), 4) + "-" + pad(d.getUTCMonth() + 1) + "-" +
      pad(d.getUTCDate()) + "T" + pad(d.getUTCHours()) + ":" +
      pad(d.getUTCMinutes()) + ":" + pad(d.getUTCSeconds()) + "Z";
  }

  function localStr(d) {
    var offMin = -d.getTimezoneOffset();
    var sign = offMin >= 0 ? "+" : "-";
    var abs = Math.abs(offMin);
    var off = sign + pad(Math.floor(abs / 60)) + ":" + pad(abs % 60);
    return pad(d.getFullYear(), 4) + "-" + pad(d.getMonth() + 1) + "-" +
      pad(d.getDate()) + " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + ":" +
      pad(d.getSeconds()) + " UTC" + off;
  }

  function relative(ms) {
    var diff = ms - Date.now();
    var future = diff > 0;
    var s = Math.round(Math.abs(diff) / 1000);
    var value, unit;
    if (s < 60) { value = s; unit = "second"; }
    else if (s < 3600) { value = Math.round(s / 60); unit = "minute"; }
    else if (s < 86400 * 2) { value = Math.round(s / 3600); unit = "hour"; }
    else if (s < 86400 * 365) { value = Math.round(s / 86400); unit = "day"; }
    else { value = Math.round(s / (86400 * 365.25) * 10) / 10; unit = "year"; }
    var phrase = value + " " + unit + (value === 1 ? "" : "s");
    return future ? "in " + phrase : phrase + " ago";
  }

  function parse(text) {
    var raw = text.trim();
    if (!raw) return null;
    if (/^-?\d+$/.test(raw)) {
      var n = parseInt(raw, 10);
      var digits = raw.replace("-", "").length;
      var isMs = digits >= 12;
      var ms = isMs ? n : n * 1000;
      if (!isFinite(ms) || Math.abs(ms) > 8.64e15) throw "that number is outside the representable date range";
      var digitWord = digits + " digit" + (digits === 1 ? "" : "s");
      return { ms: ms, note: isMs
        ? "interpreted as milliseconds (" + digitWord + ")"
        : "interpreted as seconds (" + digitWord + " — 12 or more would mean milliseconds)" };
    }
    var parsed = Date.parse(raw);
    if (isNaN(parsed)) {
      throw "'" + raw + "' is neither an epoch number nor a date I can parse — try ISO 8601 like 2026-12-25T09:00:00Z";
    }
    var hasTz = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(raw);
    var dateOnly = /^\d{4}-\d{2}-\d{2}$/.test(raw);
    return { ms: parsed, note: dateOnly
      ? "bare dates parse as midnight UTC"
      : (hasTz ? null : "no timezone given — parsed in your local timezone") };
  }

  function row(label, value, extra) {
    return "<tr><td>" + label + '</td><td class="ts-mono">' + value +
      (extra ? ' <span class="ts-dim">' + extra + "</span>" : "") + "</td></tr>";
  }

  function analyze() {
    error.hidden = true;
    note.hidden = true;
    tableWrap.hidden = true;
    var result;
    try {
      result = parse(input.value);
    } catch (message) {
      error.textContent = "✗ " + message;
      error.hidden = false;
      return;
    }
    if (!result) return;
    if (result.note) {
      note.textContent = result.note;
      note.hidden = false;
    }
    var d = new Date(result.ms);
    var secs = Math.floor(result.ms / 1000);
    tbody.innerHTML = [
      row("unix seconds", String(secs)),
      row("unix milliseconds", String(result.ms)),
      row("utc", isoUTC(d)),
      row("local", localStr(d)),
      row("weekday", DAYS[d.getUTCDay()], "UTC"),
      row("relative", relative(result.ms))
    ].join("");
    tableWrap.hidden = false;
  }

  function tick() {
    var now = Date.now();
    nowS.textContent = String(Math.floor(now / 1000));
    nowMs.textContent = String(now);
  }
  tick();
  setInterval(tick, 1000);

  $("ts-use-now").addEventListener("click", function () {
    input.value = String(Math.floor(Date.now() / 1000));
    analyze();
    input.focus();
  });
  input.addEventListener("input", analyze);
  Array.prototype.forEach.call(document.querySelectorAll(".ts-example[data-ts]"), function (btn) {
    btn.addEventListener("click", function () {
      input.value = btn.getAttribute("data-ts");
      analyze();
      input.focus();
    });
  });
  analyze();
})();
