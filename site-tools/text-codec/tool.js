(function () {
  "use strict";
  var plain = document.getElementById("tc-plain");
  var encoded = document.getElementById("tc-encoded");
  var mode = document.getElementById("tc-mode");
  var error = document.getElementById("tc-error");
  if (!plain || !encoded || !mode) return;

  var syncing = false;

  function textToBytes(s) { return new TextEncoder().encode(s); }
  function bytesToText(bytes) {
    return new TextDecoder("utf-8", { fatal: true }).decode(bytes);
  }

  function bytesToBase64(bytes) {
    var bin = "";
    for (var i = 0; i < bytes.length; i++) bin += String.fromCharCode(bytes[i]);
    return btoa(bin);
  }
  function base64ToBytes(s) {
    var bin = atob(s);
    var bytes = new Uint8Array(bin.length);
    for (var i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
    return bytes;
  }

  var CODECS = {
    base64: {
      encode: function (s) { return bytesToBase64(textToBytes(s)); },
      decode: function (s) { return bytesToText(base64ToBytes(s.replace(/\s+/g, ""))); }
    },
    base64url: {
      encode: function (s) {
        return bytesToBase64(textToBytes(s))
          .replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
      },
      decode: function (s) {
        var b64 = s.replace(/\s+/g, "").replace(/-/g, "+").replace(/_/g, "/");
        while (b64.length % 4) b64 += "=";
        return bytesToText(base64ToBytes(b64));
      }
    },
    url: {
      encode: function (s) { return encodeURIComponent(s); },
      decode: function (s) { return decodeURIComponent(s.replace(/\+/g, "%20")); }
    },
    hex: {
      encode: function (s) {
        var bytes = textToBytes(s);
        var out = [];
        for (var i = 0; i < bytes.length; i++) {
          out.push((bytes[i] < 16 ? "0" : "") + bytes[i].toString(16));
        }
        return out.join("");
      },
      decode: function (s) {
        var clean = s.replace(/[\s:,-]+/g, "").replace(/^0x/i, "");
        if (!/^[0-9a-fA-F]*$/.test(clean)) throw new Error("contains non-hex characters");
        if (clean.length % 2) throw new Error("odd number of hex digits");
        var bytes = new Uint8Array(clean.length / 2);
        for (var i = 0; i < bytes.length; i++) {
          bytes[i] = parseInt(clean.substr(i * 2, 2), 16);
        }
        return bytesToText(bytes);
      }
    }
  };

  function clearError() { error.hidden = true; }
  function showError(prefix, err) {
    error.textContent = "✗ " + prefix + ": " + (err && err.message ? err.message : "invalid input");
    error.hidden = false;
  }

  function fromPlain() {
    if (syncing) return;
    syncing = true;
    clearError();
    try {
      encoded.value = CODECS[mode.value].encode(plain.value);
    } catch (err) {
      showError("could not encode", err);
    }
    syncing = false;
  }

  function fromEncoded() {
    if (syncing) return;
    syncing = true;
    clearError();
    try {
      plain.value = CODECS[mode.value].decode(encoded.value);
    } catch (err) {
      showError("could not decode as " + mode.options[mode.selectedIndex].text, err);
    }
    syncing = false;
  }

  function legacyCopy(text) {
    return new Promise(function (resolve, reject) {
      var ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try {
        if (document.execCommand("copy")) { resolve(); } else { reject(new Error("copy failed")); }
      } catch (err) { reject(err); } finally { document.body.removeChild(ta); }
    });
  }
  function copyText(text) {
    if (navigator.clipboard && window.isSecureContext) {
      return navigator.clipboard.writeText(text).catch(function () { return legacyCopy(text); });
    }
    return legacyCopy(text);
  }

  plain.addEventListener("input", fromPlain);
  encoded.addEventListener("input", fromEncoded);
  mode.addEventListener("change", fromPlain);
  Array.prototype.forEach.call(document.querySelectorAll(".tc-copy"), function (btn) {
    btn.addEventListener("click", function () {
      var target = document.getElementById(btn.getAttribute("data-copy"));
      copyText(target.value).then(function () {
        btn.textContent = "copied";
        setTimeout(function () { btn.textContent = "copy"; }, 1600);
      }, function () {
        btn.textContent = "failed";
        setTimeout(function () { btn.textContent = "copy"; }, 1600);
      });
    });
  });
})();
