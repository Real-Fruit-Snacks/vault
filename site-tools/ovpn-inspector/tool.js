(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var input = $("ov-input");
  var fileInput = $("ov-file");
  var fileName = $("ov-filename");
  var error = $("ov-error");
  var summary = $("ov-summary");
  var flagsEl = $("ov-flags");
  var certsEl = $("ov-certs");
  var configWrap = $("ov-config-wrap");
  var configEl = $("ov-config");
  if (!input || !certsEl) return;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function b64ToBytes(b64) {
    var bin = atob(b64.replace(/\s+/g, ""));
    var out = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) out[i] = bin.charCodeAt(i);
    return out;
  }

  // Pull PEM blocks (both standalone and inside <ca>/<cert> tags share the same markers).
  function extractPem(text, label) {
    var re = new RegExp("-----BEGIN " + label +
      "-----([\\s\\S]*?)-----END " + label + "-----", "g");
    var blocks = [], m;
    while ((m = re.exec(text)) !== null) blocks.push(m[1]);
    return blocks;
  }

  function dn(parts) {
    return parts.map(function (p) { return p.key + "=" + p.value; }).join(", ");
  }
  function cn(parts) {
    var c = parts.filter(function (p) { return p.key === "CN"; })[0];
    return c ? c.value : dn(parts);
  }

  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function fmtDate(d) {
    if (!d) return "—";
    return d.getUTCFullYear() + "-" + pad(d.getUTCMonth() + 1) + "-" + pad(d.getUTCDate()) +
      " " + pad(d.getUTCHours()) + ":" + pad(d.getUTCMinutes()) + " UTC";
  }
  function fmtLocal(d) {
    if (!d) return "";
    return d.getFullYear() + "-" + pad(d.getMonth() + 1) + "-" + pad(d.getDate()) +
      " " + pad(d.getHours()) + ":" + pad(d.getMinutes()) + " local";
  }

  function expiryStatus(cert) {
    var now = Date.now();
    if (cert.notBefore && now < cert.notBefore.getTime()) {
      return { cls: "ov-bad", text: "not yet valid" };
    }
    if (!cert.notAfter) return { cls: "ov-dim", text: "no expiry date" };
    var days = Math.floor((cert.notAfter.getTime() - now) / 86400000);
    if (days < 0) return { cls: "ov-bad", text: "expired " + (-days) + " day" + (-days === 1 ? "" : "s") + " ago" };
    if (days < 30) return { cls: "ov-bad", text: "expires in " + days + " day" + (days === 1 ? "" : "s") };
    if (days < 90) return { cls: "ov-warn", text: days + " days left" };
    return { cls: "ov-good", text: days + " days left" };
  }

  function certRole(cert) {
    if (cert.extensions.isCA) return "certificate authority";
    var eku = cert.extensions.eku || [];
    if (eku.indexOf("serverAuth") !== -1) return "server certificate";
    if (eku.indexOf("clientAuth") !== -1) return "client certificate";
    return "certificate";
  }

  function row(label, value) {
    if (!value) return "";
    return '<tr><td>' + label + '</td><td class="ov-mono">' + value + "</td></tr>";
  }

  function renderCert(cert, index, tagLabel) {
    var status = expiryStatus(cert);
    var role = certRole(cert);
    var sigWarn = /sha1|md5/i.test(cert.signatureAlgorithm)
      ? ' <span class="ov-inline-warn">weak signature</span>' : "";
    var card = document.createElement("div");
    card.className = "ov-card";
    card.innerHTML =
      '<div class="ov-card-head">' +
        '<div><span class="ov-card-cn">' + escapeHtml(cn(cert.subject)) + "</span>" +
        '<span class="ov-card-role manifest-label">' + (tagLabel ? tagLabel + " · " : "") + role + "</span></div>" +
        '<span class="ov-badge ' + status.cls + '">' + status.text + "</span>" +
      "</div>" +
      '<table class="ov-card-table"><tbody>' +
        row("valid from", escapeHtml(fmtDate(cert.notBefore)) + ' <span class="ov-dim">' + escapeHtml(fmtLocal(cert.notBefore)) + "</span>") +
        row("valid until", escapeHtml(fmtDate(cert.notAfter)) + ' <span class="ov-dim">' + escapeHtml(fmtLocal(cert.notAfter)) + "</span>") +
        row("subject", escapeHtml(dn(cert.subject))) +
        row("issuer", escapeHtml(dn(cert.issuer))) +
        row("serial", escapeHtml(cert.serial)) +
        row("signature", escapeHtml(cert.signatureAlgorithm) + sigWarn) +
        row("public key", escapeHtml(cert.publicKey.label)) +
        row("basic constraints", cert.extensions.isCA
          ? "CA:TRUE" + (cert.extensions.pathLen != null ? ", pathlen:" + cert.extensions.pathLen : "")
          : "CA:FALSE") +
        row("key usage", cert.extensions.keyUsage ? escapeHtml(cert.extensions.keyUsage.join(", ")) : "") +
        row("extended key usage", cert.extensions.eku ? escapeHtml(cert.extensions.eku.join(", ")) : "") +
        row("subject alt names", cert.extensions.san ? escapeHtml(cert.extensions.san.join(", ")) : "") +
        '<tr><td>sha-256 fingerprint</td><td class="ov-mono ov-fp" id="ov-fp-' + index + '">computing…</td></tr>' +
      "</tbody></table>";
    certsEl.appendChild(card);
    cert.fingerprintPromise.then(function (fp) {
      var el = $("ov-fp-" + index);
      if (el) el.textContent = fp || "(unavailable)";
    });
    return { status: status, role: role };
  }

  // --- config directive parsing ---
  function parseConfig(text) {
    var directives = {};
    var lines = text.split(/\r?\n/);
    var inBlock = false;
    lines.forEach(function (raw) {
      var line = raw.trim();
      if (/^<\/?[a-z-]+>$/i.test(line)) { inBlock = /^<[a-z]/i.test(line); return; }
      if (inBlock || !line || line[0] === "#" || line[0] === ";") return;
      var sp = line.indexOf(" ");
      var key = (sp === -1 ? line : line.slice(0, sp)).toLowerCase();
      var val = sp === -1 ? "" : line.slice(sp + 1).trim();
      if (!directives[key]) directives[key] = [];
      directives[key].push(val);
    });
    return directives;
  }

  var CONFIG_ROWS = [
    ["remote", "remote(s)"], ["proto", "protocol"], ["port", "port"],
    ["dev", "device"], ["cipher", "cipher"], ["data-ciphers", "data ciphers"],
    ["auth", "auth digest"], ["tls-version-min", "min TLS"],
    ["remote-cert-tls", "server cert check"], ["auth-user-pass", "user/pass auth"],
    ["comp-lzo", "compression"], ["compress", "compression"]
  ];

  function analyzeSecurity(directives, certStatuses, isConfig) {
    var flags = [];
    if (isConfig) {
      if (directives["comp-lzo"] || directives["compress"]) {
        flags.push("<code>comp-lzo</code>/<code>compress</code> is set — compression enables the VORACLE attack; modern OpenVPN disables it by default");
      }
      var cipher = (directives.cipher || []).join(" ").toUpperCase();
      if (/BF-CBC/.test(cipher)) flags.push("<code>cipher BF-CBC</code> (Blowfish) is deprecated and vulnerable to SWEET32 — use AES-256-GCM");
      if (/DES/.test(cipher)) flags.push("<code>cipher</code> uses DES — cryptographically broken");
      var auth = (directives.auth || []).join(" ").toUpperCase();
      if (/^(MD5|SHA1)\b/.test(auth) || auth === "SHA1" || auth === "MD5") {
        flags.push("<code>auth " + escapeHtml((directives.auth || [])[0]) + "</code> is a weak HMAC digest — prefer SHA256 or better");
      }
      if (!directives["tls-version-min"]) {
        flags.push("no <code>tls-version-min</code> — pin it to <code>1.2</code> (or 1.3) to refuse legacy TLS");
      }
      if (directives.client && !directives["remote-cert-tls"] && !directives["remote-cert-eku"]) {
        flags.push("no <code>remote-cert-tls server</code> — without it a client can be tricked into trusting another client's cert as a server");
      }
    }
    certStatuses.forEach(function (s) {
      if (s.status.cls === "ov-bad") {
        flags.push("a " + s.role + " " + s.status.text + " — connections will fail until it is renewed");
      } else if (s.status.cls === "ov-warn") {
        flags.push("a " + s.role + " has " + s.status.text + " — plan renewal");
      }
    });
    return flags;
  }

  function analyze() {
    var text = input.value;
    error.hidden = true;
    summary.hidden = true;
    flagsEl.hidden = true;
    flagsEl.innerHTML = "";
    configWrap.hidden = true;
    configEl.innerHTML = "";
    certsEl.innerHTML = "";
    if (!text.trim()) return;

    var certBlocks = extractPem(text, "CERTIFICATE");
    var keyBlocks = extractPem(text, "(?:RSA |EC |ENCRYPTED |)PRIVATE KEY");
    var taBlocks = /BEGIN OpenVPN Static key/.test(text) ||
      (text.indexOf("<tls-auth>") !== -1 || text.indexOf("<tls-crypt>") !== -1);

    if (!certBlocks.length && !keyBlocks.length) {
      error.textContent = "✗ no PEM certificate or key blocks found — paste an .ovpn file or a -----BEGIN CERTIFICATE----- block";
      error.hidden = false;
      return;
    }

    var certs = [];
    certBlocks.forEach(function (b64) {
      try { certs.push(window.parseCertificate(b64ToBytes(b64))); }
      catch (err) { /* skip unparseable block, reported in summary */ }
    });

    var statuses = [];
    certs.forEach(function (c, i) { statuses.push(renderCert(c, i, null)); });

    var directives = parseConfig(text);
    var isConfig = !!(directives.client || directives.remote || directives.dev ||
      directives.proto || directives.server || directives["remote-cert-tls"]);

    summary.innerHTML =
      '<span class="ov-chip"><span class="manifest-label">certificates</span>' + certs.length + "</span>" +
      '<span class="ov-chip"><span class="manifest-label">private keys</span>' + keyBlocks.length + "</span>" +
      '<span class="ov-chip"><span class="manifest-label">tls-auth key</span>' + (taBlocks ? "yes" : "no") + "</span>" +
      (certBlocks.length > certs.length
        ? '<span class="ov-chip ov-chip-bad"><span class="manifest-label">unparsed</span>' + (certBlocks.length - certs.length) + "</span>" : "");
    summary.hidden = false;

    if (isConfig) {
      var rows = [];
      CONFIG_ROWS.forEach(function (pair) {
        var vals = directives[pair[0]];
        if (vals && vals.length) {
          rows.push('<tr><td>' + pair[1] + '</td><td class="ov-mono">' +
            escapeHtml(vals.join(" · ") || "(enabled)") + "</td></tr>");
        }
      });
      if (keyBlocks.length) {
        rows.push('<tr><td>private key</td><td class="ov-mono ov-dim">present — not displayed</td></tr>');
      }
      configEl.innerHTML = rows.join("");
      configWrap.hidden = rows.length === 0;
    }

    var flags = analyzeSecurity(directives, statuses, isConfig);
    if (flags.length) {
      flagsEl.innerHTML = '<div class="manifest-label ov-caption">security notes</div>' +
        flags.map(function (f) { return '<div class="ov-flag">⚠ ' + f + "</div>"; }).join("");
      flagsEl.hidden = false;
    }
  }

  input.addEventListener("input", analyze);
  Array.prototype.forEach.call(document.querySelectorAll(".ov-example"), function (btn) {
    btn.addEventListener("click", function () {
      var samples = window.OV_SAMPLES || {};
      var text = samples[btn.getAttribute("data-sample")];
      if (text == null) return;
      input.value = text;
      fileName.textContent = "";
      analyze();
      input.scrollTop = 0;
    });
  });
  fileInput.addEventListener("change", function () {
    var file = fileInput.files[0];
    if (!file) return;
    fileName.textContent = file.name;
    var reader = new FileReader();
    reader.onload = function () { input.value = reader.result; analyze(); };
    reader.readAsText(file);
  });
})();
