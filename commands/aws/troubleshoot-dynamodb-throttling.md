---
name: troubleshoot-dynamodb-throttling
description: >-
  Slash command for the dynamodb-throttling-troubleshooter skill. Diagnoses
  DynamoDB ProvisionedThroughputExceededException and throttle events via a
  symptom-to-cause decision tree covering read throttling, write throttling,
  GSI hot-key throttling, burst capacity exhaustion, and adaptive capacity
  lag. Emits ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE with the specific
  throttle type and evidence.
skill: dynamodb-throttling-troubleshooter
family: Databases
task_type: troubleshoot
verdict_shape: "ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:troubleshoot-dynamodb-throttling

Invoke the `dynamodb-throttling-troubleshooter` skill to diagnose a
DynamoDB throttling incident.

Read the skill at `skills/dynamodb-throttling-troubleshooter/SKILL.md`
and follow its diagnostic procedure to identify the root cause.

## When to use

- DynamoDB returns `ProvisionedThroughputExceededException` on reads or
  writes.
- CloudWatch `ThrottledRequests` is elevated.
- Throttling persists after raising provisioned capacity.
- Throttling is intermittent and starts ~5 minutes after traffic spikes.
- A GSI appears to be throttling the base table.
- `Scan` or `BatchGetItem` operations correlate with read throttling.
- On-demand mode throttles on a single partition (sudden spike > 2x
  previous peak).

## Invocation

```
/aws:troubleshoot-dynamodb-throttling <table name / symptom description>
```

The skill will:

1. Identify the symptom category (READ_CAPACITY_LOW, WRITE_CAPACITY_LOW,
   GSI_HOT_KEY, BURST_EXHAUSTED, HOT_PARTITION / ADAPTIVE_LAG,
   SCAN_MISUSE, BATCH_LIMIT).
2. Request the table name and CloudWatch `ThrottledRequests` pattern.
3. Walk the category-specific diagnostic tree.
4. Cross-reference with `ConsumedReadCapacityUnits`,
   `ConsumedWriteCapacityUnits`, per-GSI metrics, Contributor Insights,
   and CloudTrail as required by the category.
5. Map to the common root-cause catalog (8 patterns covering the
   majority of DynamoDB throttle incidents).
6. Verify the proposed fix before applying.
7. Emit the standard VERDICT block.

## Output shape

```text
TABLE: <table name> in <region>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <throttle type> — <specific root cause>
THROTTLE_TYPE: <HOT_PARTITION | GSI_HOT_KEY | READ_CAPACITY_LOW | ...>
EVIDENCE:
  - <CloudWatch signal>: <value>
  - <describe-table / Contributor Insights signal>: <value>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION: <specific config change + verification command>
```

## Pre-flight

The skill requires the table name and region. Ideally the operator also
provides the throttle error string, the CloudWatch `ThrottledRequests`
pattern (spike vs sustained), and `describe-table` output. If the table
name is unknown, the skill will run
`aws cloudwatch get-metric-statistics` across tables to surface recent
throttle events. If the user provides only a vague symptom with no
identifying info, the skill emits `NEED_MORE_INFO`.

## References

- Skill: `skills/dynamodb-throttling-troubleshooter/SKILL.md`
- Reference: `skills/dynamodb-throttling-troubleshooter/references/throttle-decision-tree.md`
- Reference: `skills/dynamodb-throttling-troubleshooter/references/capacity-math.md`
- AWS docs: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/HowItWorks.ReadWriteCapacityMode.html
