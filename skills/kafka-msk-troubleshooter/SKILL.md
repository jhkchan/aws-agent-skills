---
name: kafka-msk-troubleshooter
description: Diagnoses Amazon MSK (Managed Streaming for Apache Kafka) cluster issues via a symptom-to-cause decision tree covering broker failures (describe-cluster, broker node health, replacement), topic issues (under-replicated partitions, ISR shrink, offline partitions), producer and consumer connectivity (security groups, TLS client auth, SCRAM, IAM auth), ZooKeeper connectivity failures, MSK configuration problems (auto-create topics, log.retention, num.partitions), monitoring gaps (CloudWatch AWS/Kafka, Prometheus JMX), and storage exhaustion (EBS volume full). Supports MSK Serverless, MSK Cluster Tier (Express / Standard), and KRaft mode (KIP-833). Emits a deterministic verdict (ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE) with evidence from kafka-topics, kafka-consumer-groups, aws kafka describe-cluster, and CloudWatch metrics. Use when brokers are unhealthy, partitions are under-replicated, producers or consumers cannot connect, ZooKeeper session expired, disk is full, or consumer lag spikes.
license: Apache-2.0
compatibility: Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). Offline diagnosis works on pasted kafka-topics, kafka-consumer-groups, aws kafka describe-cluster output, and CloudWatch metric snapshots. Live-cluster diagnosis uses aws kafka describe-cluster, describe-configuration, list-nodes, get-bootstrap-brokers, describe-cluster-v2 (Cluster Tier), aws cloudwatch get-metric-statistics (AWS/Kafka namespace), kafka-topics.sh --describe --under-replicated-partitions...
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '2'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Analytics
  task_type: troubleshoot
  skill_class: capability
  lifecycle_status: active
  verdict_shape: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
  when_to_use: Diagnosing why an Amazon MSK cluster has unhealthy brokers, under-replicated partitions or shrinking ISR, producers or consumers that cannot connect, ZooKeeper session expiries, disk-full EBS volumes, consumer lag spikes, or configuration drift; interpreting kafka-topics --describe output, aws kafka describe-cluster State, CloudWatch AWS/Kafka metrics, and broker logs.
  when_not_to_use: Provisioning a new MSK cluster (use a deploy skill), optimizing MSK cost (use an optimize skill), auditing MSK security posture (use the audit-msk-cluster skill), or application-level Kafka consumer code debugging. This skill focuses on cluster-level operational diagnosis.
  activation_triggers: MSK broker unhealthy, MSK under-replicated partitions, MSK ISR shrink, MSK producer cannot connect, MSK consumer cannot connect, MSK ZooKeeper session expired, MSK disk full, MSK consumer lag, kafka-topics under-replicated, MSK cluster HEALTH_ISSUE, MSK SCRAM auth failed, MSK TLS handshake failed, MSK Serverless throttled, MSK KRaft mode, MSK Cluster Tier Express
  invocation_schema: 'Input: either (a) a symptom description (cluster ARN, observed state, error messages from kafka-topics / kafka-consumer-groups / client logs), OR (b) a live-cluster scenario where the agent runs aws kafka describe-cluster, kafka-topics --describe --under-replicated-partitions, and CloudWatch metric queries to gather evidence. Output: a deterministic INCIDENT / VERDICT / ROOT_CAUSE / EVIDENCE / REMEDIATION block where VERDICT in {ROOT_CAUSE_FOUND, NEED_MORE_INFO, ESCALATE} and ROOT_CAUSE names the specific failure category (BROKER_FAILURE / TOPIC_ISSUE / CONNECTIVITY / ZOOKEEPER / CONFIGURATION / MONITORING / STORAGE) and the offending config element or resource.'
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  keywords: MSK, Kafka, Managed Streaming for Kafka, under-replicated partitions, ISR, broker failure, ZooKeeper, KRaft, MSK Serverless, MSK Cluster Tier, Express Class, SCRAM, SASL/PLAIN, TLS client auth, IAM auth, consumer lag, producer throughput, log retention, EBS volume full, CloudWatch MSK metrics, Prometheus JMX
  tags: aws, msk, kafka, analytics, troubleshoot, broker, partition, isr, zookeeper, scram, tls
---

# Kafka MSK Troubleshooter

## Activation

Activate this skill when the user reports an Amazon MSK cluster issue. Trigger
phrases: "MSK broker unhealthy", "MSK under-replicated partitions", "MSK ISR
shrink", "MSK producer cannot connect", "MSK consumer cannot connect", "MSK
ZooKeeper session expired", "MSK disk full", "MSK consumer lag",
"kafka-topics under-replicated", "MSK cluster HEALTH_ISSUE", "MSK SCRAM auth
failed", "MSK TLS handshake failed", "MSK Serverless throttled".

## Mindset

**One-line takeaway:** every MSK failure surfaces in three places — the
cluster State (`aws kafka describe-cluster`), the partition health
(`kafka-topics --describe --under-replicated-partitions`), and the CloudWatch
`AWS/Kafka` metrics (`UnderReplicatedPartitions`, `OfflinePartitions`,
`BytesInPerSec`, `CpuUser`, `DiskUsage`). Read all three before declaring a
root cause.

Four facts make MSK troubleshooting different from self-managed Kafka:

- **The cluster State is the entry point to the decision tree.** `ACTIVE`
  with `HEALTH_ISSUE` StateInfo means broker-level degradation. `UPDATING`
  means a maintenance window or configuration change is in progress.
  `MAINTENANCE` means AWS is replacing a broker.
- **Under-replicated partitions (URP) is the single most important Kafka
  health metric.** `UnderReplicatedPartitions > 0` means at least one
  follower is not keeping up with the leader. The cause is always one of:
  broker down, broker overloaded (CPU/disk/network), ISR shrink from
  `replica.lag.time.max.ms` exceeded, or network partition between brokers.
- **MSK manages brokers — but not topics, ACLs, or client auth.** AWS
  replaces failed brokers and rebalances partitions automatically. The
  operator is responsible for topic configuration, client auth (SCRAM/TLS/
  IAM), and security group rules. Most "MSK is broken" issues are
  client-side configuration issues.
- **MSK Serverless and Cluster Tier Express do not expose brokers.**
  `kafka-topics --describe` and `kafka-consumer-groups` work, but
  `list-nodes` and per-broker metrics do not. Troubleshooting shifts to
  client-side auth, partition count limits, and throughput capacity mode.

## Quick reference — symptom to failure category

| Observed state | Failure category | First probe |
|---|---|---|
| `State=HEALTH_ISSUE`, broker node `NOT_HEALTHY` | BROKER_FAILURE | `describe-cluster` StateInfo; `list-nodes` per-broker health |
| `kafka-topics --describe --under-replicated-partitions` returns partitions | TOPIC_ISSUE | `kafka-topics --describe --topic` ISR column; ISR vs ReplicationFactor |
| Producer/consumer `TimeoutException`, `NOT_LEADER_OF_PARTITION`, `Connection refused` | CONNECTIVITY | `get-bootstrap-brokers`; security group; client auth config |
| `ZooKeeper session expired`, `AUTH_FAILED` on ZK port 2181 | ZOOKEEPER | ZK security group, TlsConfiguration, `zookeeper.set.acl` |
| `UnknownTopicOrPartitionError`, topic auto-creation, retention not working | CONFIGURATION | `describe-configuration`; verify `auto.create.topics.enable`, `log.retention.hours` |
| CloudWatch `AWS/Kafka` metrics absent or stale | MONITORING | `describe-monitoring`; CloudWatch Logs `/aws/kafka/<cluster>/` |
| `DiskUsage > 90%`, `ERROR: Disk full`, broker read-only | STORAGE | CloudWatch `DiskUsage` per broker; `log.retention.bytes` vs EBS size |
| MSK Serverless `ThrottlingException`, `429` | TOPIC_ISSUE (Serverless) | Partition count vs RCUs; `kafka-topics --describe` |

## Quick navigation

- **Step 0** — Capture the failure signal (cluster ARN, State, symptom).
- **Step 1** — Map the symptom to a category letter (A-G).
- **Step 2** — BROKER_FAILURE diagnostic (unhealthy broker, replacement).
- **Step 3** — TOPIC_ISSUE diagnostic (under-replicated partitions, ISR).
- **Step 4** — CONNECTIVITY diagnostic (producer/consumer cannot connect).
- **Step 5** — ZOOKEEPER diagnostic (session expired, ZK auth).
- **Step 6** — CONFIGURATION diagnostic (auto-create, retention, ISR).
- **Step 7** — MONITORING diagnostic (metrics missing, Prometheus).
- **Step 8** — STORAGE diagnostic (EBS disk full, retention pressure).
- **Step 9** — Root-cause catalog (top patterns + canonical fixes).
- **Step 10** — Verify the fix and decide VERDICT.

## STRICT output contract

Every diagnostic response MUST emit this block. No prose before or after.

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

Do NOT omit any field. If a field is not applicable, write `N/A` with a
one-line reason.

## Process — Diagnostic decision tree (apply in order)

### Step 0: Capture the failure signal

| Signal | Source | Why required |
|---|---|---|
| **Cluster ARN / name** | User-provided or `aws kafka list-clusters` | All describe/metrics calls need this |
| **Cluster State + StateInfo** | `aws kafka describe-cluster --cluster-arn <arn>` | Drives the symptom category |
| **Partition health** | `kafka-topics --describe --under-replicated-partitions` | Narrows from symptom to cause |

If the user has not provided the cluster ARN or name, output:

```text
INCIDENT: <unknown-cluster> — <symptom>
VERDICT: NEED_MORE_INFO
REASON: Cannot diagnose without the MSK cluster ARN or name. Identify
  the cluster with: aws kafka list-clusters
MISSING:
  - Cluster ARN or cluster name
  - Cluster type (provisioned / serverless / Cluster Tier Express)
  - Symptom (broker unhealthy, URP, consumer lag, producer timeout, etc.)
```

```bash
aws kafka list-clusters --query \
  'ClusterInfoList[*].{Name:ClusterName,ARN:ClusterArn,State:State,Type:ClusterType}'
# For Cluster Tier (v2 API):
aws kafka list-clusters-v2 --query \
  'ClusterInfoList[*].{Name:ClusterName,ARN:ClusterArn,Type:ClusterType,State:State}'
```

### Step 1: Identify the symptom category

| Category | Signature | Step |
|---|---|---|
| **A. BROKER_FAILURE** | `State=HEALTH_ISSUE`; node `NOT_HEALTHY` | Step 2 |
| **B. TOPIC_ISSUE** | URP returned; ISR < ReplicationFactor; `OfflinePartitions > 0` | Step 3 |
| **C. CONNECTIVITY** | Client `TimeoutException`, `Connection refused`, `SSLHandshakeException` | Step 4 |
| **D. ZOOKEEPER** | `ZooKeeper session expired`, ZK port 2181 `AUTH_FAILED` | Step 5 |
| **E. CONFIGURATION** | `UnknownTopicOrPartitionError`, auto-created 1-partition topics | Step 6 |
| **F. MONITORING** | CloudWatch `AWS/Kafka` metrics absent; Prometheus target down | Step 7 |
| **G. STORAGE** | `DiskUsage > 90%`; broker read-only; `log.retention.bytes` exceeded | Step 8 |

**Earliest-failure rule.** BROKER_FAILURE precedes STORAGE precedes
TOPIC_ISSUE precedes CONNECTIVITY. ZOOKEEPER and CONFIGURATION are
root-cause categories producing secondary symptoms.

### Step 2: BROKER_FAILURE diagnostic

| Signal | Root cause | Probe |
|---|---|---|
| `State=HEALTH_ISSUE`, `NOT_HEALTHY` | EBS failure, OS issue, or OOM | `list-nodes --cluster-arn <arn>` per-broker health |
| `State=MAINTENANCE`, `Replacing broker` | AWS-initiated broker replacement | Check `describe-cluster` StateInfo; wait for replacement |
| `CpuUser > 85%` sustained | Broker CPU saturated | CloudWatch `CpuUser`; check `BytesInPerSec` trend |
| `MemoryUsed > 90%` | JVM heap pressure, GC thrashing | CloudWatch `MemoryUsed`; check JVM heap config |
| Broker replaced but reassignment stalled | Reassignment task stuck or throttled | `kafka-reassign-partitions --verify` |

```bash
# Cluster state + StateInfo:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.{State:State,StateInfo:StateInfo,Version:CurrentBrokerSoftwareInfo.KafkaVersion,Type:BrokerNodeGroupInfo.InstanceType}'

# Per-broker health (provisioned only):
aws kafka list-nodes --cluster-arn <arn> \
  --query 'NodeInfoList[*].{Broker:BrokerNodeInfo.BrokerId,Instance:BrokerNodeInfo.InstanceType,Size:BrokerNodeInfo.BrokerVolumeSizeGB}'

# Cluster Tier v2:
aws kafka describe-cluster-v2 --cluster-arn <arn> \
  --query 'ClusterInfo.{Type:ClusterType,State:State,StateInfo:StateInfo}'

# CloudWatch broker CPU:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name CpuUser \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=1 \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output text
```

**Fix patterns:** EBS/OS failure — wait for MSK auto-replacement. CPU
saturated — scale up broker type or add brokers. OOM — increase JVM heap
via MSK configuration (`kafkaHeapOptions`) or scale up instance type.

### Step 3: TOPIC_ISSUE diagnostic (URP, ISR shrink)

| Signal | Root cause | Probe |
|---|---|---|
| `UnderReplicatedPartitions > 0`, ISR < ReplicationFactor | Follower broker down, slow, or partitioned from leader | Identify which brokers missing from ISR; check Step 2 |
| ISR drops periodically then recovers | `replica.lag.time.max.ms` too aggressive for burst workload | `describe-configuration`; compare to produce burst pattern |
| `OfflinePartitions > 0` | All replicas down — no ISR member | P0 — immediately check Step 2 (BROKER_FAILURE) |
| URP on specific partition set | Reassignment in progress or partition skew | `kafka-topics --describe --topic <topic>`; check leader distribution |
| Serverless `ThrottlingException`, 429 | Partition count exceeds RCUs for workload | Count partitions; reduce or batch produce calls |

**Walk:**

1. Run URP check. The output lists each affected topic-partition with
   `Leader`, `Replicas`, and `Isr`. If `Replicas: 1,2,3` and `Isr: 1`,
   brokers 2 and 3 are out of sync.
2. If ISR shrinks intermittently: check `replica.lag.time.max.ms` (default
   30s). For bursty workloads, raise to 60s.
3. Check partition distribution skew: if one broker leads 80% of partitions,
   run `kafka-preferred-replica-election` or `kafka-reassign-partitions`.
4. `OfflinePartitions > 0` is P0 — all replicas down.

```bash
# List ALL under-replicated partitions:
kafka-topics --bootstrap-server <bs> --describe --under-replicated-partitions
# List partitions under min ISR:
kafka-topics --bootstrap-server <bs> --describe --under-min-isr-partitions
# Full topic describe:
kafka-topics --bootstrap-server <bs> --describe --topic <topic>
# CloudWatch URP metric:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name UnderReplicatedPartitions \
  --dimensions Name=Cluster Name,Value=<cluster> \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Maximum --output text
```

### Step 4: CONNECTIVITY diagnostic (producer/consumer cannot connect)

| Client error | Root cause | Probe |
|---|---|---|
| `TimeoutException` | Security group blocking port; wrong bootstrap endpoint; cross-VPC without peering | `get-bootstrap-brokers`; check SG on brokers |
| `SSLHandshakeException` / `PKIX path building failed` | Client not trusting AWS private CA; TLS client auth not configured on client | Verify `security.protocol=SSL`; import CA cert into truststore |
| `SASL_AUTHENTICATION_FAILED` (SCRAM) | Wrong password in Secrets Manager; SCRAM not enabled; wrong mechanism | `describe-cluster ClientAuthentication.Sasl.Scram.Enabled`; verify secret |
| `SASL_AUTHENTICATION_FAILED` (IAM) | IAM principal lacks `kafka-cluster:Connect`; wrong client config | Check IAM policy with `kafka-cluster:*` actions |
| `TopicAuthorizationException` | ACL denies client principal | `kafka-acls --list --topic <topic>` |

**Walk:**

1. **Get the correct bootstrap brokers:**
   `aws kafka get-bootstrap-brokers --cluster-arn <arn>`. Different fields
   map to different auth modes (`BootstrapBrokerStringTls` = TLS port 9094,
   `BootstrapBrokerStringSaslScram` = SCRAM port 9096,
   `BootstrapBrokerStringSaslIam` = IAM port 9098).
2. **Verify security group:** the client SG must be allowed inbound on the
   correct port (9092/9094/9096/9098).
3. **Verify auth mode matches:** `describe-cluster ClientAuthentication`.
   If `Tls.Enabled=true` and `Sasl.Scram.Enabled=false`, client must use
   TLS, not SCRAM.
4. **For SCRAM:** verify the secret exists with `AmazonMSK_` prefix in
   Secrets Manager: `aws kafka list-scram-secrets --cluster-arn <arn>`.
5. **For IAM auth:** verify the IAM principal has `kafka-cluster:Connect`,
   `kafka-cluster:DescribeCluster`, `kafka-cluster:ReadData`/`WriteData`.
6. **For cross-VPC:** verify VPC peering/transit gateway routes and DNS
   resolution (private hosted zone for broker DNS names).

```bash
# Bootstrap brokers (all endpoint types):
aws kafka get-bootstrap-brokers --cluster-arn <arn>
# Client auth configuration:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.ClientAuthentication' --output json
# Broker security groups:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.BrokerNodeGroupInfo.SecurityGroups' --output text
# SCRAM secret association:
aws kafka list-scram-secrets --cluster-arn <arn>
# Verify SG inbound on broker port:
aws ec2 describe-security-groups --group-ids <broker-sg-id> \
  --query 'SecurityGroups[0].IpPermissions[*].{Port:FromPort,Source:UserIdGroupPairs}' --output table
# Test connectivity:
openssl s_client -connect <broker-dns>:9094 -servername <broker-dns>
```

### Step 5: ZOOKEEPER diagnostic (ZK-mode clusters only; KRaft has no ZK)

| Signal | Root cause | Probe |
|---|---|---|
| `ZooKeeper session expired` | Broker lost ZK heartbeat; network partition broker-to-ZK | Broker logs in CloudWatch; ZK security group |
| `AUTH_FAILED` on ZK port 2181 | `zookeeper.set.acl=true` but broker SASL ZK auth misconfigured | `describe-configuration`; check `zookeeper.set.acl` |
| Controller flapping | ZK latency spikes or ensemble degraded | CloudWatch `ZooKeeperRequestLatencyMs` |

```bash
# Verify ZK-mode vs KRaft:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.CurrentBrokerSoftwareInfo'
# ZK latency:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name ZooKeeperRequestLatencyMs \
  --dimensions Name=Cluster Name,Value=<cluster> Name=Broker ID,Value=1 \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Average,Maximum --output text
```

**Fix patterns:** ZK session from network partition — fix VPC route table.
`zookeeper.set.acl=true` causing auth failures — disable or ensure SASL
config matches. KRaft mode — no ZK to troubleshoot; metadata is in
`__cluster_metadata` topic.

### Step 6: CONFIGURATION diagnostic

| Signal | Root cause | Probe |
|---|---|---|
| `UnknownTopicOrPartitionError` | `auto.create.topics.enable=false` and topic not explicitly created | `describe-configuration`; `kafka-topics --list` |
| 1-partition topics from auto-create | `auto.create.topics.enable=true` + `num.partitions=1` | `describe-configuration` |
| Data not cleaned; disk growing | `log.retention.hours=-1` (infinite) or `log.retention.bytes` unset | `describe-configuration`; topic-level `kafka-configs --describe` |
| ISR flapping under burst | `replica.lag.time.max.ms=30000` (too low) | `describe-configuration`; raise to 60s+ |

```bash
# Read the MSK configuration:
aws kafka describe-configuration --arn <config-arn> \
  --query 'Configuration.ServerProperties' --output text | base64 --decode
# Topic-level overrides:
kafka-configs --bootstrap-server <bs> --entity-type topics --entity-name <topic> --describe
```

**Fix patterns:** Disable auto-create (`auto.create.topics.enable=false`),
create topics explicitly. Set finite retention (`log.retention.hours=168` +
`log.retention.bytes`). Raise `replica.lag.time.max.ms` for burst workloads.

### Step 7: MONITORING diagnostic

| Signal | Root cause | Probe |
|---|---|---|
| CloudWatch `AWS/Kafka` metrics absent | Enhanced monitoring not enabled or `DEFAULT` level | `describe-monitoring --cluster-arn <arn>` |
| Broker logs absent | Log delivery not configured | `describe-cluster LoggingInfo` |
| Prometheus JMX target down | Open Monitoring not enabled or Prometheus can't reach JMX port | `describe-monitoring` `OpenMonitoring.Prometheus` |

```bash
aws kafka describe-monitoring --cluster-arn <arn> \
  --query '{Jmx:MonitoringInfo.OpenMonitoring.Prometheus.JmxExporter,Node:MonitoringInfo.OpenMonitoring.Prometheus.NodeExporter}'
aws kafka describe-cluster --cluster-arn <arn> --query 'ClusterInfo.LoggingInfo'
aws logs describe-log-groups --log-group-name-prefix /aws/kafka/<cluster>
# Enable enhanced monitoring:
aws kafka update-monitoring --cluster-arn <arn> \
  --current-version <version> --enhanced-monitoring PER_BROKER
```

### Step 8: STORAGE diagnostic (EBS disk full)

| Signal | Root cause | Probe |
|---|---|---|
| `DiskUsage > 90%` | Retention too long; `log.retention.bytes` unset | CloudWatch `DiskUsage`; `describe-configuration` |
| `ERROR: Disk full`, broker read-only | Disk at 100% | CloudWatch `DiskUsage = 100`; broker logs |
| Disk full on one broker only | Partition skew concentrates data | `kafka-log-dirs --describe --topic-list <topics>` |
| Disk growing after reducing retention | Compacted topics never delete key history | `kafka-configs --describe`; check `cleanup.policy=compact` |

```bash
# Disk usage per broker:
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name DiskUsage \
  --dimensions Name=Cluster Name,Value=<cluster> \
  --start-time $(date -u -d '24 hours ago' +%FT%TZ) --end-time $(date -u +%FT%TZ) \
  --period 3600 --statistics Average,Maximum --output text
# Per-broker disk via kafka-log-dirs:
kafka-log-dirs --bootstrap-server <bs> --describe --topic-list <topics> --command-config <props>
# Broker volume size:
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.BrokerNodeGroupInfo.StorageInfo' --output json
```

**Fix patterns:** Set finite `log.retention.hours` + `log.retention.bytes`.
Increase EBS volume via MSK. Fix partition skew. For compacted topics, set
`min/max.compaction.lag.ms` or switch to `cleanup.policy=delete`.

### Step 9: Root-cause catalog

| # | Root cause | Category | Fix |
|---|---|---|---|
| 1 | Broker unhealthy (EBS failure, OOM, CPU saturation) | BROKER_FAILURE | Wait for MSK auto-replacement; scale up broker type / add brokers |
| 2 | URP from follower broker down | TOPIC_ISSUE | Fix broker (Step 2); ISR recovers automatically |
| 3 | ISR flapping from `replica.lag.time.max.ms` too aggressive | TOPIC_ISSUE | Raise to 60s+ in MSK configuration |
| 4 | Partition skew concentrates load on one broker | TOPIC_ISSUE | `kafka-preferred-replica-election` + `kafka-reassign-partitions` |
| 5 | Security group blocking client-to-broker on port 9094 | CONNECTIVITY | Add inbound rule for client SG on correct port |
| 6 | Client auth mismatch (TLS vs SCRAM vs IAM) | CONNECTIVITY | Align client `security.protocol` with cluster auth mode |
| 7 | SCRAM secret missing or wrong in Secrets Manager | CONNECTIVITY | Create/re-associate secret with `AmazonMSK_` prefix |
| 8 | IAM principal lacks `kafka-cluster:Connect` | CONNECTIVITY | Attach IAM policy with `kafka-cluster:*` actions |
| 9 | ZK session expired from network partition | ZOOKEEPER | Fix VPC route table between broker subnets |
| 10 | `auto.create.topics.enable=true` creating 1-partition topics | CONFIGURATION | Disable auto-create; create topics explicitly |
| 11 | Disk full from infinite retention | STORAGE | Set finite retention; increase EBS volume |
| 12 | Compacted topic disk growth from high key churn | STORAGE | Set compaction lag; evaluate `cleanup.policy=delete` |

### Step 10: Verify the fix and decide VERDICT

- **ROOT_CAUSE_FOUND.** The walk identified a specific failure category and
  config element. Output REMEDIATION with the exact change.
- **NEED_MORE_INFO.** Evidence is insufficient (no client tools, no metrics).
  Output the list of missing inputs.
- **ESCALATE.** Cause outside operator's scope: MSK broker replacement in
  progress, VPC/network owned by platform team, IAM owned by security team,
  or MSK Serverless throughput limits (quota increase via AWS Support).

## Output format — worked example (ISR shrink)

```text
INCIDENT: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/abcd-1234
  — UnderReplicatedPartitions=12, ISR shrinking on 3 topics
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: TOPIC_ISSUE — replica.lag.time.max.ms=30000 (default) too
  aggressive for bursty produce workload; followers ejected from ISR
  during produce spikes, rejoin 15-30s later
EVIDENCE:
  - kafka-topics --describe --under-replicated-partitions: 12 partitions
    across orders, payments, inventory; Isr missing broker 2 and 3
  - CloudWatch UnderReplicatedPartitions: Avg=12, Max=28 during bursts
  - describe-configuration: replica.lag.time.max.ms=30000 (default)
  - CloudWatch BytesInPerSec: spikes to 85 MB/s (baseline: 12 MB/s)
ROOT_CAUSE_CATALOG: #3 (ISR flapping from replica.lag.time.max.ms)
REMEDIATION:
  1. Create new configuration revision with replica.lag.time.max.ms=60000
  2. Apply: aws kafka update-cluster-configuration --cluster-arn <arn> \
       --configuration-info file://config.json --current-version <version>
  3. Monitor URP during next burst window
  4. If URP persists after 60s, investigate follower CPU/network (Step 2)
```

## Expert heuristic — "The MSK trinity"

Three signals, gathered in order, give you 80% of all MSK diagnoses:

1. **Cluster State first:** `aws kafka describe-cluster`. `State` and
   `StateInfo` tell you if MSK is aware of a problem. `ACTIVE` +
   `HEALTH_ISSUE` = broker degradation. `MAINTENANCE` = AWS is handling it.
2. **Partition health second:** `kafka-topics --describe
   --under-replicated-partitions`. URP is the definitive Kafka health
   signal. The ISR column tells you WHICH brokers are lagging.
3. **CloudWatch metrics third:** `UnderReplicatedPartitions`,
   `OfflinePartitions`, `CpuUser`, `DiskUsage`, `BytesInPerSec`. These
   confirm the diagnosis with quantitative evidence and show the trend.

Everything else (broker logs, Prometheus, network tracing, ACL audit) is
confirmatory.

### Additional non-obvious MSK behaviours

| Heuristic | Impact on diagnosis |
|---|---|
| MSK auto-replaces brokers but does NOT auto-rebalance partition leadership | After a broker replacement, check `kafka-preferred-replica-election`. The new broker rejoins ISR but may not become leader without intervention. |
| MSK configuration revisions are immutable | To change a config value, create a new revision and apply it. You cannot edit an existing revision. |
| SCRAM secrets must have the `AmazonMSK_` prefix | Secrets without this prefix are not recognized by MSK. The secret must be in the same account and region. |
| `replica.lag.time.max.ms` default is 30000ms (30s) | For bursty workloads, followers exceed this during produce spikes and get ejected from ISR, causing URP flapping. |
| MSK Serverless throttles per-partition, not per-cluster | Adding partitions increases aggregate throughput. Reducing partition count may throttle a single partition. |
| KRaft mode stores metadata in `__cluster_metadata` topic | Controller quorum issues are diagnosed via broker logs, not ZK. ZK diagnostic commands (Step 5) are N/A. |
| Express Class has no `list-nodes` or per-broker metrics | Troubleshoot via `describe-cluster-v2`, client logs, and partition-level signals. |

## NEVER (top 5)

- **NEVER** declare the root cause from cluster State alone. `HEALTH_ISSUE`
  is a symptom. Always run `kafka-topics --describe --under-replicated-partitions`
  and check CloudWatch `CpuUser` / `DiskUsage` first.

- **NEVER** assume a connectivity issue is a broker problem. 90% of "MSK
  is broken" reports are client-side: wrong auth mode, wrong bootstrap
  endpoint, SG blocking the port, or IAM policy missing. Verify the client
  config against `get-bootstrap-brokers` and `ClientAuthentication` first.

- **NEVER** confuse TLS client auth with SCRAM. TLS uses client certificates;
  SCRAM uses username/password in Secrets Manager over TLS transport. They
  are mutually exclusive at the client level. Check
  `ClientAuthentication` to see which is enabled.

- **NEVER** delete and recreate a topic to "fix" under-replicated partitions.
  Deleting permanently destroys data. Fix the broker or ISR config. URP
  resolves automatically when the follower rejoins ISR.

- **NEVER** use PLAINTEXT bootstrap brokers (port 9092) in production. Use
  TLS (9094), SCRAM (9096), or IAM (9098). PLAINTEXT sends data and
  credentials unencrypted.

## Recent AWS features (2024-2026)

- **MSK Cluster Tier (2025-2026):** Standard Class (provisioned brokers)
  and Express Class (brokerless, on-demand scaling). Express does not expose
  `list-nodes` or per-broker metrics. Troubleshooting shifts to client-side
  logs, partition-level metrics, and `describe-cluster-v2` capacity mode.
- **KRaft Mode (KIP-833, 2024-2025):** Kafka without ZooKeeper. Metadata in
  `__cluster_metadata` internal topic. Eliminates ZK session expiry, ZK auth
  issues, controller election storms. MSK supports KRaft on Kafka 3.5+.
  For KRaft clusters, Step 5 (ZOOKEEPER) is N/A.
- **MSK Serverless (2023 GA, enhanced 2024-2025):** Fully managed, brokerless,
  per-partition capacity (RCUs). Throttling is per-partition; reduce
  partition count or batch produce calls. Auto-scaling handles capacity.
- **IAM Authentication (2023-2025):** SASL/IAM auth using AWS IAM credentials.
  No SCRAM secrets to manage. Client uses `AWS_MSK_IAM` mechanism. Verify
  IAM policies include `kafka-cluster:*` actions on the cluster ARN.
- **Open Monitoring with Prometheus (2023-2025):** Native JMX exporter on
  MSK brokers. Provides fine-grained broker metrics beyond CloudWatch.
- **MSK Extended Client (2024-2025):** Enhanced Kafka client libraries with
  automatic retry, partition discovery, IAM auth. Reduces transient client
  failures from broker replacements by auto-refreshing metadata and retrying
  on `NOT_LEADER_OF_PARTITION` and `BROKER_NOT_AVAILABLE` errors.

## References

See `references/failure-decision-tree.md` for the full symptom-to-cause walk
with worked examples per category, and `references/diagnostic-commands.md`
for the canonical command script per failure category.

## Domain

AWS CloudOps / Amazon MSK Analytics Reliability & Kafka Cluster Operations.

## AWS documentation

- **Amazon MSK Developer Guide** — https://docs.aws.amazon.com/msk/latest/developerguide/what-is-msk.html
- **MSK troubleshooting** — https://docs.aws.amazon.com/msk/latest/developerguide/troubleshooting.html
- **MSK Serverless** — https://docs.aws.amazon.com/msk/latest/developerguide/serverless.html
- **MSK Cluster Tier** — https://docs.aws.amazon.com/msk/latest/developerguide/cluster-tier.html
- **MSK IAM auth** — https://docs.aws.amazon.com/msk/latest/developerguide/iam-access-control.html
- **MSK SCRAM** — https://docs.aws.amazon.com/msk/latest/developerguide/msk-password.html
- **MSK CloudWatch metrics** — https://docs.aws.amazon.com/msk/latest/developerguide/metrics-dimensions.html
- **MSK open monitoring** — https://docs.aws.amazon.com/msk/latest/developerguide/open-monitoring.html
- **KIP-833: KRaft mode** — https://cwiki.apache.org/confluence/display/KAFKA/KIP-833
- **AWS CLI Kafka reference** — https://docs.aws.amazon.com/cli/latest/reference/kafka/
