(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var els = {
    targets: $("nm-targets"), scan: $("nm-scan"), ports: $("nm-ports"),
    topn: $("nm-topn"), portspec: $("nm-portspec"),
    sv: $("nm-sv"), o: $("nm-o"), sc: $("nm-sc"), a: $("nm-a"), script: $("nm-script"),
    pn: $("nm-pn"), n: $("nm-n"), six: $("nm-6"),
    timing: $("nm-timing"), open: $("nm-open"), v: $("nm-v"), reason: $("nm-reason"),
    output: $("nm-output"), outfile: $("nm-outfile"),
    rowPorts: $("nm-row-ports"), rowDetect: $("nm-row-detect"), rowScript: $("nm-row-script"),
    errors: $("nm-errors"), summary: $("nm-summary"), cmd: $("nm-output-cmd"), notes: $("nm-notes")
  };
  if (!els.targets || !els.cmd) return;

  // name = human label; root = needs raw-socket privileges; noports = a host/list
  // scan with no port phase; slow flags the UDP scan for a caution note.
  var SCANS = {
    "-sS": { name: "TCP SYN", root: true },
    "-sT": { name: "TCP connect", root: false },
    "-sU": { name: "UDP", root: true, slow: true },
    "-sA": { name: "TCP ACK", root: true },
    "-sF": { name: "TCP FIN", root: true },
    "-sX": { name: "Xmas", root: true },
    "-sN": { name: "TCP Null", root: true },
    "-sn": { name: "ping sweep", root: false, noports: true },
    "-sL": { name: "list", root: false, noports: true }
  };

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  // Shell-quote a single argument (script spec, output filename). Targets are
  // never quoted — nmap splits them on whitespace into multiple hosts.
  function quoteArg(s) {
    return /[^A-Za-z0-9,._:\/@=*+-]/.test(s) ? '"' + s.replace(/(["\\])/g, "\\$1") + '"' : s;
  }
  function timingLabel() {
    return els.timing.options[els.timing.selectedIndex].text.replace(/\s*\(.*\)/, "");
  }

  function updateVisibility() {
    var scan = SCANS[els.scan.value] || {};
    var noports = !!scan.noports;
    els.rowPorts.hidden = noports;
    els.rowDetect.hidden = noports;
    els.rowScript.hidden = noports;
    els.topn.hidden = els.ports.value !== "top";
    els.portspec.hidden = els.ports.value !== "spec";
    els.outfile.hidden = !els.output.value;
    // -A subsumes -sV, -O and -sC, so grey them out while it's on.
    var aggressive = els.a.checked && !noports;
    [els.sv, els.o, els.sc].forEach(function (cb) { cb.disabled = aggressive; });
  }

  function build() {
    updateVisibility();
    var errors = [];
    var notes = [];
    var scanVal = els.scan.value;
    var scan = SCANS[scanVal] || {};
    var noports = !!scan.noports;
    var aggressive = els.a.checked && !noports;

    var targets = els.targets.value.trim();
    if (!targets) errors.push("at least one target is required");

    var parts = ["nmap", scanVal];

    if (!noports) {
      var pv = els.ports.value;
      if (pv === "-F" || pv === "-p-") {
        parts.push(pv);
      } else if (pv === "top") {
        var n = parseInt(els.topn.value, 10);
        if (!n || n < 1 || n > 65535) errors.push("top-ports count must be 1–65535");
        else parts.push("--top-ports " + n);
      } else if (pv === "spec") {
        var spec = els.portspec.value.trim().replace(/\s+/g, "");
        if (!spec) errors.push("enter a port list for the -p option");
        else if (!/^[0-9TUS,:*()\/-]+$/i.test(spec)) errors.push("port list has invalid characters");
        else parts.push("-p " + spec);
      }

      if (aggressive) {
        parts.push("-A");
      } else {
        if (els.sv.checked) parts.push("-sV");
        if (els.o.checked) parts.push("-O");
        if (els.sc.checked) parts.push("-sC");
      }
      var script = els.script.value.trim();
      if (script) parts.push("--script " + quoteArg(script));
    }

    if (els.pn.checked && !noports) parts.push("-Pn");
    if (els.n.checked) parts.push("-n");
    if (els.six.checked) parts.push("-6");
    if (els.timing.value) parts.push(els.timing.value);
    if (!noports && els.open.checked) parts.push("--open");
    if (els.v.checked) parts.push("-v");
    if (!noports && els.reason.checked) parts.push("--reason");

    if (els.output.value) {
      var of = els.outfile.value.trim();
      if (!of) errors.push("enter a filename for the output option");
      else parts.push(els.output.value + " " + quoteArg(of));
    }

    if (targets) parts.push(targets);

    els.errors.hidden = errors.length === 0;
    els.errors.innerHTML = errors.map(function (e) {
      return "<div>✗ " + escapeHtml(e) + "</div>";
    }).join("");
    if (errors.length) {
      els.summary.hidden = true;
      els.notes.hidden = true;
      els.cmd.textContent = "# fix the highlighted fields to generate the command";
      return;
    }

    els.cmd.textContent = parts.join(" ");

    // --- plain-language summary ---
    var portDesc;
    if (noports) {
      portDesc = "";
    } else {
      var pv2 = els.ports.value;
      portDesc = pv2 === "-F" ? "the top 100 ports"
        : pv2 === "-p-" ? "all 65,535 ports"
        : pv2 === "top" ? "the top " + parseInt(els.topn.value, 10) + " ports"
        : pv2 === "spec" ? "ports " + escapeHtml(els.portspec.value.trim().replace(/\s+/g, ""))
        : "the top 1,000 ports";
    }
    var dets = [];
    if (!noports) {
      if (aggressive) dets.push("aggressive detection (-A: versions, OS, default scripts, traceroute)");
      else {
        if (els.sv.checked) dets.push("service versions");
        if (els.o.checked) dets.push("OS fingerprint");
        if (els.sc.checked) dets.push("default NSE scripts");
      }
      if (els.script.value.trim()) dets.push("NSE " + escapeHtml(els.script.value.trim()));
    }
    var intro = scanVal === "-sn" ? "Discovers live hosts in "
      : scanVal === "-sL" ? "Lists (without scanning) "
      : "Scans ";
    els.summary.innerHTML = intro + "<strong>" + escapeHtml(targets) + "</strong>" +
      (noports ? "" : " with a <strong>" + scan.name + "</strong> scan across " + portDesc) +
      (dets.length ? ", detecting " + dets.join(", ") : "") +
      (els.timing.value ? ", at " + timingLabel() + " speed" : "") + ".";
    els.summary.hidden = false;

    // --- privilege / caution notes ---
    if (scan.root) {
      notes.push("The " + scan.name + " scan sends raw packets, so it needs " +
        "<strong>root / administrator</strong> privileges — run it with <code>sudo</code>.");
    }
    if (els.o.checked && !aggressive) {
      notes.push("<code>-O</code> OS detection also requires root privileges.");
    }
    if (aggressive) {
      notes.push("<code>-A</code> requires root and is loud — it is easily spotted and logged " +
        "by the target.");
    }
    if (scan.slow) {
      notes.push("UDP scans are slow because closed ports rely on ICMP rate limits — narrow the " +
        "port list where you can.");
    }
    if (!noports && els.ports.value === "-p-") {
      notes.push("Scanning all 65,535 ports takes far longer than the default 1,000.");
    }
    if (els.timing.value === "-T5") {
      notes.push("<code>-T5</code> (insane) can overwhelm hosts and drop results — reserve it for " +
        "fast, reliable LANs.");
    }
    els.notes.hidden = notes.length === 0;
    els.notes.innerHTML = notes.map(function (n) { return "<div>• " + n + "</div>"; }).join("");
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".nm-form input, .nm-form select"),
    function (el) {
      el.addEventListener("input", build);
      el.addEventListener("change", build);
    });
  build();
})();
