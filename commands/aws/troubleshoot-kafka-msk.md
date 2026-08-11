---
allowed-tools: Read, Bash, Grep
description: "Diagnoses Amazon MSK (Managed Streaming for Apache Kafka) cluster issues — broker failures, under-replicated partitions, ISR shrink, producer/consumer connectivity, ZooKeeper session failures, disk-full storage, MSK Serverless throttling, and configuration drift"
nl_triggers:
  - "MSK broker unhealthy"
  - "MSK under-replicated partitions"
  - "MSK ISR shrink"
  - "MSK producer cannot connect"
  - "MSK consumer cannot connect"
  - "MSK ZooKeeper session expired"
  - "MSK disk full"
  - "MSK consumer lag"
  - "kafka-topics under-replicated"
  - "MSK cluster HEALTH_ISSUE"
  - "MSK SCRAM auth failed"
  - "MSK TLS handshake failed"
  - "MSK Serverless throttled"
  - "MSK KRaft mode"
  - "MSK Cluster Tier Express"
  - "diagnose MSK cluster"
  - "Kafka MSK troubleshooting"
routes_to: kafka-msk-troubleshooter
---

# /aws:troubleshoot-kafka-msk

Activate the `kafka-msk-troubleshooter` skill and diagnose an Amazon MSK
cluster issue.

## What it does

Reads the cluster's failure signal (cluster State, partition health,
CloudWatch metrics, client logs) and walks the symptom-to-cause decision
tree across seven categories:

1. BROKER_FAILURE — `HEALTH_ISSUE` state, unhealthy broker nodes, MSK
   auto-replacement, CPU/memory saturation.
2. TOPIC_ISSUE — under-replicated partitions, ISR shrink, offline
   partitions, partition skew.
3. CONNECTIVITY — producer/consumer connection failures, security group
   issues, TLS/SCRAM/IAM auth mismatches, cross-VPC routing.
4. ZOOKEEPER — session expired, ZK auth failures, controller flapping
   (ZK-mode clusters; N/A for KRaft).
5. CONFIGURATION — auto-create topics, retention drift, ISR settings.
6. MONITORING — CloudWatch metrics absent, Prometheus JMX target down.
7. STORAGE — EBS disk full, infinite retention, compacted topic growth.

Supports MSK Serverless, MSK Cluster Tier (Express/Standard), and KRaft
mode.

Emits a deterministic VERDICT per cluster:

```text
INCIDENT: <cluster-arn> — <symptom>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
ROOT_CAUSE: <category name> — <specific failing config element or resource>
EVIDENCE:
  - aws kafka describe-cluster: <State + StateInfo line>
  - kafka-topics --describe: <ISR/URP/leader line>
  - CloudWatch AWS/Kafka: <metric + value + timestamp>
  - Client log / broker log: <key error line>
ROOT_CAUSE_CATALOG: #<N>
REMEDIATION:
  1. <specific config change with field name>
  2. <verification command>
  3. <post-apply monitoring>
```

## When to invoke

Paste any of the following:

- An MSK cluster State (`HEALTH_ISSUE`, `MAINTENANCE`).
- `kafka-topics --describe --under-replicated-partitions` output.
- Producer/consumer connection errors (`TimeoutException`,
  `SASL_AUTHENTICATION_FAILED`, `SSLHandshakeException`).
- CloudWatch `AWS/Kafka` metric anomalies.
- "My MSK brokers are unhealthy" / "partitions under-replicated" /
  "producers can't connect."

A bare cluster name + any troubleshoot verb also routes here.

## Inputs

- Cluster ARN or cluster name (or region to list clusters).
- Cluster type: provisioned, serverless, or Cluster Tier Express.
- `aws kafka describe-cluster` output (State + StateInfo).
- `kafka-topics --describe --under-replicated-partitions` output.
- Client error messages from producer/consumer logs.
- CloudWatch `AWS/Kafka` metric snapshots.
- For CONNECTIVITY: `get-bootstrap-brokers` output, security group IDs.

## Outputs

- One VERDICT block per cluster (earliest-failure-category wins).
- EVIDENCE citing the specific AWS CLI fields, kafka-topics output, and
  CloudWatch metrics.
- REMEDIATION with exact AWS CLI and kafka-* commands.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for MSK Analytics).
- `/aws:audit-msk-cluster` for MSK security and configuration audits.
- `/aws:troubleshoot-ecs-task` / `/aws:troubleshoot-eks-pod` for
  compute-layer troubleshooting.
