(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var els = {
    method: $("cb-method"), url: $("cb-url"), headers: $("cb-headers"),
    auth: $("cb-auth"), user: $("cb-auth-user"), token: $("cb-auth-token"),
    ctype: $("cb-ctype"), body: $("cb-body"),
    L: $("cb-L"), k: $("cb-k"), s: $("cb-s"), i: $("cb-i"), v: $("cb-v"),
    compressed: $("cb-compressed"), out: $("cb-out"),
    rowCtype: $("cb-row-ctype"), rowBody: $("cb-row-body"),
    errors: $("cb-errors"), summary: $("cb-summary"), output: $("cb-output")
  };
  if (!els.url || !els.output) return;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  // POSIX single-quote: leave a plain bareword alone, otherwise wrap in single
  // quotes and render any embedded quote as the '\'' idiom.
  function q(s) {
    if (s === "") return "''";
    if (/^[A-Za-z0-9,._:@%+=\/-]+$/.test(s)) return s;
    return "'" + s.replace(/'/g, "'\\''") + "'";
  }

  var CTYPE_HEADER = {
    json: "application/json",
    form: "application/x-www-form-urlencoded",
    text: "text/plain"
  };

  function hasBody() {
    var m = els.method.value;
    return m === "POST" || m === "PUT" || m === "PATCH" || m === "DELETE";
  }

  function headerLines() {
    return els.headers.value.split(/\r?\n/)
      .map(function (l) { return l.trim(); })
      .filter(function (l) { return l; });
  }

  function updateVisibility() {
    var body = hasBody();
    els.rowCtype.hidden = !body;
    els.rowBody.hidden = !body;
    els.user.hidden = els.auth.value !== "basic";
    els.token.hidden = els.auth.value !== "bearer";
  }

  function build() {
    updateVisibility();
    var errors = [];
    var url = els.url.value.trim();
    if (!url) errors.push("a URL is required");

    var parts = ["curl"];
    var method = els.method.value;
    if (method === "HEAD") parts.push("-I");
    else if (method !== "GET") parts.push("-X " + method);

    headerLines().forEach(function (h) { parts.push("-H " + q(h)); });

    if (els.auth.value === "basic") {
      var creds = els.user.value.trim();
      if (!creds) errors.push("enter user:password for basic auth");
      else parts.push("-u " + q(creds));
    } else if (els.auth.value === "bearer") {
      var tok = els.token.value.trim();
      if (!tok) errors.push("enter a bearer token");
      else parts.push("-H " + q("Authorization: Bearer " + tok));
    }

    if (hasBody()) {
      var ct = els.ctype.value;
      if (ct && CTYPE_HEADER[ct]) parts.push("-H " + q("Content-Type: " + CTYPE_HEADER[ct]));
      if (els.body.value !== "") parts.push("--data-raw " + q(els.body.value));
    }

    if (els.L.checked) parts.push("-L");
    if (els.k.checked) parts.push("-k");
    if (els.s.checked) parts.push("-s");
    if (els.i.checked) parts.push("-i");
    if (els.v.checked) parts.push("-v");
    if (els.compressed.checked) parts.push("--compressed");
    var out = els.out.value.trim();
    if (out) parts.push("-o " + q(out));

    if (url) parts.push(q(url));

    els.errors.hidden = errors.length === 0;
    els.errors.innerHTML = errors.map(function (e) {
      return "<div>✗ " + escapeHtml(e) + "</div>";
    }).join("");
    if (errors.length) {
      els.summary.hidden = true;
      els.output.textContent = "# fix the highlighted fields to generate the command";
      return;
    }

    els.output.textContent = parts.join(" ");

    var bits = [];
    var hc = headerLines().length;
    if (hc) bits.push(hc + " custom header" + (hc === 1 ? "" : "s"));
    if (els.auth.value === "basic") bits.push("HTTP basic auth");
    if (els.auth.value === "bearer") bits.push("a bearer token");
    if (hasBody() && els.body.value !== "") {
      bits.push((els.ctype.value === "json" ? "a JSON" :
        els.ctype.value === "form" ? "a form" : "a") + " body");
    }
    if (els.L.checked) bits.push("following redirects");
    if (out) bits.push("saving to " + escapeHtml(out));
    els.summary.innerHTML = "Sends a <strong>" + method + "</strong> request to <strong>" +
      escapeHtml(url) + "</strong>" + (bits.length ? " with " + bits.join(", ") : "") + ".";
    els.summary.hidden = false;
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".cb-form input, .cb-form select, .cb-form textarea"),
    function (el) {
      el.addEventListener("input", build);
      el.addEventListener("change", build);
    });
  build();
})();
