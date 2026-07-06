(function () {
  "use strict";
  var input = document.getElementById("pt-input");
  var tbody = document.getElementById("pt-body");
  var count = document.getElementById("pt-count");
  if (!input || !tbody) return;

  // [port, proto, service, category, notes]
  var PORTS = [
    [20, "tcp", "FTP data", "file", "active-mode data channel; see 21"],
    [21, "tcp", "FTP control", "legacy", "plaintext credentials — prefer SFTP (22)"],
    [22, "tcp", "SSH / SFTP / SCP", "remote", "secure shell and everything tunneled over it"],
    [23, "tcp", "Telnet", "legacy", "plaintext remote shell — should not exist on a modern network"],
    [25, "tcp", "SMTP", "mail", "server-to-server mail relay; often blocked outbound by ISPs"],
    [53, "both", "DNS", "infra", "UDP for queries, TCP for zone transfers and large answers"],
    [67, "udp", "DHCP server", "infra", "with 68 (client) — address assignment"],
    [68, "udp", "DHCP client", "infra", "client side of DHCP"],
    [69, "udp", "TFTP", "legacy", "trivial FTP — PXE boot and network gear config"],
    [80, "tcp", "HTTP", "web", "unencrypted web; usually a redirect to 443 now"],
    [88, "both", "Kerberos", "auth", "Active Directory authentication tickets"],
    [102, "tcp", "Siemens S7", "infra", "S7comm PLC protocol (ISO-TSAP) — ICS/OT network"],
    [110, "tcp", "POP3", "legacy", "plaintext mail pickup — use 995"],
    [111, "both", "rpcbind / portmapper", "infra", "ONC RPC service mapping (NFS)"],
    [119, "tcp", "NNTP", "legacy", "usenet news"],
    [123, "udp", "NTP", "infra", "time sync — skew breaks Kerberos and TLS"],
    [135, "tcp", "MS RPC endpoint mapper", "infra", "Windows RPC bootstrap"],
    [137, "udp", "NetBIOS name service", "legacy", "legacy Windows name resolution"],
    [138, "udp", "NetBIOS datagram", "legacy", "legacy Windows browsing"],
    [139, "tcp", "NetBIOS session", "legacy", "SMB over NetBIOS — superseded by 445"],
    [143, "tcp", "IMAP", "mail", "mail access; plaintext unless STARTTLS — prefer 993"],
    [161, "udp", "SNMP", "monitor", "device monitoring; v1/v2c community strings are plaintext"],
    [162, "udp", "SNMP trap", "monitor", "asynchronous alerts from devices"],
    [179, "tcp", "BGP", "infra", "border gateway routing between autonomous systems"],
    [389, "both", "LDAP", "auth", "directory queries; plaintext unless STARTTLS — see 636"],
    [443, "tcp", "HTTPS", "web", "TLS web — also QUIC/HTTP3 on UDP 443"],
    [445, "tcp", "SMB", "file", "Windows file sharing and AD; a top lateral-movement target"],
    [464, "both", "Kerberos kpasswd", "auth", "password changes"],
    [465, "tcp", "SMTPS", "mail", "SMTP submission over implicit TLS"],
    [500, "udp", "IKE / ISAKMP", "remote", "IPsec key exchange; pairs with NAT-T on 4500"],
    [502, "tcp", "Modbus", "infra", "Modbus/TCP PLC control — no auth by design; never expose"],
    [514, "udp", "syslog", "monitor", "classic log shipping; TCP/TLS variants on 601/6514"],
    [515, "tcp", "LPD/LPR", "legacy", "line printer daemon"],
    [520, "udp", "RIP", "legacy", "distance-vector routing protocol"],
    [546, "udp", "DHCPv6 client", "infra", "IPv6 address assignment"],
    [547, "udp", "DHCPv6 server", "infra", "IPv6 address assignment"],
    [587, "tcp", "SMTP submission", "mail", "the correct port for authenticated mail sending (STARTTLS)"],
    [623, "udp", "IPMI / RMCP", "infra", "out-of-band server management (iLO/iDRAC); historically insecure"],
    [631, "both", "IPP / CUPS", "infra", "internet printing protocol and the CUPS admin UI"],
    [636, "tcp", "LDAPS", "auth", "LDAP over TLS"],
    [853, "tcp", "DNS over TLS", "infra", "encrypted DNS (DoT)"],
    [873, "tcp", "rsync", "file", "rsync daemon mode"],
    [902, "tcp", "VMware ESXi", "infra", "host management agent"],
    [989, "tcp", "FTPS data", "file", "FTP over TLS"],
    [990, "tcp", "FTPS control", "file", "FTP over TLS"],
    [993, "tcp", "IMAPS", "mail", "IMAP over TLS — the modern mail-client port"],
    [995, "tcp", "POP3S", "mail", "POP3 over TLS"],
    [1080, "tcp", "SOCKS proxy", "infra", "generic TCP proxying"],
    [1099, "tcp", "Java RMI registry", "infra", "RMI registry — deserialization RCE risk; do not expose"],
    [1194, "udp", "OpenVPN", "remote", "default OpenVPN; TCP 443 fallback common"],
    [1433, "tcp", "SQL Server", "db", "Microsoft SQL Server"],
    [1434, "udp", "SQL Browser", "db", "SQL Server instance discovery"],
    [1521, "tcp", "Oracle", "db", "Oracle TNS listener"],
    [1701, "udp", "L2TP", "remote", "VPN tunneling, usually with IPsec"],
    [1723, "tcp", "PPTP", "legacy", "obsolete VPN — cryptographically broken"],
    [1812, "udp", "RADIUS auth", "auth", "network access authentication"],
    [1813, "udp", "RADIUS accounting", "auth", "session accounting"],
    [1883, "tcp", "MQTT", "infra", "IoT pub/sub broker; plaintext and often unauthenticated"],
    [1900, "udp", "SSDP / UPnP", "infra", "UPnP discovery — a classic reflection/amplification vector"],
    [2049, "both", "NFS", "file", "Unix network file system"],
    [2375, "tcp", "Docker API (plain)", "infra", "unauthenticated by default — never expose"],
    [2376, "tcp", "Docker API (TLS)", "infra", "TLS-protected Docker daemon"],
    [2379, "tcp", "etcd client", "infra", "Kubernetes' datastore"],
    [3000, "tcp", "dev servers / Grafana", "web", "common default for dev web apps and Grafana"],
    [3128, "tcp", "Squid proxy", "infra", "HTTP proxy default"],
    [3260, "tcp", "iSCSI", "file", "block storage over IP"],
    [3268, "tcp", "AD Global Catalog", "auth", "forest-wide LDAP searches; TLS on 3269"],
    [3306, "tcp", "MySQL / MariaDB", "db", "default MySQL family port"],
    [3389, "tcp", "RDP", "remote", "Windows Remote Desktop — brute-force magnet, gate it"],
    [3478, "udp", "STUN/TURN", "infra", "NAT traversal for VoIP/WebRTC"],
    [4369, "tcp", "EPMD", "infra", "Erlang port mapper (RabbitMQ clustering)"],
    [4444, "tcp", "Metasploit default", "remote", "common meterpreter/listener default — suspicious if unexpected"],
    [4500, "udp", "IPsec NAT-T", "remote", "IPsec through NAT"],
    [5000, "tcp", "dev servers / registries", "web", "Flask default, container registries, AirPlay on macOS"],
    [5044, "tcp", "Beats/Logstash", "monitor", "Elastic log shipping"],
    [5060, "both", "SIP", "infra", "VoIP signaling; TLS on 5061"],
    [5353, "udp", "mDNS", "infra", "multicast DNS (Bonjour/Avahi); .local name resolution"],
    [5432, "tcp", "PostgreSQL", "db", "default Postgres port"],
    [5555, "tcp", "ADB", "infra", "Android debug bridge over network — auth-free, dangerous"],
    [5601, "tcp", "Kibana", "monitor", "Elastic dashboard"],
    [5671, "tcp", "AMQP over TLS", "infra", "RabbitMQ secure"],
    [5672, "tcp", "AMQP", "infra", "RabbitMQ default"],
    [5683, "udp", "CoAP", "infra", "constrained-device REST over UDP; DTLS on 5684"],
    [5900, "tcp", "VNC", "remote", "display :0; each display adds one (5901 = :1)"],
    [5985, "tcp", "WinRM HTTP", "remote", "PowerShell remoting; TLS on 5986"],
    [5986, "tcp", "WinRM HTTPS", "remote", "PowerShell remoting over TLS"],
    [6379, "tcp", "Redis", "db", "unauthenticated by default — bind carefully"],
    [6443, "tcp", "Kubernetes API", "infra", "cluster control plane"],
    [6514, "tcp", "syslog-TLS", "monitor", "encrypted syslog"],
    [8000, "tcp", "dev HTTP", "web", "python -m http.server default"],
    [8009, "tcp", "AJP (Tomcat)", "web", "Tomcat AJP connector — Ghostcat (CVE-2020-1938); never expose"],
    [8080, "tcp", "HTTP alternate", "web", "proxies, Tomcat, dev servers"],
    [8443, "tcp", "HTTPS alternate", "web", "admin consoles, Tomcat TLS"],
    [8883, "tcp", "MQTT over TLS", "infra", "MQTT secured with TLS"],
    [8888, "tcp", "Jupyter / dev HTTP", "web", "notebooks and assorted dev tools"],
    [9000, "tcp", "SonarQube / PHP-FPM / MinIO", "web", "heavily contested default"],
    [9090, "tcp", "Prometheus", "monitor", "metrics server and UI"],
    [9093, "tcp", "Alertmanager", "monitor", "Prometheus alert routing"],
    [9100, "both", "node_exporter / JetDirect", "monitor", "Prometheus host metrics — and raw printer jobs"],
    [9200, "tcp", "Elasticsearch", "db", "REST API; cluster transport on 9300"],
    [9418, "tcp", "git daemon", "file", "unauthenticated git protocol"],
    [10050, "tcp", "Zabbix agent", "monitor", "with server on 10051"],
    [11211, "tcp", "Memcached", "db", "no auth; UDP variant fueled famous DDoS amplification"],
    [20000, "tcp", "DNP3", "infra", "SCADA telemetry for utilities — ICS/OT"],
    [27017, "tcp", "MongoDB", "db", "default mongod"],
    [31337, "tcp", "Back Orifice / 'elite'", "legacy", "historic backdoor port; a generic 'leet' marker"],
    [44818, "tcp", "EtherNet/IP (CIP)", "infra", "Allen-Bradley/Rockwell PLCs — ICS; I/O on UDP 2222"],
    [47808, "udp", "BACnet", "infra", "building automation — HVAC, access control"],
    [51820, "udp", "WireGuard", "remote", "modern VPN default"]
  ];

  var BADGES = {
    web: "pt-web", remote: "pt-remote", mail: "pt-mail", file: "pt-file",
    db: "pt-db", auth: "pt-auth", infra: "pt-infra", monitor: "pt-monitor",
    legacy: "pt-legacy"
  };
  var CATEGORY_LABEL = {
    web: "web", remote: "remote access", mail: "mail", file: "file transfer",
    db: "database", auth: "auth / directory", infra: "infrastructure",
    monitor: "monitoring", legacy: "legacy / avoid"
  };

  function escapeHtml(s) {
    return s.replace(/[&<>"]/g, function (c) {
      return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c];
    });
  }

  function render(list) {
    tbody.innerHTML = list.map(function (p) {
      return "<tr><td>" + p[0] + "</td><td>" + p[1] + "</td><td>" +
        escapeHtml(p[2]) + '</td><td><span class="pt-badge ' + BADGES[p[3]] + '">' +
        CATEGORY_LABEL[p[3]] + "</span></td><td>" + escapeHtml(p[4]) + "</td></tr>";
    }).join("");
    count.textContent = list.length + " of " + PORTS.length + " ports";
  }

  function filter() {
    var q = input.value.trim().toLowerCase();
    if (!q) { render(PORTS); return; }
    render(PORTS.filter(function (p) {
      return String(p[0]) === q || String(p[0]).indexOf(q) === 0 ||
        p[2].toLowerCase().indexOf(q) !== -1 ||
        p[4].toLowerCase().indexOf(q) !== -1 ||
        CATEGORY_LABEL[p[3]].indexOf(q) !== -1 ||
        p[1].indexOf(q) !== -1;
    }));
  }

  input.addEventListener("input", filter);
  render(PORTS);
})();
