# Eval: root-deny-list-break-glass

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Deny-list strategy at root (FullAWSAccess kept), explicit Denies for LeaveOrganization and CloudTrail tampering, break-glass OU exempted via hierarchy

## Prompt

Create an SCP named root-guardrails that denies
organizations:LeaveOrganization and the CloudTrail tampering
actions (DeleteTrail, StopLogging, PutEventSelectors) across
the org. Attach it to the root r-xxxx. Keep FullAWSAccess.
Carve out a break-glass path for OU_BreakGlass (ou-bg-001) —
the Deny must NOT be inherited there. Organization is in
"All features", caller is the management account 123456789012.
Tag the policy Governance=root-guardrails.
