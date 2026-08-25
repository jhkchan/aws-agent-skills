# Diagnostic Commands — STS Cross-Account Role Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight safety checks (run before any remediation CLI)

- **Confirm the role exists** and capture its current state:
  ```bash
  aws iam get-role --role-name <name> --query Role.AssumeRolePolicyDocument \
    --output json > /tmp/<name>-trust-backup-$(date +%s).json
  ```
  Fail closed (skip remediation) if `get-role` returns an error.

- **Check if the role is a service-linked role** (role name starts with
  `AWSServiceRoleFor...`). Service-linked roles have trust policies managed
  by AWS and CANNOT be modified via `update-assume-role-policy`. Flagging
  them as remediable wastes the operator's time.

- **Check CloudTrail for recent AssumeRole events** on the role before
  restricting trust — an active cross-account trust may be load-bearing
  for a CI/CD pipeline or monitoring integration:
  ```bash
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
    --max-results 50
  ```

- **Prefer additive remediation** (adding a condition) over destructive
  remediation (removing a statement). Adding `aws:SourceAccount` to a
  service-principal statement narrows the trust without breaking it;
  removing the statement may break a production workload immediately.

- **For WILDCARD_TRUST findings** (Principal `"*"`), treat as
  incident-response. The role may have been assumed by unauthorized parties.
  Contain first (restrict the Principal), then investigate (CloudTrail
  AssumeRole events, session activity), then rotate credentials.
