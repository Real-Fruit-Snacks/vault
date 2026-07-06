(function () {
  "use strict";
  var input = document.getElementById("we-input");
  var channelSel = document.getElementById("we-channel");
  var catSel = document.getElementById("we-cat");
  var critSel = document.getElementById("we-crit");
  var tbody = document.getElementById("we-body");
  var count = document.getElementById("we-count");
  var empty = document.getElementById("we-empty");
  var EVENTS = window.TWB_WIN_EVENTS;
  if (!input || !tbody || !EVENTS) return;

  var CAT_LABEL = {
    logon: "logon / logoff", kerberos: "kerberos", account: "account mgmt",
    process: "process", object: "object access", share: "file share",
    policy: "policy / audit", task: "scheduled tasks", service: "services",
    system: "system", powershell: "powershell", sysmon: "sysmon",
    defender: "defender", rdp: "rdp / terminal", applocker: "applocker",
    firewall: "firewall", wmi: "wmi"
  };
  // Short channel labels for the compact table column.
  function shortChannel(log) {
    if (log.indexOf("/") === -1) return log;               // Security, System, Application
    if (log === "Windows PowerShell") return log;
    var m = log.match(/^Microsoft-Windows-([^/]+)\//);
    return m ? m[1] : log;
  }

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  // --- populate the filter dropdowns from the data ---
  var channels = [];
  var seenCh = {};
  var cats = [];
  var seenCat = {};
  EVENTS.forEach(function (e) {
    if (!seenCh[e.log]) { seenCh[e.log] = true; channels.push(e.log); }
    if (!seenCat[e.cat]) { seenCat[e.cat] = true; cats.push(e.cat); }
  });
  channels.sort();
  cats.sort(function (a, b) { return CAT_LABEL[a].localeCompare(CAT_LABEL[b]); });

  channelSel.innerHTML = '<option value="">any channel</option>' +
    channels.map(function (c) {
      return '<option value="' + escapeHtml(c) + '">' + escapeHtml(shortChannel(c)) + "</option>";
    }).join("");
  catSel.innerHTML = '<option value="">any category</option>' +
    cats.map(function (c) {
      return '<option value="' + c + '">' + escapeHtml(CAT_LABEL[c]) + "</option>";
    }).join("");

  function subTable(sub) {
    var head = "<tr>" + sub.cols.map(function (c) {
      return "<th>" + escapeHtml(c) + "</th>";
    }).join("") + "</tr>";
    var body = sub.rows.map(function (r) {
      return "<tr>" + r.map(function (cell) {
        return "<td>" + escapeHtml(cell) + "</td>";
      }).join("") + "</tr>";
    }).join("");
    return '<div class="we-sub"><div class="we-sub-label manifest-label">' +
      escapeHtml(sub.label) + "</div><table class=\"we-subtable\"><thead>" +
      head + "</thead><tbody>" + body + "</tbody></table></div>";
  }

  function detailRow(e, span) {
    var parts = ['<tr class="we-detail" hidden><td colspan="' + span + '">'];
    parts.push('<div class="we-detail-body">');
    parts.push("<p>" + escapeHtml(e.desc) + "</p>");
    if (e.sec) {
      parts.push('<p class="we-sec"><span class="manifest-label">security relevance</span> ' +
        escapeHtml(e.sec) + "</p>");
    }
    if (e.sub) parts.push(subTable(e.sub));
    parts.push('<div class="we-query">');
    parts.push('<code>' + escapeHtml(e.query) + "</code>");
    parts.push('<button type="button" class="we-copy" aria-label="Copy query">copy</button>');
    parts.push("</div>");
    parts.push('<p class="we-full-channel"><span class="manifest-label">channel</span> ' +
      escapeHtml(e.log) + "</p>");
    parts.push("</div></td></tr>");
    return parts.join("");
  }

  var SPAN = 5;

  function render(list) {
    if (!list.length) {
      tbody.innerHTML = "";
      empty.hidden = false;
      count.textContent = "0 of " + EVENTS.length + " events";
      return;
    }
    empty.hidden = true;
    tbody.innerHTML = list.map(function (e) {
      var main = '<tr class="we-row" tabindex="0">' +
        '<td class="we-id">' + e.id + "</td>" +
        '<td class="we-chan">' + escapeHtml(shortChannel(e.log)) + "</td>" +
        '<td><span class="we-cat we-cat-' + e.cat + '">' + escapeHtml(CAT_LABEL[e.cat]) + "</span></td>" +
        "<td>" + escapeHtml(e.title) + "</td>" +
        '<td><span class="we-crit we-crit-' + e.crit + '">' + e.crit + "</span></td>" +
        "</tr>";
      return main + detailRow(e, SPAN);
    }).join("");
    count.textContent = list.length + " of " + EVENTS.length + " events";
  }

  function matches(e, q, ch, cat, crit) {
    if (ch && e.log !== ch) return false;
    if (cat && e.cat !== cat) return false;
    if (crit && e.crit !== crit) return false;
    if (!q) return true;
    if (String(e.id).indexOf(q) === 0) return true;
    var hay = (e.title + " " + e.desc + " " + (e.sec || "") + " " +
      CAT_LABEL[e.cat] + " " + e.log).toLowerCase();
    if (e.sub) {
      hay += " " + e.sub.rows.map(function (r) { return r.join(" "); }).join(" ").toLowerCase();
    }
    return hay.indexOf(q) !== -1;
  }

  function apply() {
    var q = input.value.trim().toLowerCase();
    var ch = channelSel.value, cat = catSel.value, crit = critSel.value;
    render(EVENTS.filter(function (e) { return matches(e, q, ch, cat, crit); }));
  }

  // Row expand/collapse via event delegation.
  function toggle(row) {
    var detail = row.nextElementSibling;
    if (!detail || detail.className.indexOf("we-detail") === -1) return;
    var open = !detail.hidden;
    detail.hidden = open;
    row.classList.toggle("we-open", !open);
  }

  tbody.addEventListener("click", function (ev) {
    var copy = ev.target.closest(".we-copy");
    if (copy) {
      var code = copy.parentNode.querySelector("code");
      if (code) copyText(code.textContent, copy);
      return;
    }
    var row = ev.target.closest(".we-row");
    if (row) toggle(row);
  });
  tbody.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter" && ev.key !== " ") return;
    var row = ev.target.closest(".we-row");
    if (row) { ev.preventDefault(); toggle(row); }
  });

  function flash(btn, ok) {
    var label = btn.getAttribute("data-label") || btn.textContent;
    btn.setAttribute("data-label", label);
    btn.textContent = ok ? "copied" : "failed";
    setTimeout(function () { btn.textContent = label; }, 1400);
  }
  function legacyCopy(text, btn) {
    var ta = document.createElement("textarea");
    ta.value = text; ta.style.position = "fixed"; ta.style.opacity = "0";
    document.body.appendChild(ta); ta.select();
    var ok = false;
    try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
    document.body.removeChild(ta);
    flash(btn, ok);
  }
  function copyText(text, btn) {
    // Clipboard API on secure contexts; execCommand fallback for plain-http
    // internal hosts where navigator.clipboard is unavailable.
    if (navigator.clipboard && window.isSecureContext) {
      navigator.clipboard.writeText(text).then(function () { flash(btn, true); },
        function () { legacyCopy(text, btn); });
    } else {
      legacyCopy(text, btn);
    }
  }

  input.addEventListener("input", apply);
  channelSel.addEventListener("change", apply);
  catSel.addEventListener("change", apply);
  critSel.addEventListener("change", apply);
  render(EVENTS);
})();
