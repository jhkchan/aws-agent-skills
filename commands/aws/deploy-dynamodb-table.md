---
description: Provision a DynamoDB table with production-grade defaults (key design, GSI, PITR, SSE-KMS, TTL, Streams, deletion protection). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create dynamodb table"
  - "provision dynamodb table"
  - "deploy dynamodb table"
  - "dynamodb table setup"
  - "dynamodb production table"
  - "design partition key"
  - "design sort key"
  - "dynamodb gsi design"
  - "dynamodb lsi"
  - "dynamodb capacity mode"
  - "dynamodb on-demand"
  - "dynamodb provisioned autoscaling"
  - "dynamodb pitr"
  - "dynamodb ttl setup"
  - "dynamodb streams"
  - "dynamodb global tables"
  - "dynamodb zero-etl"
  - "dynamodb aurora zero-etl"
  - "dynamodb opensearch zero-etl"
  - "dynamodb deletion protection"
  - "harden dynamodb table"
routes_to: dynamodb-table-deployer
---

# /aws:deploy-dynamodb-table

Activate the `dynamodb-table-deployer` skill and provision a DynamoDB
table with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Partition key design (cardinality, random suffix, composite keys)
2. Sort key design (range queries, hierarchical data)
3. Local Secondary Indexes (creation-time-only, 5-per-table HARD limit)
4. Global Secondary Indexes (projection type, sparse pattern, cascade)
5. Capacity mode + autoscaling (PROVISIONED requires per-GSI registration)
6. Encryption (SSE-KMS with customer-managed CMK for compliance)
7. Point-in-time recovery (PITR enabled by default)
8. TTL configuration (automatic item expiration)
9. Streams + table class + deletion protection
10. Resource-based policies + Global Tables v2

## When to use

- You need to create a new DynamoDB table with production defaults.
- You are designing the partition/sort key scheme before go-live.
- You need to plan GSI/LSI placement (immutable after creation).
- You want to validate that a table design meets production baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## How to invoke

### Slash command

```
/aws:deploy-dynamodb-table
```

Then provide: table name, region, workload description (access patterns,
traffic profile), encryption preference, and any optional features
(GSIs, TTL, Streams, Global Tables).

### Natural language

Any of these routes to the same skill:

- "create a production DynamoDB table"
- "provision a DynamoDB table for sessions"
- "design a DynamoDB partition key"
- "harden my DynamoDB table"
- "set up DynamoDB Streams for CDC"

### CLI routing

```bash
node cli/bin/cli.js route "create a dynamodb table"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline. The
orchestrator routes to it when the user wants to create or harden DynamoDB
tables. The output checklist feeds into verification pipelines and audit
skills (dynamodb-table-auditor for post-deployment audit).

## Example

```
You: /aws:deploy-dynamodb-table

     Provision a production table "prod-sessions" in us-east-1 for a
     high-throughput session store. Session IDs are UUID v4. Need a GSI
     on userId (some sessions anonymous). SSE-KMS with
     alias/prod-dynamodb-key. TTL on expiresAt (24h). Streams
     NEW_AND_OLD_IMAGES for downstream Lambda. Traffic is bursty.
     Account: 123456789012.

Skill:
  TABLE: prod-sessions
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Partition key: sessionId (String) — UUID v4, high-cardinality
    [✓] Sort key: None (single-item lookup)
    [✓] GSIs: gsi_by_userId (userId→sessionId, KEYS_ONLY, sparse)
    [✓] Capacity mode: PAY_PER_REQUEST (bursty traffic)
    [✓] Encryption: SSE-KMS customer CMK (alias/prod-dynamodb-key)
    [✓] PITR: Enabled (35-day window)
    [✓] TTL: Enabled (attribute: expiresAt)
    [✓] Streams: NEW_AND_OLD_IMAGES (Lambda change events)
    [✓] Table class: STANDARD (frequently accessed)
    [✓] Deletion protection: Enabled
  VERIFICATION_COMMANDS:
    aws dynamodb describe-table --table-name prod-sessions
    aws dynamodb describe-continuous-backups --table-name prod-sessions
    aws dynamodb describe-time-to-live --table-name prod-sessions
    aws kms describe-key --key-id alias/prod-dynamodb-key
```

## References

- Skill definition: `skills/dynamodb-table-deployer/SKILL.md`
- Key design and capacity guide: `skills/dynamodb-table-deployer/references/key-design-and-capacity.md`
- Provisioning CLI commands: `skills/dynamodb-table-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/dynamodb-table-deployer/evals/evals.json`
