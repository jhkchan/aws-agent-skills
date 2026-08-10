# Baseline (no-skill) response: scp-inheritance-conflict

This file captures what a generic assistant produces WITHOUT the
multi-account-governance-automator skill loaded.

---

Looking at your SCPs, the root has an Allow for ec2:* and the
Workloads-Prod OU has a Deny for specific instance types. Since the
Allow is at the root level, it should take precedence over the Deny at
the OU level.

The issue might be with the condition in the Deny SCP. Check if the
instance type values match exactly. You could also try moving the Allow
SCP to the OU level or adding the large instance types to the Allow.

If that doesn't work, try removing the Deny SCP temporarily to see if
the issue resolves. Then re-attach with modified conditions.
