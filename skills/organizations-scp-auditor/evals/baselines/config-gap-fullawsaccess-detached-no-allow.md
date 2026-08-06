# Baseline (no-skill) response: config-gap-fullawsaccess-detached-no-allow

This file captures what a generic assistant produces WITHOUT the
organizations-scp-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, OU-hierarchy reasoning).

---

It looks like FullAWSAccess has been removed from the root and there
is no replacement Allow policy. This means all accounts in the
organization will have their permissions filtered out at the SCP layer.

The only SCP attached is DenyLeaveOrg, which denies
organizations:LeaveOrganization. But without an Allow SCP, every
action is blocked.

You should either re-attach FullAWSAccess or create an explicit Allow
SCP that lists the approved services. This is likely causing
AccessDenied errors across all member accounts.
