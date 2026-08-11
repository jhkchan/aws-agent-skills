# End-to-end usage scenario: kafka-msk-troubleshooter

A walkthrough showing the skill diagnosing under-replicated partitions from
ISR flapping caused by an aggressive `replica.lag.time.max.ms` setting.
This exercises Step 1 (symptom identification), Step 3 (TOPIC_ISSUE), and
the remediation workflow.

## Input (user prompt)

> Our MSK cluster `prod-msk` in us-east-1 has UnderReplicatedPartitions
> spiking to 28 during business hours. The ISR drops from 3 to 1 on
> ~28 partitions, then recovers within 15 minutes. Cluster State is ACTIVE.
> All brokers are HEALTHY. The produce rate spikes from 12 MB/s to 85 MB/s
> during these windows. `replica.lag.time.max.ms` is at the default 30000ms.

## Skill output

```text
INCIDENT: arn:aws:kafka:us-east-1:111111111111:cluster/prod-msk/abcd-1234
  — UnderReplicatedPartitions=28, ISR shrinking during produce bursts
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: TOPIC_ISSUE — replica.lag.time.max.ms=30000 (default) too
  aggressive for bursty produce workload; followers ejected from ISR
  during produce spikes, rejoin 15-30s later
EVIDENCE:
  - aws kafka describe-cluster: State=ACTIVE, all brokers HEALTHY
  - kafka-topics --describe --under-replicated-partitions: 28 partitions
    across orders, payments, inventory; Isr missing broker 2 and 3
  - CloudWatch UnderReplicatedPartitions: Avg=12, Max=28 during bursts
  - CloudWatch BytesInPerSec: spikes to 85 MB/s (baseline: 12 MB/s)
  - describe-configuration: replica.lag.time.max.ms=30000 (default)
ROOT_CAUSE_CATALOG: #3 (ISR flapping from replica.lag.time.max.ms)
REMEDIATION:
  1. Create a new MSK configuration revision with replica.lag.time.max.ms=60000:
     aws kafka create-configuration --name "prod-msk-config-v2" \
       --server-properties file://updated.properties \
       --kafka-versions "3.5.1"
  2. Apply the configuration to the cluster:
     aws kafka update-cluster-configuration --cluster-arn <arn> \
       --configuration-info file://config.json --current-version <version>
  3. Monitor URP during the next burst window:
     aws cloudwatch get-metric-statistics \
       --namespace AWS/Kafka --metric-name UnderReplicatedPartitions \
       --dimensions Name=Cluster Name,Value=prod-msk \
       --start-time <burst-start> --end-time <burst-end> \
       --period 60 --statistics Sum,Maximum --output text
  4. If URP persists after raising to 60s, investigate follower broker
     CPU/network (Step 2) and consider adding a broker or scaling up.
```

## What the skill caught that a generic assistant misses

1. **The burst-correlated ISR flapping signature.** A generic assistant
   often attributes URP to "broker problems" or "network issues." The
   skill recognises that URP spiking during produce bursts and self-
   recovering is the classic `replica.lag.time.max.ms` too-aggressive
   pattern (catalog #3).

2. **The trinity diagnostic order.** The skill checks cluster State first
   (ACTIVE = not a broker failure), then URP (28 = TOPIC_ISSUE), then
   CloudWatch metrics (CpuUser normal = not CPU saturation). This
   eliminates BROKER_FAILURE before reaching the configuration diagnosis.

3. **Configuration-level root cause.** A generic assistant rarely looks at
   `replica.lag.time.max.ms`. The skill reads the MSK configuration via
   `describe-configuration` and identifies the default 30000ms as the
   problem for this workload pattern.

4. **Immutable configuration revision.** The skill knows MSK configurations
   are immutable — you must create a new revision and apply it, not edit
   the existing one. A generic assistant may suggest "just change the
   setting" without the revision workflow.

## Slash-command invocation

```
/aws:troubleshoot-kafka-msk
```

Or via the orchestrator:

```
/aws:pipeline
You: "MSK cluster prod-msk has under-replicated partitions spiking during business hours"
```

The orchestrator emits `[Phase: Troubleshoot | Skills routed:
kafka-msk-troubleshooter]` and hands off to this skill for the VERDICT.

## Live-cluster diagnostic flow (requires AWS CLI + Kafka client tools)

When the operator has AWS credentials and Kafka client tools:

```bash
# Capture the cluster State.
aws kafka describe-cluster --cluster-arn <arn> \
  --query 'ClusterInfo.{State:State,StateInfo:StateInfo}'

# Check under-replicated partitions.
kafka-topics --bootstrap-server <bs> --describe --under-replicated-partitions

# Read the MSK configuration.
aws kafka describe-configuration --arn <config-arn> \
  --query 'Configuration.ServerProperties' --output text | base64 --decode

# Check CloudWatch metrics during the burst window.
aws cloudwatch get-metric-statistics \
  --namespace AWS/Kafka --metric-name UnderReplicatedPartitions \
  --dimensions Name="Cluster Name",Value=prod-msk \
  --start-time $(date -u -d '1 hour ago' +%FT%TZ) \
  --end-time $(date -u +%FT%TZ) \
  --period 300 --statistics Sum,Average,Maximum --output text

# Apply the fix: new config revision with replica.lag.time.max.ms=60000.
echo "replica.lag.time.max.ms=60000" > updated.properties
aws kafka create-configuration --name "prod-msk-config-v2" \
  --server-properties file://updated.properties \
  --kafka-versions "3.5.1"
```

The single configuration change (`replica.lag.time.max.ms` 30000 to 60000)
plus the burst-correlated URP pattern confirms the diagnosis without
needing broker-level forensics.
