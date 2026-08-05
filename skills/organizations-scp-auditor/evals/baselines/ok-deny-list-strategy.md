# Baseline (no-skill) response: ok-deny-list-strategy

This file captures what a generic assistant produces WITHOUT the
organizations-scp-auditor skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, OU-hierarchy reasoning).

---

This organization has a solid SCP setup. FullAWSAccess is present at
the root in deny-list mode. LeaveOrganization is denied, security
services are protected from disruption, root credential operations are
blocked, and there is a region restriction using
aws:RequestedRegion that limits deployments to us-east-1 and us-west-2.

The region restriction correctly excludes global services like IAM,
Organizations, Route53, CloudFront, WAF, and Support via NotAction, so
those APIs will not be blocked.

This looks like a well-configured organization. No major issues found.
