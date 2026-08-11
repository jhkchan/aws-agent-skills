---
description: Diagnoses Kafka Connect and Amazon MSK Connect issues through a nine-category diagnostic tree — task FAILED status (task exceptions), worker rebalance storms (consumer group coordinator churn), source connector lag (LagMax, offset not advancing), sink connector errors (DLQ config, retry exhaustion), schema registry connectivity (Avro/JSON/Protobuf, Confluent, Glue Schema Registry), IAM auth for MSK (kafka-cluster principal), plugin or connector class not found (custom plugin, Debezium), connector configuration errors (wrong topics, bootstrap servers, converter mismatch), and Single Message Transforms (SMT chain, Cast, ExtractTopic). Reads describe-connector or REST API status, CloudWatch logs (/aws/kafkaconnect/), and MSK describe-cluster for bootstrap and IAM validation. Emits ROOT_CAUSE_FOUND with the failing probe, NEED_MORE_INFO when a probe requires operator input, or ESCALATE for AWS-side incidents.
nl_triggers:
  - "Kafka Connect failed"
  - "MSK Connect connector FAILED"
  - "Kafka Connect task FAILED"
  - "connector class not found"
  - "Kafka Connect worker rebalance"
  - "source connector lag growing"
  - "LagMax Kafka Connect"
  - "sink connector DLQ full"
  - "dead letter queue overflow"
  - "schema registry connection refused"
  - "Avro serializer error"
  - "MSK IAM authentication failed"
  - "Debezium connector not starting"
  - "Single Message Transform error"
  - "SMT Cast error"
  - "custom plugin upload failed"
  - "bootstrap servers wrong"
  - "diagnose Kafka Connect failure"
  - "Kafka Connect Protobuf Avro mismatch"
routes_to: kafka-connect-troubleshooter
---

# /aws:troubleshoot-kafka-connect

Activate the `kafka-connect-troubleshooter` skill and diagnose a
Kafka Connect or Amazon MSK Connect failure through the nine-category
diagnostic tree.

## What it does

Reads a connector status record (`describe-connector` or REST API
`/connectors/{name}/status` — state, trace, worker_id), the
CloudWatch Logs excerpt for the failing connector
(`/aws/kafkaconnect/<connector>`), and the MSK cluster bootstrap /
IAM configuration, then walks the nine-category diagnostic tree to a
root cause with positive evidence:

1. **Pre-flight** — data sufficiency gate. If CloudWatch Logs are
   missing, the connector is still CREATING/UPDATING, or the REST API
   is unreachable, emit NEED_MORE_INFO with the specific data gap.
2. **Symptom entry** — map the status / log signature to a category:
   - `trace` has a Java exception → Step 1 (TASK_EXCEPTION).
   - Logs show `Rebalance` every few minutes → Step 2
     (WORKER_REBALANCE).
   - State RUNNING but LagMax grows → Step 3 (SOURCE_LAG).
   - DLQ filling → Step 4 (SINK_DLQ / SINK_RETRY).
   - `Connection refused` to schema registry → Step 5
     (SCHEMA_REGISTRY).
   - `SASL_NOT_LOGGED_IN` / `authorization failed` → Step 6
     (IAM_AUTH).
   - `ClassNotFoundException` on creation → Step 7 (PLUGIN_MISSING).
   - `Unknown topic` / wrong bootstrap → Step 8 (CONFIG_ERROR).
   - SMT class in the trace → Step 9 (SMT_ERROR).
   - Debezium startup hangs → Step 10 (DEBEZIUM_CDC).
3. **Category-specific probe** — for each candidate category, run the
   probe (CloudWatch filter, IAM simulate, SG inspection, plugin
   describe, schema registry curl).
4. **Verdict** — ROOT_CAUSE_FOUND (failing probe confirmed),
   NEED_MORE_INFO (probe requires operator input), or ESCALATE
   (AWS-side MSK incident via AWS Health).

Emits a deterministic diagnostic block per target:

```text
TARGET: <connector-name> or <connector-name>/task-<n>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failing category and probe>
CATEGORY: TASK_EXCEPTION | WORKER_REBALANCE | SOURCE_LAG |
          SINK_DLQ | SINK_RETRY | SCHEMA_REGISTRY | IAM_AUTH |
          PLUGIN_MISSING | CONFIG_ERROR | SMT_ERROR |
          DEBEZIUM_CDC | UNKNOWN
EVIDENCE:
  - <observed symptom>
  - <failing probe — command and confirming output>
  - <passing probes — categories ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command>
```

## When to invoke

Paste a connector status record, error message, or CloudWatch
excerpt and ask any of:

- "Kafka Connect connector FAILED last night — what went wrong?"
- "MSK Connect task FAILED with empty trace"
- "connector is RUNNING but LagMax is growing"
- "DLQ is filling up for my sink connector"
- "schema registry connection refused from MSK Connect"
- "MSK IAM authentication failed for my connector"
- "Debezium connector won't start — class not found"
- "SMT Cast error in my connector"
- "diagnose this Kafka Connect failure"

A bare connector name + any failure verb ("connector failed",
"task FAILED", "DLQ full") also routes here via the orchestrator.

## Inputs

- **Connector status:** connector name, ARN, state, tasks[].state,
  trace, worker_id (from `describe-connector` or the REST API).
- **CloudWatch Logs excerpt:** the failing connector's log group
  (`/aws/kafkaconnect/<connector>`) filtered to ERROR / Exception.
- **MSK cluster info:** cluster ARN, bootstrap brokers, IAM auth
  configuration (from `describe-cluster`).
- **IAM:** connector execution role ARN, IAM policy (for the
  `simulate-principal-policy` probe in Step 6).
- **Network:** worker subnet, worker SG (for the egress probe in
  Step 6 and Step 5).
- **Plugin:** custom plugin ARN and state (for Step 7).
- **Producer / schema registry:** producer converter, schema
  registry URL and reachability (for Step 5 and Step 8).

## Outputs

- One diagnostic block per connector.
- CATEGORY from the enumerated set.
- Evidence section with the failing probe AND passing probes
  (categories ruled out) — never a verdict without positive
  evidence.
- Specific remediation: config update, plugin re-upload, IAM policy
  edit, SG rule, or AWS Support escalation.
- A CONFIRM gate before any state-changing CLI.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for Kafka Connect / MSK
  Connect).
- `/aws:audit-msk-cluster` for MSK cluster configuration posture
  audits (this skill diagnoses connectors, not the cluster itself).
- `/aws:troubleshoot-vpc-connectivity` when the connector failure is
  downstream network-side (the connector is fine; the broker /
  registry / sink is unreachable).
- `/aws:troubleshoot-iam-permission` when the root cause is an IAM
  permission gap on the connector's execution role.
