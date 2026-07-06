(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var els = {
    iface: $("td-iface"), proto: $("td-proto"),
    hostdir: $("td-hostdir"), host: $("td-host"),
    portdir: $("td-portdir"), port: $("td-port"),
    net: $("td-net"), extra: $("td-extra"),
    verbose: $("td-verbose"), nn: $("td-nn"), A: $("td-A"), X: $("td-X"), e: $("td-e"), p: $("td-p"),
    count: $("td-count"), snap: $("td-snap"), write: $("td-write"),
    errors: $("td-errors"), notes: $("td-notes"), output: $("td-output"), filter: $("td-filter")
  };
  if (!els.iface || !els.output) return;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  // POSIX single-quote a filter or filename so the shell keeps it as one token.
  function q(s) {
    if (s === "") return "''";
    if (/^[A-Za-z0-9,._:@%+=\/-]+$/.test(s)) return s;
    return "'" + s.replace(/'/g, "'\\''") + "'";
  }

  function build() {
    var errors = [];
    var prims = [];

    if (els.proto.value) prims.push(els.proto.value);

    var host = els.host.value.trim();
    if (host) {
      if (!/^[A-Za-z0-9._:-]+$/.test(host)) errors.push("host has invalid characters");
      else prims.push(els.hostdir.value + " " + host);
    }

    var port = els.port.value.trim();
    if (port) {
      if (!/^\d+(-\d+)?$/.test(port)) {
        errors.push("port must be a number or range like 8000-8100");
      } else if (!port.split("-").every(function (p) {
        var n = parseInt(p, 10); return n >= 0 && n <= 65535;
      })) {
        errors.push("port must be within 0-65535");
      } else {
        prims.push(els.portdir.value + " " + port);
      }
    }

    var net = els.net.value.trim();
    if (net) {
      if (!/^[0-9A-Fa-f.:]+(\/\d{1,3})?$/.test(net)) errors.push("network must be an address or CIDR");
      else prims.push("net " + net);
    }

    var extra = els.extra.value.trim();
    if (extra) prims.push(extra);

    var filter = prims.join(" and ");

    var parts = ["tcpdump"];
    if (els.iface.value.trim()) parts.push("-i " + q(els.iface.value.trim()));
    if (els.nn.checked) parts.push("-nn");
    if (els.verbose.value) parts.push(els.verbose.value);
    if (els.e.checked) parts.push("-e");
    if (els.p.checked) parts.push("-p");
    if (els.A.checked) parts.push("-A");
    if (els.X.checked) parts.push("-X");

    var count = els.count.value.trim();
    if (count) {
      var cn = parseInt(count, 10);
      if (isNaN(cn) || cn < 1) errors.push("count must be a positive number");
      else parts.push("-c " + cn);
    }
    var snap = els.snap.value.trim();
    if (snap !== "") {
      var sn = parseInt(snap, 10);
      if (isNaN(sn) || sn < 0) errors.push("snaplen must be 0 or greater");
      else parts.push("-s " + sn);
    }
    var write = els.write.value.trim();
    if (write) parts.push("-w " + q(write));

    if (filter) parts.push(q(filter));

    els.errors.hidden = errors.length === 0;
    els.errors.innerHTML = errors.map(function (e) {
      return "<div>✗ " + escapeHtml(e) + "</div>";
    }).join("");
    if (errors.length) {
      els.notes.hidden = true;
      els.output.textContent = "# fix the highlighted fields";
      els.filter.textContent = "(invalid)";
      return;
    }

    els.output.textContent = parts.join(" ");
    els.filter.textContent = filter || "(no filter — captures everything)";

    if (els.p.checked) {
      // -p on: purely informational, neutral tone.
      els.notes.className = "td-notes td-info";
      els.notes.innerHTML = "<div>• <code>-p</code> disables promiscuous mode — the capture " +
        "sees only this host's own traffic plus broadcast and multicast. Uncheck it (and use a " +
        "mirror/SPAN port or a tap) to capture other hosts on the segment.</div>";
      els.notes.hidden = false;
    } else {
      // promiscuous mode active (the default): worth flagging as a warning.
      els.notes.className = "td-notes td-warn";
      els.notes.innerHTML = "<div>⚠ Promiscuous mode is <strong>on</strong> (tcpdump's " +
        "default): the interface captures every frame on the segment, not just this host's. " +
        "It needs elevated privilege and is noticeable on shared media. Add <code>-p</code> to " +
        "capture only this host's traffic.</div>";
      els.notes.hidden = false;
    }
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".td-form input, .td-form select"),
    function (el) {
      el.addEventListener("input", build);
      el.addEventListener("change", build);
    });
  build();
})();
