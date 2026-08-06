# Baseline (no-skill) response: permissive-fragment-default-pass

This file captures what a generic assistant produces WITHOUT the
network-firewall-rule-auditor skill loaded.

---

The firewall has `StatelessFragmentDefaultActions` set to `aws:pass`. This
means fragmented IP packets are allowed through without inspection.

The rest of the configuration looks good — the main stateless default
forwards to the stateful engine, the stateful default drops unmatched
traffic, TLS inspection is on, and logging is enabled.

The fragment default should probably be changed to forward fragments to the
stateful engine or drop them, so that fragmented traffic does not bypass
inspection.
