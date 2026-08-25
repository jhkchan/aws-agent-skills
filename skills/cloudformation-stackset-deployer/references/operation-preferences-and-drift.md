# Operation Preferences and Drift Detection — CloudFormation StackSet Deployer

Deep reference on operation preference tuning, region concurrency,
drift detection mechanics, managed execution, and the full drift
remediation lifecycle. Loaded on demand by the skill.

## Operation preference fields

Operation preferences are passed as `--operation-preferences` on
every create/update/delete-stack-instances and update-stack-set
call. They are NOT persisted on the StackSet — each operation
specifies its own.

| Field | Type | Default | Description |
|---|---|---|---|
| `FailureToleranceCount` | integer | 0 | Number of stack instances that can fail before halting the operation |
| `FailureTolerancePercentage` | integer (0-100) | — | Same as count, as percentage of total instances |
| `MaxConcurrentCount` | integer | 1 | Number of stack instances to deploy/update in parallel |
| `MaxConcurrentPercentage` | integer (0-100) | — | Same as count, as percentage of total instances |
| `RegionConcurrencyType` | SEQUENTIAL \| PARALLEL | SEQUENTIAL | Whether regions deploy in sequence or in parallel |
| `RegionOrder` | list of region names | — | Order of regions when RegionConcurrencyType=SEQUENTIAL |

### Mutual exclusivity rules

- `FailureToleranceCount` and `FailureTolerancePercentage` are
  mutually exclusive. Set ONE per operation, not both.
- `MaxConcurrentCount` and `MaxConcurrentPercentage` are mutually
  exclusive. Set ONE per operation, not both.
- Mixing Count and Percentage in the same operation causes
  `ValidationError`.

### Region concurrency

- `SEQUENTIAL` (default): regions deploy one at a time. Use
  `RegionOrder` to control which region deploys first.
- `PARALLEL`: all regions deploy concurrently. `RegionOrder` is
  ignored. Increases blast radius but completes faster.

## Tuning recommendations

### By organization size

| Org size (target accounts) | FailureTolerance | MaxConcurrent | RegionConcurrency |
|---|---|---|---|
| 1-5 | Count=0 | Count=1 | SEQUENTIAL |
| 5-20 | Count=1 | Count=3 | SEQUENTIAL |
| 20-100 | Percentage=5 | Percentage=10 | SEQUENTIAL |
| 100+ | Percentage=5 | Percentage=20 | SEQUENTIAL or PARALLEL |

### By template sensitivity

| Template type | FailureTolerance | MaxConcurrent | Notes |
|---|---|---|---|
| IAM baseline (low risk) | Percentage=5 | Percentage=20 | Safe to fan out quickly |
| Network/VPC (medium risk) | Count=0 | Count=3 | Halt on first failure |
| Database migration (high risk) | Count=0 | Count=1 | One at a time, halt on failure |

## Drift detection

### Per-instance drift

Each stack instance has its own drift status, independent of other
instances. Drift detection is on-demand or continuous (if managed
execution is enabled).

**On-demand drift detection:**

```bash
aws cloudformation detect-stack-set-drift \
  --stack-set-name my-stackset \
  --operation-preferences MaxConcurrentCount=5
```

This triggers drift detection on ALL stack instances of the
StackSet. Returns an `OperationId` you can poll:

```bash
aws cloudformation describe-stack-set-operation \
  --stack-set-name my-stackset \
  --operation-id <op-id>
```

### StackSet-level drift status

After drift detection completes, the StackSet has an aggregated
drift status:

```bash
aws cloudformation describe-stack-set \
  --stack-set-name my-stackset \
  --query 'StackSet.[DriftStatus,LastDriftCheckTimestamp]'
```

`DriftStatus` values:
- `IN_SYNC` — no instances drifted.
- `DRIFTED` — at least one instance drifted.
- `NOT_CHECKED` — drift detection has not been run.
- `UNKNOWN` — drift detection failed.

### Per-instance drift detail

```bash
aws cloudformation list-stack-instances \
  --stack-set-name my-stackset \
  --output table

# Each instance shows:
#   StackInstanceStatus.DriftStatus: DRIFTED | IN_SYNC | NOT_CHECKED
```

For the specific resource that drifted:

```bash
aws cloudformation describe-stack-resource-drifts \
  --stack-name <member-stack-name> \
  --stack-resource-drift-status-filters MODIFIED DELETED
```

## Managed execution (SERVICE_MANAGED)

For SERVICE_MANAGED StackSets, `ManagedExecution.Active=true`
enables:

1. **Continuous drift detection** — CloudFormation monitors for
   drift without manual `detect-stack-set-drift` calls.
2. **Automatic targeting reconciliation** — when accounts join or
   leave a targeted OU, instances are created or deleted
   automatically on the next `update-stack-set`.
3. **Drift auto-remediation** — drifted instances are reconciled
   on the next `update-stack-set` call.

**Enable managed execution:**

```bash
aws cloudformation update-stack-set \
  --stack-set-name my-stackset \
  --managed-execution Active=true
```

**Warning:** managed execution AUTO-RECONCILES drift. If your
workflow depends on reviewing drift before remediation, set
`Active=false` and schedule manual `detect-stack-set-drift`.

## Drift remediation lifecycle

```text
1. Detect drift
   → detect-stack-set-drift (manual) or managed execution (continuous)
   → StackSet.DriftStatus: DRIFTED

2. Identify drifted instances
   → list-stack-instances --filter DriftStatus=DRIFTED
   → describe-stack-resource-drifts (per instance, for specific resource)

3. Remediate
   → update-stack-instances (reset specific instances to match template)
     OR
   → update-stack-set (reset ALL instances + apply template changes)

4. Verify
   → detect-stack-set-drift again
   → StackSet.DriftStatus should return to IN_SYNC
```

### Manual remediation of specific instances

```bash
aws cloudformation update-stack-instances \
  --stack-set-name my-stackset \
  --deployment-targets Accounts="111111111111" \
  --regions "us-east-1" \
  --operation-preferences MaxConcurrentCount=1
```

This deletes and recreates the member stack from the StackSet
template, overwriting any out-of-band changes.

## Common drift scenarios

| Scenario | Cause | Remediation |
|---|---|---|
| IAM role policy modified manually | Operator edited the role in the console | `update-stack-instances` for that account/region |
| Resource deleted out-of-band | Cleanup script or manual deletion | `update-stack-instances` recreates the resource |
| Parameter drift | Parameter overridden at stack level | `update-stack-instances` with correct parameters |
| Account removed from OU | Account moved to different OU | Instance auto-deleted (if RetainStacksOnAccountRemoval=false) |

## References

- [Operation preferences](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-concepts.html#stacksets-concepts-operation-preferences)
- [StackSet drift detection](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-drift.html)
- [Managed execution](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/stacksets-managed-execution.html)

## Blast-radius tuning heuristic (moved from SKILL.md)

Operation preferences look like a minor knob; they are the single
most important blast-radius control on a StackSet deployment. A
baseline model accepts the defaults; this heuristic explains tuning.

```text
FailureToleranceCount / FailureTolerancePercentage
  → number (or %) of instances that can fail BEFORE halting the operation
  → DEFAULT: 0 (any failure halts) — TOO conservative for large fan-outs
  → Recommendation: set so ≤5% of instances can fail without halting

MaxConcurrentCount / MaxConcurrentPercentage
  → number (or %) of instances deployed IN PARALLEL
  → DEFAULT: 1 (sequential) — TOO slow for large fan-outs
  → Recommendation: 5-10 for typical orgs

Count and Percentage variants are MUTUALLY EXCLUSIVE per operation.
RegionConcurrencyType: SEQUENTIAL (default) or PARALLEL.
RegionOrder: only for SEQUENTIAL (e.g., ['us-east-1','us-west-2']).
```

**Production pattern:** `FailureTolerancePercentage=5`,
`MaxConcurrentPercentage=20`, `RegionConcurrencyType=SEQUENTIAL`,
`RegionOrder=[primary, secondary]`. Tolerate 5% failure, run 20%
of accounts in parallel per region, deploy regions sequentially.

**Safe pattern:** `FailureToleranceCount=0`, `MaxConcurrentCount=1`.
Halt on ANY failure, deploy ONE account at a time.
