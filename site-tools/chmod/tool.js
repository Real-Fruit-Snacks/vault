(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var octal = $("ch-octal");
  var symbolic = $("ch-symbolic");
  var error = $("ch-error");
  var warn = $("ch-warn");
  var output = $("ch-output");
  var lsEl = $("ch-ls");
  var boxes = document.querySelectorAll("#ch-grid input[data-bit]");
  var setuid = $("ch-setuid");
  var setgid = $("ch-setgid");
  var sticky = $("ch-sticky");
  if (!octal || !symbolic || !output) return;

  var syncing = false;

  // mode = 12-bit value: special (setuid 04000, setgid 02000, sticky 01000) + rwxrwxrwx
  function fromWidgets() {
    var mode = 0;
    boxes.forEach(function (b) { if (b.checked) mode |= parseInt(b.getAttribute("data-bit"), 10); });
    if (setuid.checked) mode |= 0x800;
    if (setgid.checked) mode |= 0x400;
    if (sticky.checked) mode |= 0x200;
    return mode;
  }

  function toWidgets(mode) {
    boxes.forEach(function (b) { b.checked = !!(mode & parseInt(b.getAttribute("data-bit"), 10)); });
    setuid.checked = !!(mode & 0x800);
    setgid.checked = !!(mode & 0x400);
    sticky.checked = !!(mode & 0x200);
  }

  function toOctal(mode) {
    var special = (mode >> 9) & 7;
    var body = ((mode >> 6) & 7).toString() + ((mode >> 3) & 7).toString() + (mode & 7).toString();
    return special ? special.toString() + body : body;
  }

  function toSymbolic(mode) {
    var s = "";
    var triads = [[8, 7, 6, 0x800, "s", "S"], [5, 4, 3, 0x400, "s", "S"], [2, 1, 0, 0x200, "t", "T"]];
    triads.forEach(function (t) {
      s += (mode & (1 << t[0])) ? "r" : "-";
      s += (mode & (1 << t[1])) ? "w" : "-";
      var x = !!(mode & (1 << t[2]));
      var sp = !!(mode & t[3]);
      s += sp ? (x ? t[4] : t[5]) : (x ? "x" : "-");
    });
    return s;
  }

  function parseOctal(text) {
    if (!/^[0-7]{3,4}$/.test(text)) {
      throw "octal mode must be 3 or 4 digits of 0-7";
    }
    var digits = text.split("").map(Number);
    var special = digits.length === 4 ? digits.shift() : 0;
    return (special << 9) | (digits[0] << 6) | (digits[1] << 3) | digits[2];
  }

  function parseSymbolic(text) {
    if (!/^[rwxsStT-]{9}$/.test(text)) {
      throw "symbolic form needs exactly 9 of r w x s S t T -";
    }
    var mode = 0;
    var specials = [0x800, 0x400, 0x200];
    for (var i = 0; i < 9; i++) {
      var c = text[i];
      var pos = 8 - i;
      var isXSlot = i % 3 === 2;
      if (c === "-") continue;
      if (c === "r" && i % 3 === 0) { mode |= 1 << pos; continue; }
      if (c === "w" && i % 3 === 1) { mode |= 1 << pos; continue; }
      if (isXSlot) {
        if (c === "x") { mode |= 1 << pos; continue; }
        var slot = Math.floor(i / 3);
        if ((c === "s" || c === "S") && slot < 2) {
          mode |= specials[slot];
          if (c === "s") mode |= 1 << pos;
          continue;
        }
        if ((c === "t" || c === "T") && slot === 2) {
          mode |= specials[2];
          if (c === "t") mode |= 1 << pos;
          continue;
        }
      }
      throw "'" + c + "' is not valid at position " + (i + 1) +
        " (columns are rwx for owner, group, others)";
    }
    return mode;
  }

  function describeWarnings(mode) {
    var notes = [];
    if (mode & 2) notes.push("world-writable — anyone on the system can modify this");
    if ((mode & 0x800) && (mode & 1)) notes.push("setuid + world-execute: runs with the owner's privileges for every user — classic privilege-escalation surface");
    if ((mode & 7) === 7) notes.push("others have full rwx");
    return notes;
  }

  function render(mode) {
    var oct = toOctal(mode);
    output.textContent = "chmod " + oct + " file";
    lsEl.textContent = "-" + toSymbolic(mode);
    var notes = describeWarnings(mode);
    warn.hidden = notes.length === 0;
    warn.textContent = notes.map(function (n) { return "⚠ " + n; }).join("  ");
  }

  function syncFrom(source) {
    if (syncing) return;
    syncing = true;
    error.hidden = true;
    try {
      var mode;
      if (source === "octal") {
        mode = parseOctal(octal.value.trim());
        toWidgets(mode);
        symbolic.value = toSymbolic(mode);
      } else if (source === "symbolic") {
        mode = parseSymbolic(symbolic.value.trim());
        toWidgets(mode);
        octal.value = toOctal(mode);
      } else {
        mode = fromWidgets();
        octal.value = toOctal(mode);
        symbolic.value = toSymbolic(mode);
      }
      render(mode);
    } catch (message) {
      error.textContent = "✗ " + message;
      error.hidden = false;
    }
    syncing = false;
  }

  octal.addEventListener("input", function () { syncFrom("octal"); });
  symbolic.addEventListener("input", function () { syncFrom("symbolic"); });
  boxes.forEach(function (b) { b.addEventListener("change", function () { syncFrom("widgets"); }); });
  [setuid, setgid, sticky].forEach(function (b) {
    b.addEventListener("change", function () { syncFrom("widgets"); });
  });
  Array.prototype.forEach.call(document.querySelectorAll(".ch-example"), function (btn) {
    btn.addEventListener("click", function () {
      octal.value = btn.getAttribute("data-octal");
      syncFrom("octal");
      octal.focus();
    });
  });
  syncFrom("octal");
})();
