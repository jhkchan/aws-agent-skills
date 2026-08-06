# Baseline (no-skill) response: no-tls-inspection-missing-config

This file captures what a generic assistant produces WITHOUT the
network-firewall-rule-auditor skill loaded.

---

This firewall has HTTP-based Suricata rules that inspect content payloads
for malware beacons and suspicious user agents. The policy does not have a
TLS inspection configuration attached.

Since most modern web traffic uses HTTPS, these content-matching rules will
only work on unencrypted HTTP traffic. For HTTPS traffic, the firewall
cannot see the payload content, so the rules will not match.

You should consider enabling TLS inspection if you want these payload rules
to work on encrypted traffic. The rest of the configuration looks fine —
routing is correct, defaults forward to stateful, and logging is enabled.
