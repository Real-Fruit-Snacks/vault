(function () {
  "use strict";
  function $(id) { return document.getElementById(id); }
  var els = {
    name: $("sd-name"), desc: $("sd-desc"), docs: $("sd-docs"),
    after: $("sd-after"), wants: $("sd-wants"), requires: $("sd-requires"),
    type: $("sd-type"), exec: $("sd-exec"), execpre: $("sd-execpre"), execstop: $("sd-execstop"),
    workdir: $("sd-workdir"), user: $("sd-user"), group: $("sd-group"),
    env: $("sd-env"), envfile: $("sd-envfile"),
    restart: $("sd-restart"), restartsec: $("sd-restartsec"), remain: $("sd-remain"),
    wantedby: $("sd-wantedby"),
    errors: $("sd-errors"), output: $("sd-output"), install: $("sd-install"), filename: $("sd-filename")
  };
  if (!els.exec || !els.output) return;

  function escapeHtml(s) {
    return String(s).replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }
  function line(key, val) { return val ? key + "=" + val + "\n" : ""; }

  function build() {
    var errors = [];
    var name = (els.name.value.trim() || "myapp").replace(/\.service$/, "");
    if (!/^[A-Za-z0-9_.@-]+$/.test(name)) errors.push("service name has invalid characters");

    var exec = els.exec.value.trim();
    if (!exec) {
      errors.push("ExecStart is required");
    } else {
      // systemd requires an absolute path, after any of the -, @, +, !, : prefixes.
      var bare = exec.replace(/^[-@+!:]+/, "").trim();
      if (bare.charAt(0) !== "/") errors.push("ExecStart must be an absolute path (e.g. /usr/bin/…)");
    }

    var unit = "[Unit]\n";
    unit += line("Description", els.desc.value.trim());
    unit += line("Documentation", els.docs.value.trim());
    unit += line("After", els.after.value.trim());
    unit += line("Wants", els.wants.value.trim());
    unit += line("Requires", els.requires.value.trim());

    var svc = "\n[Service]\n";
    svc += line("Type", els.type.value);
    svc += line("ExecStartPre", els.execpre.value.trim());
    svc += line("ExecStart", exec);
    svc += line("ExecStop", els.execstop.value.trim());
    svc += line("WorkingDirectory", els.workdir.value.trim());
    svc += line("User", els.user.value.trim());
    svc += line("Group", els.group.value.trim());
    els.env.value.split(/\r?\n/).forEach(function (l) {
      var e = l.trim();
      if (e) svc += "Environment=" + e + "\n";
    });
    svc += line("EnvironmentFile", els.envfile.value.trim());
    // Restart=no is the default, so only emit a non-default policy.
    if (els.restart.value !== "no") svc += "Restart=" + els.restart.value + "\n";
    var rs = els.restartsec.value.trim();
    if (rs !== "") {
      var rn = parseInt(rs, 10);
      if (isNaN(rn) || rn < 0) errors.push("RestartSec must be 0 or greater");
      else svc += "RestartSec=" + rn + "\n";
    }
    if (els.remain.checked) svc += "RemainAfterExit=yes\n";

    var install = "\n[Install]\n";
    install += line("WantedBy", els.wantedby.value.trim() || "multi-user.target");

    els.filename.textContent = name + ".service";
    els.errors.hidden = errors.length === 0;
    els.errors.innerHTML = errors.map(function (e) {
      return "<div>✗ " + escapeHtml(e) + "</div>";
    }).join("");
    if (errors.length) {
      els.output.textContent = "# fix the highlighted fields";
      els.install.textContent = "";
      return;
    }

    els.output.textContent = (unit + svc + install).replace(/\s+$/, "") + "\n";
    els.install.textContent =
      "sudo cp " + name + ".service /etc/systemd/system/\n" +
      "sudo systemctl daemon-reload\n" +
      "sudo systemctl enable --now " + name + ".service\n" +
      "systemctl status " + name + ".service";
  }

  Array.prototype.forEach.call(
    document.querySelectorAll(".sd-form input, .sd-form select, .sd-form textarea"),
    function (el) {
      el.addEventListener("input", build);
      el.addEventListener("change", build);
    });
  build();
})();
