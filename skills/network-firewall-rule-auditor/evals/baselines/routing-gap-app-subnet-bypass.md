# Baseline (no-skill) response: routing-gap-app-subnet-bypass

This file captures what a generic assistant produces WITHOUT the
network-firewall-rule-auditor skill loaded.

---

The firewall policy looks reasonable — it has a drop rule for known bad IP
ranges and the defaults forward to the stateful engine. TLS inspection is
enabled and logging is configured.

However, looking at the route table for the app subnet, the default route
(0.0.0.0/0) points directly to the internet gateway (igw-0abc123def456)
instead of the firewall ENI. This means traffic from the app subnet goes
directly to the internet without passing through the firewall. The firewall
rules will not be applied to this traffic.

You should update the route table to point the default route to the firewall
ENI instead of the IGW.
