(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var input = $("ip-input");
  var error = $("ip-error");
  var note = $("ip-note");
  var classRow = $("ip-class-row");
  var classBadge = $("ip-class");
  var binaryBlock = $("ip-binary-block");
  var binary = $("ip-binary");
  var tableWrap = $("ip-table-wrap");
  var tbody = $("ip-body");
  if (!input || !tbody) return;

  function parseOctets(s) {
    var parts = s.split(".");
    if (parts.length !== 4) return null;
    var value = 0;
    for (var i = 0; i < 4; i++) {
      if (!/^\d{1,3}$/.test(parts[i])) return null;
      var octet = parseInt(parts[i], 10);
      if (octet > 255) return null;
      value = ((value << 8) | octet) >>> 0;
    }
    return value;
  }

  function toIP(value) {
    return [(value >>> 24) & 255, (value >>> 16) & 255,
            (value >>> 8) & 255, value & 255].join(".");
  }

  function prefixToMask(p) {
    return p === 0 ? 0 : (0xFFFFFFFF << (32 - p)) >>> 0;
  }

  function maskToPrefix(mask) {
    for (var p = 0; p <= 32; p++) {
      if (prefixToMask(p) === mask) return p;
    }
    return null;
  }

  // Most-specific-first special ranges. [cidr, label, badge class]
  var RANGES = [
    ["255.255.255.255/32", "limited broadcast", "reserved"],
    ["192.0.2.0/24", "documentation (TEST-NET-1)", "special"],
    ["198.51.100.0/24", "documentation (TEST-NET-2)", "special"],
    ["203.0.113.0/24", "documentation (TEST-NET-3)", "special"],
    ["169.254.0.0/16", "link-local / APIPA (RFC 3927)", "special"],
    ["192.168.0.0/16", "private (RFC 1918)", "private"],
    ["198.18.0.0/15", "benchmarking (RFC 2544)", "special"],
    ["172.16.0.0/12", "private (RFC 1918)", "private"],
    ["100.64.0.0/10", "carrier-grade NAT (RFC 6598)", "special"],
    ["0.0.0.0/8", "“this network” (RFC 791)", "special"],
    ["10.0.0.0/8", "private (RFC 1918)", "private"],
    ["127.0.0.0/8", "loopback", "loopback"],
    ["224.0.0.0/4", "multicast (RFC 5771)", "multicast"],
    ["240.0.0.0/4", "reserved for future use (RFC 1112)", "reserved"]
  ].map(function (r) {
    var bits = r[0].split("/");
    var p = parseInt(bits[1], 10);
    return { net: parseOctets(bits[0]), mask: prefixToMask(p), label: r[1], cls: r[2] };
  });

  function classify(ip) {
    for (var i = 0; i < RANGES.length; i++) {
      if (((ip & RANGES[i].mask) >>> 0) === RANGES[i].net) {
        return { label: RANGES[i].label, cls: RANGES[i].cls };
      }
    }
    return { label: "public (globally routable)", cls: "public" };
  }

  function parse(text) {
    var raw = text.trim().replace(/\s+/g, " ");
    if (!raw) return null;
    var ip, prefix, bare = false;
    if (raw.indexOf("/") !== -1) {
      var cp = raw.split("/");
      if (cp.length !== 2) throw "only one '/' allowed";
      ip = parseOctets(cp[0].trim());
      if (ip === null) throw "'" + cp[0].trim() + "' is not a valid IPv4 address";
      if (!/^\d{1,2}$/.test(cp[1].trim())) throw "prefix '/" + cp[1].trim() + "' must be 0-32";
      prefix = parseInt(cp[1].trim(), 10);
      if (prefix > 32) throw "prefix /" + prefix + " is out of range 0-32";
    } else if (raw.indexOf(" ") !== -1) {
      var mp = raw.split(" ");
      if (mp.length !== 2) throw "expected 'address netmask'";
      ip = parseOctets(mp[0]);
      if (ip === null) throw "'" + mp[0] + "' is not a valid IPv4 address";
      var mask = parseOctets(mp[1]);
      if (mask === null) throw "'" + mp[1] + "' is not a valid netmask";
      prefix = maskToPrefix(mask);
      if (prefix === null) {
        throw "'" + mp[1] + "' is not a contiguous netmask (its binary form mixes 1s and 0s)";
      }
    } else {
      ip = parseOctets(raw);
      if (ip === null) throw "'" + raw + "' is not a valid IPv4 address";
      prefix = 32;
      bare = true;
    }
    return { ip: ip, prefix: prefix, bare: bare };
  }

  function renderBinary(ip, prefix) {
    var groups = [];
    for (var o = 0; o < 4; o++) {
      var bits = [];
      for (var b = 0; b < 8; b++) {
        var idx = o * 8 + b;
        if (idx === prefix) bits.push('<span class="ip-boundary"></span>');
        var bit = (ip >>> (31 - idx)) & 1;
        var cls = idx < prefix ? "ip-bit-net" : "ip-bit-host";
        bits.push('<span class="ip-bit ' + cls + '">' + bit + "</span>");
      }
      groups.push('<div class="ip-octet"><div class="ip-bits">' + bits.join("") +
        '</div><span class="manifest-label">' + ((ip >>> (24 - o * 8)) & 255) +
        "</span></div>");
    }
    return groups.join("");
  }

  function row(label, value, extra) {
    return "<tr><td>" + label + '</td><td class="ip-mono">' + value +
      (extra ? ' <span class="ip-dim">' + extra + "</span>" : "") + "</td></tr>";
  }

  function analyze() {
    error.hidden = true;
    note.hidden = true;
    classRow.hidden = true;
    binaryBlock.hidden = true;
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
    note.hidden = !result.bare;

    var ip = result.ip;
    var p = result.prefix;
    var mask = prefixToMask(p);
    var network = (ip & mask) >>> 0;
    var broadcast = (network | (~mask >>> 0)) >>> 0;
    var total = Math.pow(2, 32 - p);

    var kind = classify(ip);
    classBadge.textContent = kind.label;
    classBadge.className = "ip-badge ip-" + kind.cls;
    classRow.hidden = false;

    binary.innerHTML = renderBinary(ip, p);
    binaryBlock.hidden = false;

    var rows = [
      row("address", toIP(ip)),
      row("cidr", toIP(network) + "/" + p),
      row("netmask", toIP(mask), "/" + p),
      row("wildcard mask", toIP(~mask >>> 0), "for router ACLs")
    ];
    if (p <= 30) {
      rows.push(row("network", toIP(network)));
      rows.push(row("broadcast", toIP(broadcast)));
      rows.push(row("first host", toIP(network + 1)));
      rows.push(row("last host", toIP(broadcast - 1)));
      rows.push(row("usable hosts", (total - 2).toLocaleString(),
        "of " + total.toLocaleString() + " addresses"));
    } else if (p === 31) {
      rows.push(row("network", toIP(network)));
      rows.push(row("host pair", toIP(network) + " and " + toIP(broadcast),
        "point-to-point, RFC 3021"));
      rows.push(row("usable hosts", "2", "no broadcast address on a /31"));
    } else {
      rows.push(row("usable hosts", "1", "a /32 is a single host route"));
    }
    tbody.innerHTML = rows.join("");
    tableWrap.hidden = false;
  }

  input.addEventListener("input", analyze);
  Array.prototype.forEach.call(document.querySelectorAll(".ip-example"), function (btn) {
    btn.addEventListener("click", function () {
      input.value = btn.getAttribute("data-ip");
      analyze();
      input.focus();
    });
  });
  analyze();
})();
