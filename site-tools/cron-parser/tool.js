(function () {
  "use strict";
  var input = document.getElementById("cp-input");
  var boxes = document.getElementById("cp-boxes");
  var error = document.getElementById("cp-error");
  var expanded = document.getElementById("cp-expanded");
  var rebootNote = document.getElementById("cp-reboot");
  var tableWrap = document.getElementById("cp-table-wrap");
  var tbody = document.getElementById("cp-body");
  var runsBlock = document.getElementById("cp-runs-block");
  var runsList = document.getElementById("cp-runs");
  if (!input || !boxes || !error || !tbody) return;

  var MONTH_NAMES = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  var DAY_NAMES = ["SUN", "MON", "TUE", "WED", "THU", "FRI", "SAT"];
  var SHORTCUTS = {
    "@yearly": "0 0 1 1 *", "@annually": "0 0 1 1 *", "@monthly": "0 0 1 * *",
    "@weekly": "0 0 * * 0", "@daily": "0 0 * * *", "@midnight": "0 0 * * *",
    "@hourly": "0 * * * *"
  };
  var FIELDS = [
    { name: "minute", cls: "cp-min", min: 0, max: 59, unit: ["minute", "minutes"] },
    { name: "hour", cls: "cp-hour", min: 0, max: 23, unit: ["hour", "hours"] },
    { name: "day of month", cls: "cp-dom", min: 1, max: 31, unit: ["day", "days"] },
    { name: "month", cls: "cp-mon", min: 1, max: 12, unit: ["month", "months"],
      names: MONTH_NAMES, nameBase: 1 },
    { name: "weekday", cls: "cp-dow", min: 0, max: 7, unit: ["weekday", "weekdays"],
      names: DAY_NAMES, nameBase: 0, mod: 7 }
  ];

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function disp(field, v) {
    if (!field.names) return String(v);
    var idx = field.mod ? v % field.mod : v - field.nameBase;
    return field.names[idx] !== undefined ? field.names[idx] : String(v);
  }

  function resolveValue(field, token) {
    if (/^\d+$/.test(token)) return parseInt(token, 10);
    if (field.names) {
      var idx = field.names.indexOf(token.slice(0, 3).toUpperCase());
      if (idx !== -1) return idx + field.nameBase;
    }
    throw field.name + ": '" + token + "' is not a number" +
      (field.names ? " or a name like " + field.names[0] : "");
  }

  function describeTerm(field, base, lo, hi, step, hasStep) {
    if (base === "*" && !hasStep) return "every " + field.unit[0];
    if (base === "*") return "every " + step + " " + field.unit[1];
    if (lo === hi) return field.unit[0] + " " + disp(field, lo);
    var range = disp(field, lo) + " through " + disp(field, hi);
    if (!hasStep) return field.unit[1] + " " + range;
    return "every " + step + " " + field.unit[1] + " from " + range;
  }

  function parseField(field, text) {
    var values = {};
    var descs = [];
    var terms = text.split(",");
    for (var i = 0; i < terms.length; i++) {
      var term = terms[i];
      if (!term) throw field.name + ": empty list item in '" + text + "'";
      var stepParts = term.split("/");
      if (stepParts.length > 2) throw field.name + ": too many '/' in '" + term + "'";
      var hasStep = stepParts.length === 2;
      var step = 1;
      if (hasStep) {
        if (!/^\d+$/.test(stepParts[1]) || parseInt(stepParts[1], 10) === 0) {
          throw field.name + ": step '" + stepParts[1] + "' must be a positive number";
        }
        step = parseInt(stepParts[1], 10);
      }
      var base = stepParts[0];
      var lo, hi;
      if (base === "*") {
        lo = field.min; hi = field.max;
      } else if (base.indexOf("-") !== -1) {
        var ends = base.split("-");
        if (ends.length !== 2 || !ends[0] || !ends[1]) {
          throw field.name + ": bad range '" + base + "'";
        }
        lo = resolveValue(field, ends[0]);
        hi = resolveValue(field, ends[1]);
      } else {
        lo = resolveValue(field, base);
        hi = hasStep ? field.max : lo;
      }
      if (lo < field.min || lo > field.max) {
        throw field.name + ": " + lo + " is out of range " + field.min + "-" + field.max;
      }
      if (hi < field.min || hi > field.max) {
        throw field.name + ": " + hi + " is out of range " + field.min + "-" + field.max;
      }
      if (lo > hi) throw field.name + ": range '" + base + "' is reversed";
      for (var v = lo; v <= hi; v += step) {
        values[field.mod ? v % field.mod : v] = true;
      }
      descs.push(describeTerm(field, base, lo, hi, step, hasStep));
    }
    return { values: values, desc: descs.join("; "),
             restricted: text.charAt(0) !== "*" };
  }

  function parse(text) {
    var raw = text.trim().replace(/\s+/g, " ");
    if (!raw) return null;
    var lower = raw.toLowerCase();
    if (lower === "@reboot") return { reboot: true };
    var source = SHORTCUTS[lower] || raw;
    var parts = source.split(" ");
    if (parts.length !== 5) {
      if (parts.length === 6 || parts.length === 7) {
        throw "that looks like a " + parts.length + "-field (Quartz-style) expression — " +
          "standard Unix cron has exactly 5 fields (minute hour day-of-month month weekday)";
      }
      throw "expected 5 fields (minute hour day-of-month month weekday), got " + parts.length;
    }
    var fields = [];
    for (var i = 0; i < 5; i++) {
      fields.push({ spec: FIELDS[i], text: parts[i],
                    parsed: parseField(FIELDS[i], parts[i]) });
    }
    return { fields: fields, shortcut: SHORTCUTS[lower] ? raw : null, source: source };
  }

  function nextRuns(fields, count) {
    var minute = fields[0].parsed, hour = fields[1].parsed, dom = fields[2].parsed,
        month = fields[3].parsed, dow = fields[4].parsed;
    var minutes = Object.keys(minute.values).map(Number).sort(function (a, b) { return a - b; });
    var hours = Object.keys(hour.values).map(Number).sort(function (a, b) { return a - b; });
    var runs = [];
    var now = new Date();
    var start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    for (var d = 0; d < 1600 && runs.length < count; d++) {
      var day = new Date(start.getFullYear(), start.getMonth(), start.getDate() + d);
      if (!month.values[day.getMonth() + 1]) continue;
      var domOk = !!dom.values[day.getDate()];
      var dowOk = !!dow.values[day.getDay()];
      var dayOk;
      if (dom.restricted && dow.restricted) dayOk = domOk || dowOk;
      else if (dom.restricted) dayOk = domOk;
      else if (dow.restricted) dayOk = dowOk;
      else dayOk = true;
      if (!dayOk) continue;
      for (var h = 0; h < hours.length && runs.length < count; h++) {
        for (var m = 0; m < minutes.length && runs.length < count; m++) {
          var t = new Date(day.getFullYear(), day.getMonth(), day.getDate(),
                           hours[h], minutes[m]);
          if (t > now) runs.push(t);
        }
      }
    }
    return runs;
  }

  function pad(n) { return (n < 10 ? "0" : "") + n; }

  function fmt(t) {
    return t.getFullYear() + "-" + pad(t.getMonth() + 1) + "-" + pad(t.getDate()) +
      " " + pad(t.getHours()) + ":" + pad(t.getMinutes()) +
      " (" + DAY_NAMES[t.getDay()] + ")";
  }

  function relative(t, now) {
    var s = Math.round((t - now) / 1000);
    if (s < 90) return "in " + s + " seconds";
    var m = Math.round(s / 60);
    if (m < 90) return "in " + m + " minutes";
    var h = Math.round(m / 60);
    if (h < 48) return "in " + h + " hours";
    return "in " + Math.round(h / 24) + " days";
  }

  function hideAll() {
    error.hidden = true;
    expanded.hidden = true;
    boxes.hidden = true;
    rebootNote.hidden = true;
    tableWrap.hidden = true;
    runsBlock.hidden = true;
  }

  function analyze() {
    hideAll();
    var result;
    try {
      result = parse(input.value);
    } catch (message) {
      error.textContent = "✗ " + message;
      error.hidden = false;
      return;
    }
    if (!result) return;
    if (result.reboot) {
      rebootNote.hidden = false;
      return;
    }
    if (result.shortcut) {
      expanded.textContent = result.shortcut + " expands to “" + result.source + "”";
      expanded.hidden = false;
    }
    boxes.innerHTML = result.fields.map(function (f) {
      return '<div class="cp-field ' + f.spec.cls + '">' +
        '<span class="cp-value">' + escapeHtml(f.text) + "</span>" +
        '<span class="manifest-label">' + f.spec.name + "</span></div>";
    }).join("");
    boxes.hidden = false;
    tbody.innerHTML = result.fields.map(function (f) {
      return '<tr><td><span class="cp-badge ' + f.spec.cls + '">' + f.spec.name +
        '</span></td><td class="cp-mono">' + escapeHtml(f.text) + "</td><td>" +
        escapeHtml(f.parsed.desc) + "</td></tr>";
    }).join("");
    tableWrap.hidden = false;
    var now = new Date();
    var runs = nextRuns(result.fields, 5);
    runsList.innerHTML = runs.length
      ? runs.map(function (t) {
          return '<li><span class="cp-when">' + fmt(t) + "</span>" +
            '<span class="cp-rel">' + relative(t, now) + "</span></li>";
        }).join("")
      : '<li>no matching times in the next ~4 years</li>';
    runsBlock.hidden = false;
  }

  input.addEventListener("input", analyze);
  Array.prototype.forEach.call(document.querySelectorAll(".cp-example"), function (btn) {
    btn.addEventListener("click", function () {
      input.value = btn.getAttribute("data-cron");
      analyze();
      input.focus();
    });
  });
  analyze();
})();
