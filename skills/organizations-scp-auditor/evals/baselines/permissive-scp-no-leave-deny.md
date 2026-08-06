# Baseline (no-skill) response: permissive-scp-no-leave-deny

This file captures what a generic assistant produces WITHOUT the
organizations-scp-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, OU-hierarchy reasoning).

---

The organization has FullAWSAccess attached at the root, which means
all services are allowed by default at the SCP layer. The Production OU
has a Deny on root access key creation, which is good.

However, there is no SCP denying organizations:LeaveOrganization.
This means an account administrator could remove their account from the
organization. You should add a deny for that action.

Also, security services like GuardDuty and Security Hub are not
protected from being disabled. Consider adding denies for those
actions too.
