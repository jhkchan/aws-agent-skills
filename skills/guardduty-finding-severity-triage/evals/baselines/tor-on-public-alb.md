# Baseline (no-skill) response: tor-on-public-alb

This file captures what a generic assistant produces WITHOUT the
guardduty-finding-severity-triage skill loaded — the contrast that proves
the skill identifies the expected-anonymous-access false-positive pattern.

---

This finding indicates that an EC2 instance was contacted by a Tor exit
node IP address (185.220.101.45). The severity is 5.0 (medium).

Tor is used for anonymous browsing and can be associated with malicious
activity. You should investigate whether this Tor traffic is expected
for your application.

If you do not expect Tor traffic, you may want to block this IP address
in your security group or WAF rules. If the traffic is expected, you
can archive this finding.
