# Stack Status, Drift, and Stack Policy Reference

Supplementary reference for the CloudFormation Stack Rollback
Troubleshooter skill. Loaded on-demand when a diagnostic needs stack
status transition semantics, drift detection procedures, stack policy
evaluation, or ChangeSet-based rollback preview.

## CloudFormation stack status lifecycle

### Creation lifecycle

```
CREATE_IN_PROGRESS
  → CREATE_COMPLETE (success)
  → CREATE_FAILED (failure)
    → ROLLBACK_IN_PROGRESS
      → ROLLBACK_COMPLETE (all resources cleaned up; stack can only be deleted)
      → ROLLBACK_FAILED (some resources couldn't be cleaned up)
```

### Update lifecycle

```
UPDATE_IN_PROGRESS
  → UPDATE_COMPLETE (success)
  → UPDATE_FAILED (failure)
    → UPDATE_ROLLBACK_IN_PROGRESS
      → UPDATE_ROLLBACK_COMPLETE (rollback succeeded)
      → UPDATE_ROLLBACK_FAILED (rollback failed; terminal state)
```

### Rollback lifecycle

```
UPDATE_ROLLBACK_FAILED (terminal — requires action)
  → continue-update-rollback
    → UPDATE_ROLLBACK_IN_PROGRESS
      → UPDATE_ROLLBACK_COMPLETE (success)
      → UPDATE_ROLLBACK_FAILED (still stuck; another resource blocking)
```

### Delete lifecycle

```
DELETE_IN_PROGRESS
  → DELETE_COMPLETE (success)
  → DELETE_FAILED (some resources couldn't be deleted)
```

## Status semantics for rollback diagnosis

| Status | Meaning | Operator action |
|---|---|---|
| `UPDATE_ROLLBACK_COMPLETE` | Rollback succeeded; stack is back to pre-update state | Investigate the original update failure separately |
| `UPDATE_ROLLBACK_IN_PROGRESS` | Rollback is running | Wait; do not diagnose until terminal |
| `UPDATE_ROLLBACK_FAILED` | Rollback failed; terminal state | Run `continue-update-rollback` (optionally with `--resources-to-skip`) |
| `ROLLBACK_COMPLETE` | Creation failed; all resources cleaned up | Stack can only be deleted; recreate after fixing the template |
| `ROLLBACK_FAILED` | Creation rollback failed; some resources remain | Run `continue-update-rollback`; or `delete-stack` |
| `DELETE_FAILED` | Deletion failed; some resources remain | Identify the resource that can't be deleted; remove dependencies; retry |

## DisableRollback behaviour

| `DisableRollback` | After a failed create/update | Effect |
|---|---|---|
| `false` (default) | CloudFormation rolls back automatically | Resources created before the failure are deleted; stack returns to pre-operation state |
| `true` | CloudFormation does NOT roll back | Resources created before the failure remain; stack stays in `CREATE_FAILED` or `UPDATE_FAILED` with resources intact |

Use `DisableRollback: true` for debugging (preserves the failure state
for investigation). The operator must then manually clean up or fix
the stack via `update-stack`.

## Drift detection

Drift occurs when a resource's actual state diverges from its template
(expected) state due to out-of-band changes (console edits, CLI calls,
API modifications).

### Detection process

```bash
# Initiate drift detection (async operation)
aws cloudformation detect-stack-drift \
  --stack-name <name> --output json
# Returns: { "StackDriftDetectionId": "..." }

# Check detection status
aws cloudformation describe-stack-drift-detection-status \
  --stack-drift-detection-id <id> --output json
# Wait until DetectionStatus = "DETECTION_COMPLETE"

# Review drifted resources
aws cloudformation describe-stack-resource-drifts \
  --stack-name <name> --output json | \
  jq '.StackResourceDrifts[] | select(.StackResourceDriftStatus != "IN_SYNC")'
```

### Drift status values

| `StackResourceDriftStatus` | Meaning |
|---|---|
| `IN_SYNC` | Resource matches the template |
| `MODIFIED` | Resource has been modified outside CloudFormation |
| `DELETED` | Resource exists in the template but was deleted out-of-band |
| `NOT_CHECKED` | Drift detection hasn't been run for this resource |

### How drift blocks rollback

CloudFormation rollback reconciles resources to their previous template
state. If a resource has drifted, the actual state doesn't match either
the current or previous template — CloudFormation can't determine the
correct delta to apply.

Common drift-blocked resources:

| Resource type | Common drift | Rollback failure mode |
|---|---|---|
| `AWS::EC2::SecurityGroup` | Manually-added ingress/egress rules | CFN tries to remove rules that don't exist in either template version |
| `AWS::IAM::Role` | Manually-attached policies | CFN tries to detach policies that aren't in the template |
| `AWS::S3::Bucket` | Manually-changed versioning, lifecycle, policy | CFN tries to revert settings that conflict with drift |
| `AWS::DynamoDB::Table` | Manually-changed billing mode, GSI | CFN tries to revert; billing mode change is immediate |
| `AWS::Lambda::Function` | Manually-changed runtime, memory, timeout | CFN tries to revert; conflicts with drift state |

### Fixing drift before rollback

1. **Revert the drift:** manually change the resource back to match the
   template state. Then retry the rollback.
2. **Update the template:** modify the template to match the drifted
   state, then retry the rollback (the new template state becomes the
   target).
3. **Bypass with `--resources-to-skip`:** skip the drifted resource and
   manage it manually after the rollback.

## Stack policy

A stack policy is a JSON document that protects specific resources from
stack updates. It uses the same IAM-like syntax with `Effect`, `Principal`,
`Action`, `Resource`, and `Condition`.

### Default behaviour

Without a stack policy, all resources can be updated freely. Once a
stack policy is set, all resources are protected by default (implicit
Deny) unless the policy explicitly Allows updates.

### Action values for rollback

| Action | What it covers | Relevance to rollback |
|---|---|---|
| `Update:Modify` | In-place property changes | Rollback may need to Modify a resource |
| `Update:Replace` | Resource replacement (delete old, create new) | Rollback of replaced resources |
| `Update:Delete` | Resource deletion | Rollback of resources created during the failed update |
| `Update:*` | All update actions | Catch-all |
| `Update` (without prefix) | All update actions (legacy syntax) | Same as `Update:*` |

### Example protective policy (blocks RDS replacement)

```json
{
  "Statement": [{
    "Effect": "Deny",
    "Principal": "*",
    "Action": "Update:*",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "ResourceType": ["AWS::RDS::DBInstance"]
      }
    }
  }, {
    "Effect": "Allow",
    "Principal": "*",
    "Action": "Update:*",
    "Resource": "*"
  }]
}
```

This policy Denies ALL updates to RDS instances but Allows updates to
everything else. During rollback, CloudFormation cannot modify RDS
instances — the rollback fails on any RDS resource.

### Temporarily lifting a stack policy for rollback

```bash
# 1. Save the current policy
aws cloudformation get-stack-policy \
  --stack-name <name> --output json > original-policy.json

# 2. Set a temporary allow-all policy
cat > temp-allow-all.json << 'EOF'
{
  "Statement": [{
    "Effect": "Allow",
    "Principal": "*",
    "Action": "Update:*",
    "Resource": "*"
  }]
}
EOF

aws cloudformation set-stack-policy \
  --stack-name <name> \
  --stack-policy-body file://temp-allow-all.json --profile <p>

# 3. Retry the rollback
aws cloudformation continue-update-rollback \
  --stack-name <name> --profile <p>

# 4. After rollback completes, restore the protective policy
aws cloudformation set-stack-policy \
  --stack-name <name> \
  --stack-policy-body file://original-policy.json --profile <p>
```

**Always restore the protective policy after the rollback.** Leaving an
allow-all policy in place defeats the purpose of having a stack policy.

## ChangeSet-based rollback preview

A ChangeSet shows exactly what CloudFormation will do before you execute.
This is the safest way to preview a rollback.

### Creating a rollback ChangeSet

```bash
# Get the current template
aws cloudformation get-template \
  --stack-name <name> --output json > current-template.json

# Create a ChangeSet with the previous template version
aws cloudformation create-change-set \
  --stack-name <name> \
  --change-set-name rollback-preview \
  --change-set-type UPDATE \
  --template-body file://previous-template.json \
  --parameters <same-parameters> \
  --capabilities CAPABILITY_IAM \
  --output json

# Review the changes
aws cloudformation describe-change-set \
  --stack-name <name> \
  --change-set-name rollback-preview \
  --output json | \
  jq '.Changes[].ResourceChange | \
      {Action, LogicalResourceId, ResourceType, Replacement, Scope}'
```

### Interpreting ChangeSet output

| `Action` | Meaning |
|---|---|
| `Add` | New resource will be created |
| `Modify` | Existing resource will be updated in-place or replaced |
| `Remove` | Resource will be deleted |
| `Remove` with `Replacement: True` | Old resource deleted, new one created |

For rollback diagnosis, look for:
- `Remove` on resources that have dependents → will fail
- `Modify` with `Replacement: True` on IAM resources → old resource must
  be deletable
- `Remove` on RDS with `DeletionPolicy: Snapshot` → final snapshot will
  be created

### Execute or discard

```bash
# If the changes look correct:
aws cloudformation execute-change-set \
  --stack-name <name> \
  --change-set-name rollback-preview --profile <p>

# If the changes are wrong:
aws cloudformation delete-change-set \
  --stack-name <name> \
  --change-set-name rollback-preview --profile <p>
```

## CloudFormation resource limits affecting rollback

| Limit | Value | Impact |
|---|---|---|
| Resources per stack | 500 | Large stacks may hit limit during rollback with nested stacks |
| Outputs per stack | 200 | Nested stack output references |
| Parameters per stack | 200 | Template complexity |
| Mappable accounts per StackSet | 1000 | StackSet rollback |
| Stack name length | 128 chars | Child stack naming |
| Template body size | 460,800 bytes | Large templates |
| ChangeSet size | 100 changes per set | Very large rollbacks |

## AWS Health events affecting CloudFormation

| Category | Likely impact |
|---|---|
| `AWS_CLOUDFORMATION_SERVICE` | Regional CFN degradation; stacks may be slow or fail |
| `AWS_CLOUDFORMATION_LIMITS` | Service limits exceeded; stack operations fail |
| `AWS_REGIONAL_EVENT` | Multiple services affected; broad impact |

Always probe `aws health describe-events` for regional issues before
declaring a customer-side root cause during a wide-impact incident.
