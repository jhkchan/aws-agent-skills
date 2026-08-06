# Baseline (no-skill) response: permissive-wildcard-stateful-pass

This file captures what a generic assistant produces WITHOUT the
network-firewall-rule-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, evaluation-order reasoning).

---

This Network Firewall policy has a stateful rule group with a `pass ip any
any -> any any` rule. That looks like it allows all IP traffic through the
firewall. There is also a drop rule for SSH traffic from 10.0.0.0/8, but
since the pass rule comes first and the group uses strict ordering, the drop
rule might not work as expected.

The defaults look correct — traffic is forwarded to the stateful engine and
the stateful default drops unmatched traffic. TLS inspection is enabled and
logging is on.

You should probably remove or narrow the pass rule if you want the firewall
to actually block things.
