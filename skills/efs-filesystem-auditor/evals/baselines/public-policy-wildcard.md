# Baseline (no-skill) response: public-policy-wildcard

This file captures what a generic assistant produces WITHOUT the
efs-filesystem-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, ClientRootAccess danger reasoning).

---

The filesystem policy grants access to Principal "*" which means everyone.
This includes ClientMount, ClientWrite, and ClientRootAccess which gives
full access including root privileges. This is a security risk because
anyone who can reach the mount target can mount and modify files.

The filesystem is encrypted which is good, and has a lifecycle policy.
However, there are no access points configured.

You should restrict the Principal to specific IAM roles and add conditions
to limit access. Consider using access points for better isolation.
