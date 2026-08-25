# Advanced Patterns — Multi-Account Governance Automator

## AWS Resource Explorer (2024-2025) — setup commands and use cases

Cross-account search index. Aggregator-type index in one account
(typically audit) collects from local indexes in member accounts.

```bash
# Member account — local index
aws resource-explorer-2 create-index --region us-east-1
# Aggregator account — aggregator index + view
aws resource-explorer-2 update-index-type --index-arn <arn> --type AGGREGATOR
aws resource-explorer-2 create-view --view-name CrossAccountView
```
Use cases: "find all unencrypted S3 buckets across the org", "list every
EC2 instance tagged CostCenter=1234".

## Expert heuristic callouts

- **SCP `Condition` keys are scoped.** `aws:RequestedRegion` works for
  most services but NOT for global services (IAM, Organizations, Route
  53). Use a separate Deny on `iam:*` where applicable.
- **The management account sees SCPs in the console but is NOT subject
  to them.** Treat the management account as untrusted for any automation.
- **Control Tower `CreateAccount` has 5-15 minute latency.** Pipelines
  must poll (`get-account`), not block.
- **Identity Center permission set ARNs differ across regions.** A
  permission set created in us-east-1 has a different ARN than the same
  set in eu-west-1 — `create-account-assignment` requires the
  region-specific ARN.
- **Config recorder delivery failures are silent.** Set a CloudWatch
  alarm on `LastStatus != SUCCESS`.
- **CloudTrail org trail + per-account KMS key = broken.** Each member
  needs to use the log-archive account's KMS key.
- **Security Hub finding aggregator is region-aware.** Cross-region
  findings have a 30-min lag. Use region linking mode `ALL_REGIONS`.
- **Resource Explorer v2 has a 36-hour cold-start.** Do not rely on it
  for incident-time enumeration.
- **Delegated admin rotation is destructive.** Disabling a delegated
  admin deletes the member enrollment. Plan rotation carefully.
- **Control Tower drift detection does NOT cover custom SCPs.** A custom
  SCP you attach is invisible to drift detection — monitor with Config.

## Edge-case handling

- **Member account leaves the org.** Block with a deny-leave-org SCP at
  root. Without it, a member calling `organizations:LeaveOrganization`
  escapes SCP governance entirely.
- **Compromised account.** Move to a `Suspended` OU with Deny-all SCP.
  Revoke RAM shares. Do NOT delete the account — preserve forensics.
- **New region launch.** SCPs scoped to specific regions do not auto-cover
  the new region. Review the region-throttle SCP quarterly.
- **IdP outage.** Without a break-glass path, the org is locked out.
  Document and test a sealed-envelope emergency permission set.
- **Landing Zone drift.** A manual change to a CT-managed SCP or Config
  rule breaks drift detection. Re-baseline via the CT console or
  `update-landing-zone`.

## Recent AWS features (2024-2026)

- **Control Tower Landing Zone v2 (2024-2025):** Customizable guardrails,
  drift detection, lifecycle controls, configurable management region.
  Upgrade via `aws controltower update-landing-zone`.
- **AWS Resource Explorer v2 (2024-2025):** Cross-account aggregator
  indexes. Local index in each member; aggregator in the audit account.
  36-hour cold-start.
- **IAM Identity Center Trusted Identity Propagation (2024-2025):**
  Propagates corporate IdP user identity through to downstream services
  (Redshift, Q Business) for human-attributed audit trails.
- **Control Tower Customizations for Landing Zone (2024-2025):** Native
  Lambda + CloudFormation templates that deploy custom resources alongside
  CT's baseline.
- **Organizations Policy Types (2024-2025):** Beyond SCP — BackupPolicy,
  TagPolicy, AIServicesOptOutPolicy. Use `enable-policy-type`.
- **Security Hub centralized configuration (2024-2025):** Push a single
  Security Hub configuration to all members from the delegated admin.
- **Config Conformance Packs (2024-2025):** Packaged Config rules +
  remediation, deployable across the org via StackSets.

