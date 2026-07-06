/* Self-contained MD5 (RFC 1321) over a Uint8Array, returning lowercase hex.
   MD5 is not in WebCrypto, hence this implementation. For integrity display
   only — MD5 is cryptographically broken for signatures/passwords. */
(function () {
  "use strict";
  var S = [7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
           5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
           4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
           6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21];
  var K = [];
  for (var i = 0; i < 64; i++) {
    K[i] = Math.floor(Math.abs(Math.sin(i + 1)) * 4294967296) >>> 0;
  }

  function rotl(x, c) { return ((x << c) | (x >>> (32 - c))) >>> 0; }

  window.md5Bytes = function (bytes) {
    var len = bytes.length;
    var padded = (((len + 8) >> 6) + 1) << 6;
    var buf = new Uint8Array(padded);
    buf.set(bytes);
    buf[len] = 0x80;
    var dv = new DataView(buf.buffer);
    dv.setUint32(padded - 8, (len * 8) >>> 0, true);
    dv.setUint32(padded - 4, Math.floor(len / 536870912) >>> 0, true);

    var a0 = 0x67452301, b0 = 0xefcdab89, c0 = 0x98badcfe, d0 = 0x10325476;
    var M = new Array(16);
    for (var off = 0; off < padded; off += 64) {
      for (var j = 0; j < 16; j++) M[j] = dv.getUint32(off + j * 4, true);
      var A = a0, B = b0, C = c0, D = d0;
      for (var t = 0; t < 64; t++) {
        var F, g;
        if (t < 16) { F = (B & C) | (~B & D); g = t; }
        else if (t < 32) { F = (D & B) | (~D & C); g = (5 * t + 1) % 16; }
        else if (t < 48) { F = B ^ C ^ D; g = (3 * t + 5) % 16; }
        else { F = C ^ (B | ~D); g = (7 * t) % 16; }
        F = ((F >>> 0) + A + K[t] + M[g]) >>> 0;
        A = D; D = C; C = B;
        B = (B + rotl(F, S[t])) >>> 0;
      }
      a0 = (a0 + A) >>> 0;
      b0 = (b0 + B) >>> 0;
      c0 = (c0 + C) >>> 0;
      d0 = (d0 + D) >>> 0;
    }

    function hexLE(n) {
      var out = "";
      for (var k = 0; k < 4; k++) {
        var byte = (n >>> (k * 8)) & 255;
        out += (byte < 16 ? "0" : "") + byte.toString(16);
      }
      return out;
    }
    return hexLE(a0) + hexLE(b0) + hexLE(c0) + hexLE(d0);
  };
})();
