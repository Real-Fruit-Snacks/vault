(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var els = {
    name: $("st-name"), prog: $("st-prog"), args: $("st-args"), sc: $("st-sc"),
    mo: $("st-mo"), moUnit: $("st-mo-unit"), monthlyMode: $("st-monthly-mode"),
    dom: $("st-dom"), dow: $("st-dow"), days: $("st-days"), months: $("st-months"),
    st: $("st-st"), sd: $("st-sd"), idle: $("st-idle"),
    ru: $("st-ru"), ruCustom: $("st-ru-custom"), rl: $("st-rl"), f: $("st-f"),
    errors: $("st-errors"), summary: $("st-summary"), output: $("st-output")
  };
  if (!els.name || !els.output) return;

  var shortPathEl = $("st-short-path");
  var shortUseBtn = $("st-short-use");
  var shortVerifyEl = $("st-short-verify");

  var DAYS = ["MON", "TUE", "WED", "THU", "FRI", "SAT", "SUN"];
  var MONTHS = ["JAN", "FEB", "MAR", "APR", "MAY", "JUN",
    "JUL", "AUG", "SEP", "OCT", "NOV", "DEC"];
  var MO_LIMITS = {
    MINUTE: { max: 1439, unit: "minute(s)" },
    HOURLY: { max: 23, unit: "hour(s)" },
    DAILY: { max: 365, unit: "day(s)" },
    WEEKLY: { max: 52, unit: "week(s)" },
    MONTHLY: { max: 12, unit: "month(s)" }
  };

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function makeChips(container, labels, prefix) {
    container.innerHTML = labels.map(function (l) {
      return '<label class="st-chip"><input type="checkbox" value="' + l + '" ' +
        'data-group="' + prefix + '"><span>' + l + "</span></label>";
    }).join("");
  }
  makeChips(els.days, DAYS, "day");
  makeChips(els.months, MONTHS, "month");
  els.dom.innerHTML = (function () {
    var opts = [];
    for (var d = 1; d <= 31; d++) opts.push("<option>" + d + "</option>");
    return opts.join("");
  })();

  function chipValues(container) {
    return Array.prototype.map.call(
      container.querySelectorAll("input:checked"),
      function (c) { return c.value; });
  }

  function show(rowId, visible) { $(rowId).hidden = !visible; }

  function updateVisibility() {
    var sc = els.sc.value;
    var monthly = sc === "MONTHLY";
    var mode = els.monthlyMode.value;
    var hasMo = !!MO_LIMITS[sc] && !(monthly && mode !== "DOM");
    show("st-row-mo", hasMo);
    if (MO_LIMITS[sc]) {
      els.moUnit.textContent = MO_LIMITS[sc].unit;
      els.mo.max = MO_LIMITS[sc].max;
    }
    show("st-row-monthly-mode", monthly);
    show("st-row-dom", monthly && mode === "DOM");
    show("st-row-dow", monthly && mode !== "DOM" && mode !== "LASTDAY");
    show("st-row-days", sc === "WEEKLY");
    show("st-row-months", monthly);
    show("st-row-st", sc !== "ONSTART" && sc !== "ONLOGON" && sc !== "ONIDLE");
    show("st-row-sd", sc === "ONCE");
    show("st-row-idle", sc === "ONIDLE");
    els.ruCustom.hidden = els.ru.value !== "custom";
  }

  function fmtDate(iso) {
    var p = iso.split("-");
    return p[1] + "/" + p[2] + "/" + p[0];
  }

  var KNOWN_SHORT = {
    "program files": "PROGRA~1",
    "program files (x86)": "PROGRA~2"
  };

  function shortSegment(seg, isFile) {
    var known = KNOWN_SHORT[seg.toLowerCase()];
    if (known) return known;
    if (seg.indexOf(" ") === -1) return seg;
    var name = seg;
    var ext = "";
    if (isFile) {
      var dot = seg.lastIndexOf(".");
      if (dot > 0) {
        name = seg.slice(0, dot);
        ext = seg.slice(dot + 1);
      }
    }
    var cleaned = name.replace(/[ .]/g, "").toUpperCase();
    if (!cleaned) return seg;
    var base = cleaned.slice(0, 6) + "~1";
    return ext ? base + "." + ext.slice(0, 3).toUpperCase() : base;
  }

  function shortPath(path) {
    if (!/^[A-Za-z]:\\/.test(path) || path.indexOf(" ") === -1) return null;
    var segs = path.split("\\");
    var changed = false;
    var out = segs.map(function (seg, i) {
      if (i === 0) return seg;
      var s = shortSegment(seg, i === segs.length - 1);
      if (s !== seg) changed = true;
      return s;
    });
    return changed ? out.join("\\") : null;
  }

  function build() {
    updateVisibility();
    var errors = [];
    var sc = els.sc.value;
    var monthly = sc === "MONTHLY";
    var mode = els.monthlyMode.value;

    var name = els.name.value.trim();
    if (!name) errors.push("task name is required");
    else if (name.indexOf('"') !== -1) errors.push('task name cannot contain "');

    var prog = els.prog.value.trim();
    if (!prog) errors.push("program to run is required");
    var args = els.args.value.trim();

    var sp = prog ? shortPath(prog) : null;
    show("st-row-short", !!sp);
    if (sp) {
      shortPathEl.textContent = sp;
      shortVerifyEl.textContent = 'for %I in ("' + prog + '") do @echo %~sI';
    }

    var moVisible = !$("st-row-mo").hidden;
    var mo = parseInt(els.mo.value, 10);
    if (moVisible && (!mo || mo < 1 || mo > MO_LIMITS[sc].max)) {
      errors.push("repeat interval must be 1-" + MO_LIMITS[sc].max + " for " +
        sc.toLowerCase() + " schedules");
    }

    var st = els.st.value;
    if (!$("st-row-st").hidden && !st) errors.push("start time is required");
    if (sc === "ONCE" && !els.sd.value) errors.push("start date is required for a one-time task");

    var idle = parseInt(els.idle.value, 10);
    if (sc === "ONIDLE" && (!idle || idle < 1 || idle > 999)) {
      errors.push("idle minutes must be 1-999");
    }

    var ruUser = els.ru.value === "custom" ? els.ruCustom.value.trim() : els.ru.value;
    if (els.ru.value === "custom" && !ruUser) errors.push("enter the account to run as");

    els.errors.hidden = errors.length === 0;
    els.errors.innerHTML = errors.map(function (e) {
      return "<div>✗ " + escapeHtml(e) + "</div>";
    }).join("");

    if (errors.length) {
      els.summary.hidden = true;
      els.output.textContent = "rem fix the highlighted fields to generate the command";
      return;
    }

    var parts = ["schtasks", "/create", '/tn "' + name + '"'];
    var trInner = (prog.indexOf(" ") !== -1 ? '\\"' + prog + '\\"' : prog) +
      (args ? " " + args : "");
    parts.push('/tr "' + trInner + '"');
    parts.push("/sc " + sc);

    var when = [];
    if (monthly && mode !== "DOM") {
      parts.push("/mo " + mode);
      if (mode === "LASTDAY") {
        when.push("on the last day of the month");
      } else {
        parts.push("/d " + els.dow.value);
        when.push("on the " + mode.toLowerCase() + " " + els.dow.value + " of the month");
      }
    } else if (moVisible) {
      parts.push("/mo " + mo);
      var unit = MO_LIMITS[sc].unit.replace("(s)", mo === 1 ? "" : "s");
      when.push(sc === "MONTHLY" ? "every " + mo + " " + unit : "every " + mo + " " + unit);
    }
    if (monthly && mode === "DOM") {
      parts.push("/d " + els.dom.value);
      when.push("on day " + els.dom.value);
    }
    if (sc === "WEEKLY") {
      var days = chipValues(els.days);
      if (days.length) {
        parts.push("/d " + days.join(","));
        when.push("on " + days.join(","));
      } else {
        when.push("on today's weekday (no /d given)");
      }
    }
    if (monthly) {
      var months = chipValues(els.months);
      if (months.length) {
        parts.push("/m " + months.join(","));
        when.push("in " + months.join(","));
      }
    }
    if (sc === "ONCE") {
      parts.push("/sd " + fmtDate(els.sd.value));
      when.push("once on " + fmtDate(els.sd.value));
    }
    if (!$("st-row-st").hidden && st) {
      parts.push("/st " + st);
      when.push("at " + st);
    }
    if (sc === "ONIDLE") {
      parts.push("/i " + idle);
      when.push("after " + idle + " idle minutes");
    }
    if (sc === "ONSTART") when.push("at system startup");
    if (sc === "ONLOGON") when.push("at logon");

    if (ruUser) parts.push('/ru "' + ruUser + '"');
    if (els.rl.value) parts.push("/rl " + els.rl.value);
    if (els.f.checked) parts.push("/f");

    els.output.textContent = parts.join(" ");
    els.summary.innerHTML = "Creates task <strong>" + escapeHtml(name) +
      "</strong> — runs <code>" + escapeHtml(prog) + (args ? " " + escapeHtml(args) : "") +
      "</code> " + escapeHtml(when.join(" ")) +
      (ruUser ? ", as <strong>" + escapeHtml(ruUser) + "</strong>" : "") +
      (els.rl.value ? ", with highest privileges" : "") +
      (els.f.checked ? ", replacing any existing task" : "") + ".";
    els.summary.hidden = false;
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".st-form input, .st-form select"),
    function (el) {
      el.addEventListener("input", build);
      el.addEventListener("change", build);
    });
  shortUseBtn.addEventListener("click", function () {
    els.prog.value = shortPathEl.textContent;
    build();
    els.prog.focus();
  });
  build();
})();
