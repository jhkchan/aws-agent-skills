---
name: operate-dynamodb-global-tables
description: >-
  Slash command for the dynamodb-global-tables-operator skill. Manages
  DynamoDB Global Tables across the full lifecycle: creating replicated
  tables in multiple regions, adding and removing replica regions,
  monitoring ReplicationLatency, executing application-level regional
  failover, and managing per-region PITR. Covers Global Tables v2
  (standard), LAST_WRITER_WINS conflict resolution, and per-region PITR.
  Emits READY | BLOCKED | COMPLETED with the exact CLI sequence and
  verification commands.
skill: dynamodb-global-tables-operator
family: Databases
task_type: operate
verdict_shape: "READY | BLOCKED | COMPLETED"
allowed-tools: Read, Bash, Grep, Glob
---

# /aws:operate-dynamodb-global-tables

Invoke the `dynamodb-global-tables-operator` skill to plan and execute a
DynamoDB Global Tables operation.

Read the skill at `skills/dynamodb-global-tables-operator/SKILL.md`
and follow its procedure to identify the operation, run pre-checks, and
emit the verdict.

## When to use

- Creating a new DynamoDB Global Table replicated across multiple regions.
- Adding a new replica region to an existing global table.
- Removing a replica region from a global table.
- Monitoring cross-region replication latency (ReplicationLatency).
- Executing application-level regional failover.
- Enabling or verifying per-region PITR on a global table.
- Planning a multi-region disaster recovery drill.

## Invocation

```
/aws:operate-dynamodb-global-tables <table name / operation description>
```

The skill will:

1. Identify the operation (create-global-table, add-replica,
   remove-replica, failover, enable-pitr, verify-replication).
2. Run the pre-check gate (table status, schema consistency, replica
   status, IAM permissions, conflict resolution awareness).
3. Emit READY with the exact CLI sequence, or BLOCKED with the failed
   checks.
4. Execute behind a CONFIRM gate.
5. Run post-verification (all replicas ACTIVE, ReplicationLatency within
   threshold, PITR enabled per region).
6. Emit COMPLETED with the verification results and notes.

## Output shape

```text
OPERATION: <create-global-table | add-replica | remove-replica | failover | enable-pitr>
VERDICT: READY | BLOCKED | COMPLETED
TARGET: <table name, primary region, replica regions>
PRE_CHECKS:
  - [PASS] <check description>
  - [FAIL] <check description> — <reason>
STEPS:
  1. <CLI command with flags populated>
  2. <wait/poll command>
POST_VERIFY:
  - [PASS] <verification description>
REPLICA_STATUS:
  - <region>: <ACTIVE | CREATING | DELETING>
NOTES: <application cutover, cost implications, PITR, autoscaling>
```

## Pre-flight

The skill requires the table name and the operation type. Ideally the
operator also provides the target regions, billing mode, and whether
identical tables have been pre-created (for create-global-table). If the
table name is unknown, the skill will suggest
`aws dynamodb list-global-tables` to surface existing global tables.
If the user provides only a vague request with no table name, the skill
emits `BLOCKED`.

## References

- Skill: `skills/dynamodb-global-tables-operator/SKILL.md`
- Reference: `skills/dynamodb-global-tables-operator/references/global-tables-procedures.md`
- Reference: `skills/dynamodb-global-tables-operator/references/multi-region-dr-guide.md`
- AWS docs: https://docs.aws.amazon.com/amazondynamodb/latest/developerguide/GlobalTables.html
