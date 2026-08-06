# Baseline (no-skill) response: permissive-resource-policy

This file captures what a generic assistant produces WITHOUT the
networkmanager-core-network-auditor skill loaded.

---

The resource policy on this core network grants networkmanager:* to
Principal "*", which means any AWS account can perform any Network
Manager action on this core network. This is a significant security
risk because any account could create or modify attachments, injecting
routes into your network.

The attachment itself is properly connected and the segment policy
looks reasonable with prod isolated to itself.

You should restrict the resource policy to only the accounts that
need access. Replace the wildcard principal with specific account or
role ARNs.
