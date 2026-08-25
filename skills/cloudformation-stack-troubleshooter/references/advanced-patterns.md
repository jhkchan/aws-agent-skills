# Advanced Patterns (load on demand) — CloudFormation Stack Troubleshooter

Mindset framing, expert-knowledge deep dives, the edge-case catalog, and recent AWS features moved verbatim from SKILL.md. Loaded on demand.

---

## Mindset — three facts (moved from SKILL.md)

**One-line takeaway:** every CloudFormation stack failure surfaces a
`ResourceStatusReason` on the failing resource in
`describe-stack-events`, and the stack's `StackStatus` identifies which
phase of the lifecycle broke. These two signals are the primary
diagnostic surface — the job of this skill is to walk from the stack
status to the specific resource, then from the `ResourceStatusReason` to
the specific root cause (IAM, limit, immutable property, dependent
resource, custom-resource timeout, nested stack).

Three facts make CloudFormation troubleshooting different from generic
service debugging:

- **`StackStatus` is the lifecycle phase, not the root cause.**
  `CREATE_FAILED`, `UPDATE_FAILED`, `UPDATE_ROLLBACK_COMPLETE`,
  `ROLLBACK_COMPLETE`, `DELETE_FAILED` each name a phase where the stack
  broke. The actionable cause is in the failing resource's
  `ResourceStatusReason`, which is a short string that often embeds the
  underlying service's error message (e.g.,
  `Resource creation cancelled` vs `API: iam:CreateRole AccessDenied`).
  Always read both fields.

- **Updates can require Replacement, and Replacement is irreversible.**
  When a ChangeSet reports `Replacement: true` for a resource,
  CloudFormation will create a new physical resource and delete the old
  one. Many properties are immutable (e.g., an RDS DBInstance's
  `DBInstanceIdentifier`, a DynamoDB table's `KeySchema`, an IAM role's
  `RoleName`). Operators often run `update-stack` without first reviewing
  the ChangeSet and are surprised when the resource is replaced. The
  ChangeSet is the diagnostic surface for updates — always read it.

- **Rollback is not recovery.** When a CREATE or UPDATE fails,
  CloudFormation attempts to roll back. If the rollback also fails, the
  stack enters `ROLLBACK_COMPLETE` (after a failed CREATE) or
  `UPDATE_ROLLBACK_FAILED` (after a failed UPDATE). In both states, the
  stack is broken and cannot be updated — it must be deleted (and, for
  UPDATE_ROLLBACK_FAILED, continued with `ContinueUpdateRollback` to
  skip the failing resource). Operators often keep retrying `update-stack`
  on a `ROLLBACK_COMPLETE` stack and are confused when CloudFormation
  rejects it.
## Expert edge cases (moved from SKILL.md)

These patterns represent genuine, non-obvious CloudFormation failure
modes that a senior operator would catch but a generalist would miss.

### The first `CREATE_FAILED` is the cause; the rest are cascade

When a stack fails to create, CloudFormation cancels all in-flight
resources. `describe-stack-events` may show many `CREATE_FAILED`
resources, but only the **first** (by timestamp) is the real cause —
the rest were cancelled as a cascade. Filter events by
`ResourceStatus: CREATE_FAILED` and sort by `Timestamp` ascending; the
earliest is the root cause.

### `Replacement: True` is not always visible in `describe-stack-events`

When an UPDATE fails because of a replacement, the
`ResourceStatusReason` may say only `Resource update cancelled` — the
replacement intent is visible only in the ChangeSet's
`Changes[].ResourceChange.Replacement`. Always cross-reference
`describe-change-set` for an UPDATE diagnosis, not just events.

### `DeletionPolicy: Retain` does not fail the stack delete

Operators sometimes believe a Retain resource causes `DELETE_FAILED`.
It does not. CloudFormation skips Retain resources and reports them as
`DELETE_SKIPPED` in events. A genuine `DELETE_FAILED` is always a
resource CloudFormation tried to delete but could not (S3 bucket not
empty, dependent resource, custom resource not signalling).

### Nested stacks: the parent's status lags the child's

A parent stack in `UPDATE_ROLLBACK_IN_PROGRESS` often reflects a child
that already failed. The parent's `describe-stack-events` will show the
`AWS::CloudFormation::Stack` resource as the failure point, but the
real cause is inside the child. Always drill into the child stack —
the `PhysicalResourceId` of the nested-stack resource is the child's
ARN.

### `ContinueUpdateRollback --resources-to-skip` is the only recovery from UPDATE_ROLLBACK_FAILED

There is no `retry-rollback` API. The only recovery is
`ContinueUpdateRollback`, optionally with `--resources-to-skip` for a
resource that cannot be rolled back (e.g., a replaced resource whose
old version is gone). After completion, the stack returns to
`UPDATE_ROLLBACK_COMPLETE` and can be updated again. Skipping leaves
the resource in a potentially inconsistent state — document and
reconcile manually.

### Drift can cause UPDATE_FAILED on an unrelated property change

A resource drifted out-of-band (e.g., an S3 bucket's policy edited
directly). A later stack UPDATE that touches a different property
fails because CloudFormation reconciles the drifted property too.
`detect-stack-drift` reveals the drifted property; either import the
current state or reset it before re-deploying.

### Custom resources must handle Delete idempotently

A custom resource's Lambda function must always send `SUCCESS` for a
`Delete` request, even if the physical resource is already gone. A
function that returns `FAILED` on Delete because the resource is
missing will block stack delete indefinitely. Standard pattern: check
existence; if absent, return `SUCCESS` without error.

### CreationPolicy TimeoutSignal is not a CREATE_FAILED resource error

When a `CreationPolicy` `Count` or `TimeoutInMinutes` is not satisfied
(common on EC2 / ASG where cfn-init / cfn-signal is not wired),
CloudFormation reports `CREATE_FAILED` with reason `The following
resource(s) failed to create: [ASG].` — but the instances may be
running and healthy. The fix is in the user-data (`cfn-signal -e 0`)
or the ASG desired capacity, not the template resource itself.

### Service limits can be hard or soft; only Soft can be raised via Quotas

`LimitExceeded` for S3 buckets per account (Soft, default 100) can be
raised via Service Quotas; so can IAM entities per account (default
5000) and VPCs per region (default 5, has a ceiling). Confirm via
`aws service-quotas get-service-quota`.
## Recent AWS features 2024-2026 (moved from SKILL.md)

- **Import resources into an existing stack (enhanced 2024-2025):**
  `cloudformation import-resources` (resource-level import) lets you
  bring an out-of-band resource under stack management without a full
  stack import. Useful when CREATE_FAILED reports "resource already
  exists".
- **ContinueUpdateRollback with nested-stack skip (2024):** enhanced
  to skip nested-stack child resources, making recovery from
  `UPDATE_ROLLBACK_FAILED` on nested stacks less destructive.
- **CloudFormation Drift Detection for nested stacks (2024-2025):**
  drift detection now recurses into nested stacks, surfacing child
  drift in the parent's `describe-stack-resource-drifts`.
- **cfn-lint v1 (2024-2025):** new rule set, stricter on IAM resource
  properties and `DependsOn` cycles. Update pinned versions before
  relying on results.
- **Service Quotas integration (2025):** per-account stack count and
  stack-instance count visible in Service Quotas, simplifying
  `LimitExceeded` triage.
- **UpdateReplacePolicy (GA):** controls retain / delete / snapshot
  behaviour for the OLD physical resource on a Replacement. Set
  `UpdateReplacePolicy: Retain` to keep the old resource after a
  replacement — critical for UPDATE_FAILED recovery.
