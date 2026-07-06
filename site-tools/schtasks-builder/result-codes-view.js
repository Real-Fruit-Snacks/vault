(function () {
  "use strict";
  var input = document.getElementById("rc-input");
  var famSel = document.getElementById("rc-fam");
  var sevSel = document.getElementById("rc-sev");
  var tbody = document.getElementById("rc-body");
  var count = document.getElementById("rc-count");
  var empty = document.getElementById("rc-empty");
  var CODES = window.TWB_TASK_CODES;
  if (!input || !tbody || !CODES) return;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // Normalise a hex code or query for matching: drop the 0x and leading zeros
  // so "0x00041303", "0x41303", and "41303" all compare equal. An all-zero
  // value collapses to "0".
  function normHex(s) {
    s = String(s).toLowerCase().replace(/^0x/, "").replace(/^0+/, "");
    return s === "" ? "0" : s;
  }
  CODES.forEach(function (e) { e._nc = normHex(e.code); });

  function render(list) {
    if (!list.length) {
      tbody.innerHTML = "";
      empty.hidden = false;
      count.textContent = "0 of " + CODES.length + " codes";
      return;
    }
    empty.hidden = true;
    tbody.innerHTML = list.map(function (e) {
      var nameCell = e.name
        ? '<span class="rc-const">' + escapeHtml(e.name) + "</span>"
        : '<span class="rc-generic">' +
          (e.fam === "exit" ? "program exit code" : "") + "</span>";
      var fix = e.fix
        ? '<span class="rc-fix">' + escapeHtml(e.fix) + "</span>" : "";
      return '<tr class="rc-row">' +
        '<td class="rc-code">' + escapeHtml(e.code) + "</td>" +
        '<td class="rc-name">' + nameCell + "</td>" +
        '<td class="rc-meaning">' + escapeHtml(e.desc) + fix + "</td>" +
        '<td><span class="rc-sev rc-sev-' + e.sev + '">' + e.sev + "</span></td>" +
        "</tr>";
    }).join("");
    count.textContent = list.length + " of " + CODES.length + " codes";
  }

  function matches(e, q, nq, fam, sev) {
    if (fam && e.fam !== fam) return false;
    if (sev && e.sev !== sev) return false;
    if (!q) return true;
    if (e._nc.indexOf(nq) === 0) return true;                // code prefix
    // Keyword search: every whitespace-separated token must appear somewhere,
    // in any order, so "access denied" still finds "Access is denied".
    var hay = (e.code + " " + e.name + " " + e.desc + " " + e.fix).toLowerCase();
    return q.split(/\s+/).every(function (t) { return hay.indexOf(t) !== -1; });
  }

  function apply() {
    var q = input.value.trim().toLowerCase();
    var nq = normHex(q);
    var fam = famSel.value, sev = sevSel.value;
    render(CODES.filter(function (e) { return matches(e, q, nq, fam, sev); }));
  }

  input.addEventListener("input", apply);
  famSel.addEventListener("change", apply);
  sevSel.addEventListener("change", apply);
  render(CODES);
})();
