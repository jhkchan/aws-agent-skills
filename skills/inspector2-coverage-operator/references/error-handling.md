# Error handling and diagnostic flows — inspector2-coverage-operator

Pre-flight attribute effects and per-resource-type diagnostic flows, moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Pre-flight attribute effects (moved from SKILL.md)

| Attribute | Effect on operation |
|---|---|
| `autoEnable.ec2: false` at org level | New members do NOT auto-enable EC2. Update org config or enable per-member. |
| `maxAccountLimitReached: true` | Org hit the member cap (default 1000). BLOCKED until members disassociated. |
| Delegated admin mismatch | `enable-delegated-admin-account` for a non-delegated account returns `ConflictException`. BLOCKED. |
| `relationshipStatus: DISABLED` for a member | Member in the org but Inspector disabled. ENABLE required via delegated admin. |
| `PingStatus: ConnectionLost` (EC2) | Deep inspection cannot scan. BLOCKED for deep-inspection operations. |
| `scanOnPush: false` (ECR) | Images scanned only on manual `start-image-scan`. INFO. |
| Lambda runtime `provided.al2023` | Supported but custom layers may need explicit `lambda:GetLayerVersion` grant. INFO. |

## Diagnostic flows (moved from SKILL.md)

### EC2 instance shows 0% coverage

1. `inspector2 list-coverage --filter-criteria
   'RESOURCE_ID=_EQUALS=i-0123456789abcdef0'` — capture `scanStatus`,
   `scanType`, `errorMessage`.
2. Common failures:
   - `AGENT_NOT_INSTALLED`: install the SSM agent; wait 15-30 min.
   - `AGENT_OFFLINE`: SSM agent `PingStatus: ConnectionLost`. Reboot
     the agent or instance.
   - `DEEP_INSPECTION_NOT_ACTIVE`: SSM association
     `AmazonInspector-ManageAWSAgent` missing or `Associated: false`.
     Create the association via SSM State Manager.
   - `UNSUPPORTED_OS`: rare with 2026 coverage; check release notes.
3. Remediation: install SSM agent / create association / update OS.
   Re-scan is automatic after the next scan window.

### ECR repository shows no scans

1. `ecr describe-image-scanning-configuration --repository-name <name>`
   — capture `scanOnPush`.
2. `ecr describe-images --repository-name <name> --image-ids
   imageTag=latest --query 'imageDetails[0].imageScanStatus'`.
3. Common failures:
   - `scanOnPush: false` and no manual `start-image-scan`: enable
     `scanOnPush` or run `start-image-scan`.
   - `imageScanStatus: FAILED`: image size or manifest error.
   - Region does not support `ecr-enhanced`: fall back to `basic`.
4. Remediation: `put-image-scanning-configuration` /
   `start-image-scan` / move the repository to a supported region.

### Lambda function not scanned

1. `inspector2 list-coverage --filter-criteria
   'RESOURCE_TYPE=_EQUALS=LAMBDA_FUNCTION'` — check if the function
   appears.
2. `lambda get-function-configuration --function-name <name>` —
   capture `runtime`.
3. Common failures:
   - Unsupported runtime (`dotnet6`, `ruby`): Inspector skips.
   - Layers lacking Inspector principal: add `lambda:GetLayerVersion`
     to the layer policy.
   - Function is a published version only: scan applies to `$LATEST`.
4. Remediation: switch runtime (if feasible), add layer permission,
   or accept as a known gap.
