# Advanced Patterns (load on demand) — CloudFormation Drift Troubleshooter

Expert-knowledge deep dives, the full edge-case catalog, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Prevention deep dive — IAM aws:CalledViaFirst policy (moved from SKILL.md Step 8)

The IAM `aws:CalledViaFirst` condition is the canonical pattern for
"only CloudFormation may touch this resource":

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDirectMutationOnCfnManagedResources",
      "Effect": "Deny",
      "NotAction": [
        "s3:Get*",
        "s3:List*"
      ],
      "Resource": "arn:aws:s3:::my-cfn-managed-bucket",
      "Condition": {
        "StringNotEquals": {
          "aws:CalledViaFirst": "cloudformation.amazonaws.com"
        }
      }
    }
  ]
}
```
## Expert edge cases (moved from SKILL.md)

These patterns represent genuine, non-obvious CloudFormation drift
behaviours that a senior operator would catch but a generalist would
miss.

### Drift detection does not run automatically

CloudFormation does not run drift detection on a schedule. The console
"drift status" column reflects the **last manual run**. A stack may
report `IN_SYNC` based on a stale detection hours or days old. Always
run `detect-stack-drift` before diagnosing, then poll
`describe-stack-drift-detection-status`. For continuous posture, pair
AWS Config with the `cloudformation-stack-drift-detection-check`
managed rule on a schedule.

### Not all resource types support drift detection

CloudFormation drift detection covers most AWS resources, but some
resource types (e.g., `AWS::CloudFormation::WaitConditionHandle`,
some third-party registered types, and resources with custom
`Default` values in extensions) report `NOT_CHECKED`. A stack can
report `DRIFTED` based on partial coverage — and conversely,
`IN_SYNC` based on partial coverage does not mean the un-checked
resources have not drifted. Always inspect the per-resource
`ResourceDriftStatus`, not just the stack-level
`StackDriftStatus`.

### Drift on tags is reported as MODIFIED but rarely impactful

Tags are mutable and almost never block updates. A `MODIFIED` drift
where the only `PropertyDifference` is `Tags` is low-priority and can
usually be resolved by `RESET_TO_DRIFT` (accept the actual tags into
the template) without risk. Reserve urgency for drift on
configuration properties that affect Replacement.

### `aws:CalledViaFirst` is the canonical prevention condition

A simple deny on the underlying service API breaks CloudFormation too.
The correct pattern is a `Condition` that allows the API only when
`aws:CalledViaFirst == cloudformation.amazonaws.com` — CloudFormation
sets this context key when it makes a downstream API call on behalf
of the stack. Apply the deny to all principals that should not make
direct changes, including the CloudFormation execution role itself
(the role inherits the context key correctly when CloudFormation
calls the service).

### Import does not reset drift — it imports the resource

Operators sometimes run `import-resources` expecting it to align the
template to the actual state. It does — but only because the operator
supplies a template that matches the actual resource. Import does not
auto-generate the template from the resource's current configuration.
For that, use the IaC Generator (`cloudformation create-generated-template`),
which emits a template fragment from the existing resource; then
import that fragment into the stack.

### Nested stack drift requires drilling into the child

A parent stack reports `DRIFTED` based on its own resources plus the
aggregate of its child stacks. A child in `DRIFTED` state propagates
up. The parent's `describe-stack-resource-drifts` shows the
`AWS::CloudFormation::Stack` resource as the carrier, but the actual
drifted resources are in the child. Always drill into the child via
its ARN (the parent resource's `PhysicalResourceId`).

### CDK drift differs from CloudFormation drift

`cdk drift` (2025) compares the synthesized template to the deployed
stack, but CDK construct-level drift is not the same as CloudFormation
resource-level drift. A CDK construct may synthesise into multiple
resources; construct-level drift hides which underlying resource
diverged. Always cross-reference the CloudFormation
`describe-stack-resource-drifts` for resource-level detail when
remediating CDK drift.

### `DeletionPolicy: Retain` resources drift silently after stack delete

A resource with `DeletionPolicy: Retain` is skipped on stack delete —
it persists in the account. Subsequent direct changes to that orphaned
resource are not tracked by CloudFormation (the stack no longer
exists). Use AWS Config to track these resources, or attach a
CloudTrail alarm scoped to the resource ARN.

### Drift can cause UPDATE_FAILED on an unrelated property change

A resource drifted out-of-band (e.g., an S3 bucket policy edited
directly). A later stack UPDATE that touches a different property
(e.g., lifecycle configuration) can fail because CloudFormation
reconciles all properties, including the drifted one. The fix is
either to revert the drift before the update, or to update the
template to match the drift first.

### Resource import requires exact property match

The template used in `--resources-to-import` must declare the
resource with properties that match the actual physical resource at
import time. A mismatch causes `IMPORT_FAILED` (similar to
`CREATE_FAILED` for normal stacks). Always run `cfn-lint` on the
import template and verify property values via Config or the
underlying service's describe API before the import.
## Expert heuristic — read the per-resource ResourceDriftStatus (moved from SKILL.md)

The single most common diagnostic mistake is treating the stack-level
`StackDriftStatus: DRIFTED` as the diagnosis. It is the symptom. The
actionable signal is the per-resource `ResourceDriftStatus` on each
resource returned by `describe-stack-resource-drifts`, including the
specific `PropertyDifferences` for each drifted property.

Quick lookup table for common drift resolutions:

| Per-resource finding | What it means | Default resolution |
|---|---|---|
| `MODIFIED` on a mutable property | Property edited out-of-band; update is safe | `RESET_TO_DRIFT` if intentional, else `REVERT_TO_TEMPLATE` |
| `MODIFIED` on an immutable property | Property edited out-of-band; update triggers Replacement | `REVERT_TO_TEMPLATE` first; only `RESET_TO_DRIFT` if Replacement is acceptable |
| `DELETED` on a resource with no dependents | Resource removed manually; nothing depends on it | `REMOVE_FROM_TEMPLATE` or `update-stack` to recreate |
| `DELETED` on a resource with dependents in the stack | Resource removed manually; downstream resources will fail | `update-stack` to recreate first; then verify dependents |
| `ADDITION` (via Config) of a resource that should be managed | Out-of-band resource that overlaps the stack's responsibility | `IMPORT` to bring under management |
| `NOT_CHECKED` on a critical resource | Drift detection unsupported; unknown state | Pair AWS Config rule with periodic CloudTrail review |

When in doubt, run:
`aws cloudformation describe-stack-resource-drifts --stack-name <name>`
and read the `ResourceDriftStatus` and `PropertyDifferences` for each
non-`IN_SYNC` resource. The stack-level `StackDriftStatus` is the
symptom; the per-resource drift is the diagnosis.
## Recent AWS features 2024-2026 (moved from SKILL.md)

- **CloudFormation drift detection for nested stacks (2024-2025):**
  drift detection now recurses into nested child stacks, surfacing
  child drift via the parent's `describe-stack-resource-drifts`. The
  parent's `AWS::CloudFormation::Stack` resource carries the child's
  aggregate drift status; the per-resource detail is in the child.
- **Resource-level import (`import-resources`, enhanced 2024-2025):**
  bring an out-of-band resource under stack management without a
  full stack import. The `--resources-to-import` payload maps an
  existing physical resource to a new logical id in the template.
- **CDK drift detection (`cdk drift`, 2025):** CDK v2.180+ exposes
  `cdk drift <stack-name>`, comparing the synthesized template to
  the deployed stack. Construct-level drift is reported; cross-
  reference CloudFormation for resource-level detail.
- **IaC Generator (`create-generated-template`, 2024-2025):** generates
  CloudFormation template fragments from existing resources in the
  account. Useful for producing the template required for an
  `import-resources` operation on drifted or out-of-band resources.
- **CloudFormation Hooks (GA, 2024-2025):** pre-deployment Hooks fire
  on `CREATE_PRE_DEPLOYMENT`, `UPDATE_PRE_DEPLOYMENT`, and
  `DELETE_PRE_DEPLOYMENT`. Hooks do not prevent out-of-band drift
  directly but enforce compliance on the next stack update.
- **Conformance Pack: `cloudformation-stack-drift-detection-check`**
  (managed rule, 2024): schedules drift detection on a cadence and
  alerts on `StackDriftStatus: DRIFTED`. Pair with SNS + Lambda for
  auto-detection and remediation.
- **`aws:CalledViaFirst` condition key (enhanced 2024-2025):** now
  broadly supported across services, enabling precise IAM policies
  that allow mutations only when made via CloudFormation.
