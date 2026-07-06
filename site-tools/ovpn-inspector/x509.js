/* Minimal ASN.1 DER + X.509 certificate parser (no dependencies).
   Parses enough of RFC 5280 to display certificate metadata: validity,
   subject/issuer, serial, signature algorithm, public key, and the common
   extensions (basic constraints, key usage, EKU, SAN). Display-only. */
(function () {
  "use strict";

  // --- ASN.1 DER reader ---
  function Reader(bytes) { this.b = bytes; this.pos = 0; }
  Reader.prototype.readLength = function () {
    var first = this.b[this.pos++];
    if (first < 0x80) return first;
    var n = first & 0x7f;
    var len = 0;
    for (var i = 0; i < n; i++) len = len * 256 + this.b[this.pos++];
    return len;
  };
  Reader.prototype.readTLV = function () {
    var start = this.pos;
    var tag = this.b[this.pos++];
    var len = this.readLength();
    var contentStart = this.pos;
    this.pos += len;
    return {
      tag: tag, cls: tag >> 6, constructed: !!(tag & 0x20), num: tag & 0x1f,
      length: len, content: this.b.subarray(contentStart, contentStart + len),
      full: this.b.subarray(start, this.pos)
    };
  };
  function children(tlv) {
    var r = new Reader(tlv.content);
    var out = [];
    while (r.pos < tlv.content.length) out.push(r.readTLV());
    return out;
  }

  function bytesToHex(bytes, sep) {
    var out = [];
    for (var i = 0; i < bytes.length; i++) {
      out.push((bytes[i] < 16 ? "0" : "") + bytes[i].toString(16));
    }
    return out.join(sep || "");
  }

  function decodeOID(bytes) {
    var vals = [];
    var v = 0;
    for (var i = 0; i < bytes.length; i++) {
      v = v * 128 + (bytes[i] & 0x7f);
      if (!(bytes[i] & 0x80)) { vals.push(v); v = 0; }
    }
    var first = vals.shift();
    var out = [Math.floor(first / 40), first % 40].concat(vals);
    return out.join(".");
  }

  var OID = {
    "2.5.4.3": "CN", "2.5.4.6": "C", "2.5.4.7": "L", "2.5.4.8": "ST",
    "2.5.4.10": "O", "2.5.4.11": "OU", "1.2.840.113549.1.9.1": "emailAddress",
    "1.2.840.113549.1.1.1": "RSA", "1.2.840.10045.2.1": "EC",
    "1.2.840.113549.1.1.5": "sha1WithRSA", "1.2.840.113549.1.1.11": "sha256WithRSA",
    "1.2.840.113549.1.1.12": "sha384WithRSA", "1.2.840.113549.1.1.13": "sha512WithRSA",
    "1.2.840.113549.1.1.4": "md5WithRSA",
    "1.2.840.10045.4.3.2": "ecdsaWithSHA256", "1.2.840.10045.4.3.3": "ecdsaWithSHA384",
    "2.5.29.15": "keyUsage", "2.5.29.19": "basicConstraints",
    "2.5.29.17": "subjectAltName", "2.5.29.37": "extKeyUsage",
    "1.3.6.1.5.5.7.3.1": "serverAuth", "1.3.6.1.5.5.7.3.2": "clientAuth",
    "1.2.840.10045.3.1.7": "P-256", "1.3.132.0.34": "P-384", "1.3.132.0.35": "P-521"
  };

  function parseName(tlv) {
    // Name ::= SEQUENCE OF RelativeDistinguishedName (SET OF AttributeTypeAndValue)
    var parts = [];
    children(tlv).forEach(function (rdn) {
      children(rdn).forEach(function (atv) {
        var pair = children(atv);
        var oid = decodeOID(pair[0].content);
        var name = OID[oid] || oid;
        var value = new TextDecoder().decode(pair[1].content);
        parts.push({ key: name, value: value });
      });
    });
    return parts;
  }

  function parseTime(tlv) {
    var s = new TextDecoder().decode(tlv.content);
    var m;
    if (tlv.num === 0x17) { // UTCTime YYMMDDHHMMSSZ
      m = s.match(/^(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/);
      if (!m) return null;
      var yy = parseInt(m[1], 10);
      var year = yy < 50 ? 2000 + yy : 1900 + yy;
      return new Date(Date.UTC(year, +m[2] - 1, +m[3], +m[4], +m[5], +m[6]));
    }
    // GeneralizedTime YYYYMMDDHHMMSSZ
    m = s.match(/^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})Z$/);
    if (!m) return null;
    return new Date(Date.UTC(+m[1], +m[2] - 1, +m[3], +m[4], +m[5], +m[6]));
  }

  function parseSAN(content) {
    var names = [];
    var r = new Reader(content);
    var seq = r.readTLV(); // SEQUENCE OF GeneralName
    children(seq).forEach(function (gn) {
      var text = new TextDecoder().decode(gn.content);
      if (gn.num === 2) names.push("DNS:" + text);
      else if (gn.num === 1) names.push("email:" + text);
      else if (gn.num === 6) names.push("URI:" + text);
      else if (gn.num === 7 && gn.content.length === 4) names.push("IP:" + Array.from(gn.content).join("."));
      else names.push("other:" + text);
    });
    return names;
  }

  var KEY_USAGE = ["digitalSignature", "nonRepudiation", "keyEncipherment",
    "dataEncipherment", "keyAgreement", "keyCertSign", "cRLSign",
    "encipherOnly", "decipherOnly"];

  function parseKeyUsage(content) {
    var r = new Reader(content);
    var bs = r.readTLV(); // BIT STRING
    var unused = bs.content[0];
    var bits = bs.content.subarray(1);
    var usages = [];
    var total = bits.length * 8 - unused;
    for (var i = 0; i < total && i < KEY_USAGE.length; i++) {
      if (bits[i >> 3] & (0x80 >> (i & 7))) usages.push(KEY_USAGE[i]);
    }
    return usages;
  }

  function parseExtensions(tlv) {
    var ext = { keyUsage: null, eku: null, san: null, isCA: false, pathLen: null };
    var seq = children(tlv)[0]; // [3] EXPLICIT wraps SEQUENCE OF Extension
    children(seq).forEach(function (e) {
      var kids = children(e);
      var oid = decodeOID(kids[0].content);
      var name = OID[oid];
      var valueOctet = kids[kids.length - 1]; // OCTET STRING (skip optional critical BOOL)
      var inner = valueOctet.content;
      if (name === "basicConstraints") {
        var bc = new Reader(inner).readTLV();
        var bcKids = children(bc);
        bcKids.forEach(function (k) {
          if (k.num === 1) ext.isCA = k.content[0] !== 0; // BOOLEAN
          if (k.num === 2) { // INTEGER pathLen
            var pl = 0; for (var i = 0; i < k.content.length; i++) pl = pl * 256 + k.content[i];
            ext.pathLen = pl;
          }
        });
      } else if (name === "keyUsage") {
        ext.keyUsage = parseKeyUsage(inner);
      } else if (name === "extKeyUsage") {
        var ekuSeq = new Reader(inner).readTLV();
        ext.eku = children(ekuSeq).map(function (o) {
          var eo = decodeOID(o.content); return OID[eo] || eo;
        });
      } else if (name === "subjectAltName") {
        ext.san = parseSAN(inner);
      }
    });
    return ext;
  }

  function parsePublicKey(spkiTlv) {
    var kids = children(spkiTlv);
    var algSeq = children(kids[0]);
    var algOid = decodeOID(algSeq[0].content);
    var alg = OID[algOid] || algOid;
    var bitString = kids[1];
    if (alg === "RSA") {
      // BIT STRING -> DER RSAPublicKey SEQUENCE { modulus INTEGER, exponent INTEGER }
      var keyBytes = bitString.content.subarray(1); // drop unused-bits byte
      var rsaSeq = new Reader(keyBytes).readTLV();
      var modulus = children(rsaSeq)[0].content;
      var bits = modulus.length * 8;
      if (modulus[0] === 0x00) bits -= 8; // leading zero pad for sign
      return { type: "RSA", bits: bits, label: "RSA " + bits + "-bit" };
    }
    if (alg === "EC") {
      var curveOid = algSeq.length > 1 ? decodeOID(algSeq[1].content) : null;
      var curve = OID[curveOid] || curveOid || "unknown curve";
      return { type: "EC", curve: curve, label: "EC (" + curve + ")" };
    }
    return { type: alg, label: alg };
  }

  // --- SHA-256 fingerprint (async) ---
  function fingerprint(der) {
    if (!(window.crypto && window.crypto.subtle)) return Promise.resolve(null);
    return window.crypto.subtle.digest("SHA-256", der).then(function (buf) {
      return bytesToHex(new Uint8Array(buf), ":").toUpperCase();
    });
  }

  window.parseCertificate = function (der) {
    var root = new Reader(der).readTLV();          // Certificate SEQUENCE
    var top = children(root);
    var tbs = top[0];                               // TBSCertificate
    var sigAlgSeq = children(top[1]);
    var sigAlg = OID[decodeOID(sigAlgSeq[0].content)] || "unknown";

    var t = children(tbs);
    var idx = 0;
    if (t[0].cls === 2 && t[0].num === 0) idx = 1;   // skip [0] version if present
    var serial = bytesToHex(t[idx].content);         // serialNumber INTEGER
    var issuer = parseName(t[idx + 2]);
    var validity = children(t[idx + 3]);
    var notBefore = parseTime(validity[0]);
    var notAfter = parseTime(validity[1]);
    var subject = parseName(t[idx + 4]);
    var pubkey = parsePublicKey(t[idx + 5]);
    var ext = { keyUsage: null, eku: null, san: null, isCA: false, pathLen: null };
    for (var i = idx + 6; i < t.length; i++) {
      if (t[i].cls === 2 && t[i].num === 3) { ext = parseExtensions(t[i]); break; }
    }

    return {
      serial: serial.replace(/^00/, ""),
      issuer: issuer, subject: subject,
      notBefore: notBefore, notAfter: notAfter,
      signatureAlgorithm: sigAlg,
      publicKey: pubkey,
      extensions: ext,
      der: der,
      fingerprintPromise: fingerprint(der)
    };
  };

  window.x509Util = { bytesToHex: bytesToHex };
})();
