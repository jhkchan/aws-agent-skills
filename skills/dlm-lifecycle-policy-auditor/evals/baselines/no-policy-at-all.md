# Baseline (no-skill) response: no-policy-at-all

This file captures what a generic assistant produces WITHOUT the
dlm-lifecycle-policy-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, silent-failure reasoning).

---

You have 50 production EBS volumes but no DLM lifecycle policies. You should
create a DLM policy to automate EBS snapshots for these volumes. Without a
policy, you have no automated backup and would lose data if a volume is
deleted or corrupted.

To fix this, create a DLM lifecycle policy in the console or via CLI that
targets volumes tagged Environment:production and creates daily snapshots
with reasonable retention.
