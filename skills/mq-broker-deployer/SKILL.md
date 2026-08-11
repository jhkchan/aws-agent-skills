---
name: mq-broker-deployer
description: >-
  Provisions Amazon MQ brokers with production defaults: ActiveMQ vs
  RabbitMQ engine selection, deployment mode (single-instance vs
  active/standby vs cluster), broker instance type sizing (mq.t3.micro
  to mq.m5.16xl), EBS storage with KMS encryption at-rest, TLS
  in-transit, authentication (LDAP, ActiveMQ web console, basic),
  security groups and subnet placement, public access vs private
  broker, CloudWatch alarms for broker metrics (CpuUtilization,
  MemoryUtilization, enqueueCount), message persistence, queues/topics,
  auto minor version upgrade, and maintenance window. Emits a
  READY_TO_DEPLOY checklist with verification commands. Use when
  creating an Amazon MQ broker, choosing ActiveMQ vs RabbitMQ,
  designing HA topology, sizing broker instances, wiring LDAP auth,
  or configuring CloudWatch alarms. Triggers: create Amazon MQ broker,
  provision ActiveMQ, provision RabbitMQ, Amazon MQ active/standby,
  Amazon MQ cluster, mq.t3, mq.m5, Amazon MQ LDAP, broker CloudWatch
  alarms, Amazon MQ encryption, Amazon MQ maintenance window.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with mq, ec2, kms,
  iam, and secretsmanager access. Works with Terraform aws_mq_broker /
  aws_mq_configuration resources and CloudFormation
  AWS::AmazonMQ::Broker templates.
keywords:
  - aws
  - amazon mq
  - activemq
  - rabbitmq
  - cloudops
  - deploy
  - provisioning
  - message broker
  - active/standby
  - cluster
  - single instance
  - mq.t3
  - mq.m5
  - ldap
  - iam authentication
  - mutual tls
  - cloudwatch alarms
  - cpu utilization
  - memory utilization
  - enqueue count
  - maintenance window
  - auto minor version upgrade
  - kms encryption
  - message persistence
tags:
  - aws
  - amazon-mq
  - activemq
  - rabbitmq
  - cloudops
  - deploy
  - appintegration
  - messaging
  - provisioning
  - active-standby
  - broker-cluster
  - encryption
  - cloudwatch-alarms
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: App Integration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - amazon-mq
    - activemq
    - rabbitmq
    - cloudops
    - deploy
    - appintegration
    - messaging
    - provisioning
    - active-standby
    - broker-cluster
    - encryption
    - cloudwatch-alarms
  dependencies:
    - aws-orchestrator
  keywords:
    - create amazon mq broker
    - provision activemq broker
    - provision rabbitmq broker
    - amazon mq active/standby
    - amazon mq cluster mode
    - mq.t3 micro
    - mq.m5 large
    - amazon mq ldap
    - broker cloudwatch alarms
    - amazon mq kms encryption
    - amazon mq maintenance window
    - amazon mq message persistence
  when_to_use: >-
    Invoke when the user wants to create an Amazon MQ broker (ActiveMQ
    or RabbitMQ), choose between ActiveMQ and RabbitMQ engines, design
    an active/standby or cluster deployment mode for HA, size a broker
    instance type for a given workload, configure LDAP or basic
    authentication, set up KMS encryption at-rest and TLS in-transit,
    configure CloudWatch alarms for broker metrics (CpuUtilization,
    MemoryUtilization, enqueueCount), configure a maintenance window,
    or enable auto minor version upgrades. Do NOT invoke for Amazon MSK
    (Managed Streaming for Kafka), Amazon Kinesis, Amazon SQS/SNS, or
    self-managed Kafka/RabbitMQ on EC2.
---

# MQ Broker Deployer

An AWS CloudOps agent skill that provisions Amazon MQ brokers with
correct production defaults. The skill walks the operator through
engine selection (ActiveMQ vs RabbitMQ), deployment mode (single-
instance vs active/standby vs cluster), instance type sizing, storage
and encryption, authentication (LDAP vs basic), security group and
subnet placement, CloudWatch alarms for broker metrics, maintenance
window configuration, and message persistence, captures all
deployment decisions, explains why each default matters, and emits a
READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## Activation keywords

create Amazon MQ broker, provision ActiveMQ broker, provision
RabbitMQ broker, Amazon MQ active/standby, Amazon MQ cluster mode,
Amazon MQ single instance, Amazon MQ LDAP, broker CloudWatch alarms,
Amazon MQ KMS encryption, Amazon MQ maintenance window, mq.t3,
mq.m5, Amazon MQ message persistence.

## STRICT output contract

When this skill is invoked with an Amazon-MQ-provisioning request
(create a broker, choose ActiveMQ vs RabbitMQ, design HA topology,
configure auth/encryption/alarms, or a partial configuration), the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels
`MQ_BROKER:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Engine selection (ActiveMQ vs RabbitMQ) | Core engine decision |
| Step 2 — Deployment mode | HA topology |
| Step 3 — Instance type sizing | Capacity planning |
| Step 4 — Storage volume and encryption | EBS + KMS + TLS |
| Step 5 — Authentication (LDAP vs basic) | Auth model |
| Step 6 — Network and security groups | VPC placement |
| Step 7 — Public access vs private | Exposure decision |
| Step 8 — CloudWatch alarms | Broker metric monitoring |
| Step 9 — Maintenance window and upgrades | Patching |
| Step 10 — Message persistence and destinations | Queues/topics |
| Step 11 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/engine-and-topology.md | Engine + deployment mode detail |
| references/security-and-monitoring.md | Encryption + auth + alarms detail |

## Mindset

**One-line takeaway:** Amazon MQ is a managed message broker service
supporting ActiveMQ and RabbitMQ engines. ActiveMQ supports active/
standby HA (2 brokers, one primary one standby) with automatic
failover. RabbitMQ supports cluster deployment mode (3 brokers, all
active, raft-based quorum). The engine choice is IMMUTABLE — you
cannot convert an ActiveMQ broker to RabbitMQ or vice versa; you must
recreate the broker.

Three misconceptions dominate Amazon MQ misdesign at provisioning
time:

- **"ActiveMQ cluster mode provides horizontal scale."** It does NOT.
  ActiveMQ supports only single-instance and active/standby (2-broker
  HA with one standby) deployment modes. For horizontal cluster
  scaling, RabbitMQ cluster mode (3 brokers, all active) is required.
  A baseline model may suggest "cluster mode" for ActiveMQ — that does
  not exist.

- **"Single-instance is fine for production."** It is NOT for HA-
  sensitive workloads. Single-instance has no standby; if the broker
  or its AZ fails, the broker is unavailable until AWS provisions a
  replacement (minutes to tens of minutes). For production HA, use
  active/standby (ActiveMQ) or cluster mode (RabbitMQ).

- **"Basic authentication is sufficient."** For production, basic
  username/password auth has no central identity management, no
  rotation, and no audit trail per user. LDAP (ActiveMQ) or IAM
  (RabbitMQ) provides federated identity, centralized rotation, and
  per-user audit. A production broker should use LDAP or IAM unless
  the workload is truly single-tenant.

## Configuration dependency graph (novel heuristic)

Amazon MQ broker configurations are NOT independent. The engine
choice determines which deployment modes are available. The deployment
mode determines the minimum subnet/AZ count. Authentication choice
(LDAP/IAM) requires additional directory/IAM setup. Use this graph to
sequence provisioning.

| Configuration | Hard dependencies (API error without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Engine type (ActiveMQ/RabbitMQ) | None — chosen at creation | IMMUTABLE — cannot convert after creation; must recreate broker | determines available deployment modes and protocol surface |
| Deployment mode | engine chosen; ActiveMQ = single or active/standby; RabbitMQ = single or cluster | active/standby requires 2 AZs; cluster requires 3 AZs | HA level and subnet count requirement |
| Instance type | engine chosen | type can be changed later but requires reboot | broker capacity (connections, message throughput) |
| Storage volume (EBS) | broker exists | volume size can be increased but NOT decreased; encryption set at creation | message persistence durability |
| KMS encryption at-rest | KMS key exists and policy permits mq service | encryption cannot be toggled after creation — set at broker creation | data-at-rest encryption |
| TLS in-transit | broker engine version supports TLS | TLS is enabled by default on Amazon MQ; disabling is NOT recommended | data-in-transit encryption |
| Authentication (LDAP) | LDAP server reachable from broker VPC; security group permits LDAP port (389/636) | LDAP config is set at creation; changing requires broker recreation | federated user auth for ActiveMQ |
| Authentication (IAM for RabbitMQ) | RabbitMQ engine; IAM roles/users exist | IAM auth requires `authenticationStrategy = LDAP` for RabbitMQ (despite name, it enables IAM) | federated AWS auth for RabbitMQ |
| Security group | VPC exists; SG created with correct inbound ports per protocol | SG can be modified after creation | network access control |
| Subnet placement | at least 1 subnet (single); 2 subnets in 2 AZs (active/standby); 3 subnets in 3 AZs (cluster) | subnet IDs set at creation; changing requires recreation | AZ fault isolation |
| Public access | broker created with `publiclyAccessible = true/false` | public access set at creation; changing requires recreation | broker reachable from outside VPC |
| CloudWatch alarms | broker exists; CloudWatch namespace `AWS/AmazonMQ` | alarms are separate from broker; configured via CloudWatch, not MQ API | metric-based alerting |
| Maintenance window | broker exists | window set at creation; can be modified later | controlled patch timing |
| Auto minor version upgrade | broker exists | enabled at creation; can be modified | automatic patching within maintenance window |

**The deployment-mode-determines-AZ-count row is the one a baseline
model misses.** Active/standby requires exactly 2 subnets in 2
different AZs; cluster mode requires exactly 3 subnets in 3 different
AZs. Providing fewer subnets causes a creation failure; providing
subnets in the same AZ defeats the HA purpose.

**Cross-dependency gotchas:**
- Engine choice is immutable. Always confirm ActiveMQ vs RabbitMQ
  before creating the broker. A wrong choice means full recreation.
- LDAP authentication requires network connectivity from the broker
  VPC to the LDAP/Active Directory server. Verify security group
  rules and routing before setting auth mode.
- RabbitMQ IAM authentication uses `authenticationStrategy = LDAP`
  (counterintuitive naming). This enables IAM-based auth for
  RabbitMQ, not LDAP.
- CloudWatch alarms are configured via the CloudWatch API (not the
  MQ API). The broker emits metrics to the `AWS/AmazonMQ` namespace
  automatically; alarms are a separate provisioning step.

## Expert heuristic: active/standby vs cluster multi-AZ trade-offs

A baseline model says "pick HA." The correct heuristic recognizes
that ActiveMQ and RabbitMQ have fundamentally different HA models,
and the choice cascades into AZ count, failover behavior, and
throughput.

```text
Engine: ActiveMQ
  Deployment modes:
    ├── Single-instance (1 broker, 1 AZ)
    │     No HA. AZ failure = broker down. Use for dev/test only.
    ├── Active/Standby (2 brokers, 2 AZs)
    │     One active, one standby (warm). Automatic failover on
    │     active failure. Standby has same storage (EBS replicated).
    │     No horizontal scale — throughput = single broker capacity.
    │     Requires exactly 2 subnets in 2 AZs.
    └── Cluster (NOT supported for ActiveMQ)

Engine: RabbitMQ
  Deployment modes:
    ├── Single-instance (1 broker, 1 AZ)
    │     No HA. Use for dev/test only.
    ├── Cluster (3 brokers, 3 AZs)
    │     All 3 brokers active. Raft-based quorum queues for HA.
    │     Horizontal scale — throughput scales with broker count.
    │     Automatic failover: if one broker fails, others continue.
    │     Requires exactly 3 subnets in 3 AZs.
    └── Active/Standby (NOT supported for RabbitMQ)
```

**Key implication:** ActiveMQ active/standby gives you failover but
NOT horizontal scale — the standby is warm and does not serve
traffic. RabbitMQ cluster gives you BOTH failover AND horizontal
scale. If the workload needs throughput scaling, RabbitMQ cluster is
the only option in Amazon MQ.

## Expert heuristic: LDAP vs basic auth trade-offs

```text
ActiveMQ:
  ├── Basic (username + password) — set at creation, stored in
  │     Secrets Manager. No central identity. OK for dev/test.
  ├── LDAP (Active Directory / OpenLDAP) — connects to external
  │     directory. Central identity, rotation, audit. Requires
  │     network connectivity to LDAP server (port 389 or 636).
  └── ActiveMQ Web Console — web UI auth using same credentials.

RabbitMQ:
  ├── Basic (username + password) — same trade-offs as ActiveMQ.
  ├── IAM (AWS IAM users/roles) — uses authenticationStrategy =
  │     LDAP (counterintuitive name). Users auth via AWS IAM
  │     credentials (SigV4). Central identity via IAM.
  └── mTLS (mutual TLS) — client cert auth. Strongest but highest
        operational overhead. Requires CA and client cert management.
```

**Key implication:** for production, LDAP (ActiveMQ) or IAM
(RabbitMQ) eliminates password management and provides audit per
user. Basic auth is acceptable for dev/test but creates a credential
rotation burden in production.

## Expert heuristic: instance type sizing by workload

```text
mq.t3.micro   — 2 vCPU, 1 GiB    — dev/test, <100 connections
mq.t3.small   — 2 vCPU, 2 GiB    — small prod, <500 connections
mq.m5.large   — 2 vCPU, 8 GiB    — prod, ~1,000 connections
mq.m5.xlarge  — 4 vCPU, 16 GiB   — prod, ~2,000 connections
mq.m5.2xlarge — 8 vCPU, 32 GiB   — high-throughput, ~4,000 connections
mq.m5.4xlarge — 16 vCPU, 64 GiB  — heavy prod, ~8,000 connections
mq.m5.8xlarge — 32 vCPU, 128 GiB — very heavy, ~15,000 connections
mq.m5.16xlarge— 64 vCPU, 256 GiB — max capacity, ~30,000 connections

Throughput (approximate, 1 KB messages):
  mq.m5.large: ~5,000 msg/sec | mq.m5.2xlarge: ~15,000 | mq.m5.4xlarge: ~30,000
```

**Key implication:** size by peak connection count and message rate,
not average. Broker CPU and memory utilization should stay below 70%
under peak load to allow for GC spikes and failover headroom. Set
CloudWatch alarms at 80% CpuUtilization and 80% MemoryUtilization.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| VPC exists | Broker must be placed in a VPC | `aws ec2 describe-vpcs --vpc-ids <vpc-id>` |
| Subnet(s) in correct AZ count | single = 1; active/standby = 2 AZs; cluster = 3 AZs | `aws ec2 describe-subnets --subnet-ids <subnet-ids>` |
| Security group with correct ports | Inbound ports per protocol (OpenWire 61617, AMQP 5671, STOMP 61614, MQTT 8883, Console 8162) | `aws ec2 describe-security-groups --group-ids <sg-id>` |
| Engine decision (ActiveMQ vs RabbitMQ) | Immutable after creation | Confirm with operator |
| Deployment mode decision | Determines AZ/subnet count | Confirm with operator |
| KMS key (if custom CMK) | Encryption at-rest uses this key; must permit mq service | `aws kms describe-key --key-id <key-id>` |
| LDAP server reachable (if LDAP auth) | Broker must reach LDAP server on 389/636 | Verify SG rules and routing |
| IAM users/roles defined (if RabbitMQ IAM) | IAM auth requires pre-existing IAM identities | `aws iam list-users` / `list-roles` |
| Broker name and instance type | Required at creation | Confirm with operator |
| Region identified | Broker is regional | `aws configure get region` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Engine selection (ActiveMQ vs RabbitMQ)

| Feature | ActiveMQ | RabbitMQ |
|---|---|---|
| Protocols | OpenWire, AMQP, STOMP, MQTT, WS | AMQP 0-9-1, MQTT, STOMP |
| HA modes | Single-instance, Active/Standby | Single-instance, Cluster |
| Horizontal scale | NO (standby is warm) | YES (cluster, all active) |
| Failover | Active/standby (warm standby, automatic) | Cluster (quorum queues, automatic) |
| Auth | Basic, LDAP, Web Console | Basic, IAM, mTLS |
| Configuration | XML (broker.xml overrides) | Definitions JSON |
| Best for | JMS apps, multi-protocol, legacy integration | High-throughput AMQP, horizontal scale, microservices |

**Engine choice is IMMUTABLE.** Once a broker is created as
ActiveMQ, it cannot be converted to RabbitMQ (or vice versa). A new
broker must be created and messages migrated.

## Step 2 — Deployment mode

| Mode | Engines | Brokers | AZs | HA | Horizontal scale |
|---|---|---|---|---|---|
| Single-instance | Both | 1 | 1 | No | No |
| Active/Standby | ActiveMQ only | 2 | 2 | Yes (warm standby) | No |
| Cluster | RabbitMQ only | 3 | 3 | Yes (quorum) | Yes |

**Active/Standby (ActiveMQ):** 2 brokers in 2 AZs. One is active
(primary), one is standby (warm replica). EBS storage is replicated.
On active failure, standby is promoted automatically. The standby
does NOT serve client traffic — it is warm only.

**Cluster (RabbitMQ):** 3 brokers in 3 AZs, all active. Uses quorum
queues (Raft consensus) for HA. Throughput scales with broker count.
If one broker fails, the other two continue serving traffic.

## Step 3 — Instance type sizing

| Type | vCPU | RAM | Connections (approx) | Use case |
|---|---|---|---|---|
| mq.t3.micro | 2 | 1 GiB | <100 | Dev/test |
| mq.t3.small | 2 | 2 GiB | <500 | Small prod |
| mq.m5.large | 2 | 8 GiB | ~1,000 | Production |
| mq.m5.xlarge | 4 | 16 GiB | ~2,000 | Production |
| mq.m5.2xlarge | 8 | 32 GiB | ~4,000 | High-throughput |
| mq.m5.4xlarge | 16 | 64 GiB | ~8,000 | Heavy prod |
| mq.m5.8xlarge | 32 | 128 GiB | ~15,000 | Very heavy |
| mq.m5.16xlarge | 64 | 256 GiB | ~30,000 | Max capacity |

**Sizing rule:** size by peak (not average) connections and message
rate. Target <70% CPU and memory under peak load.

## Step 4 — Storage volume and encryption

**EBS storage:** each broker has an EBS volume for message
persistence. Default 100 GiB; can be increased (not decreased).

```bash
# Create broker with 200 GiB EBS, KMS-encrypted
aws mq create-broker \
  --broker-name prod-mq \
  --engine-type ActiveMQ \
  --engine-version 5.18.0 \
  --host-instance-type mq.m5.large \
  --deployment-mode ACTIVE_STANDBY \
  --storage-type ebs \
  --storage-volume-size 200 \
  --encryption-options '{"UseAwsOwnedKey": false, "KmsKeyId": "alias/prod-mq-kms"}' \
  ...
```

**KMS encryption at-rest:** set at creation. Cannot be toggled after
creation. Use a customer-managed CMK for production (not the
AWS-owned key).

**TLS in-transit:** enabled by default on Amazon MQ. All broker
endpoints are TLS-secured (ports with `ssl` suffix: 61617, 5671,
61614, 8883). Disabling TLS is NOT recommended.

## Step 5 — Authentication (LDAP vs basic)

**Basic auth (both engines):** credentials set at creation, stored in
AWS Secrets Manager.

```bash
aws mq create-broker \
  --broker-name prod-mq \
  --users '[{"Username": "admin", "Password": "<password>", "ConsoleAccess": true, "Groups": ["admin"]}]'
```

**LDAP auth (ActiveMQ):** configured via broker configuration XML
override (broker.xml with `LdapLoginModule`). Requires network
connectivity to LDAP server on ports 389/636.

**IAM auth (RabbitMQ):** uses `authenticationStrategy = LDAP`
(counterintuitive — the strategy name is "LDAP" but it enables IAM
for RabbitMQ).

```bash
aws mq create-broker \
  --broker-name prod-rmq \
  --engine-type RabbitMQ \
  --authentication-strategy LDAP
```

## Step 6 — Network and security groups

**Subnet placement by deployment mode:**

```bash
# Active/standby: 2 subnets in 2 AZs
aws mq create-broker ... --subnet-ids subnet-aaa subnet-bbb --security-groups sg-mq123

# Cluster (RabbitMQ): 3 subnets in 3 AZs
aws mq create-broker ... --subnet-ids subnet-aaa subnet-bbb subnet-ccc --security-groups sg-rmq456
```

**Security group inbound ports by protocol:**

| Protocol | ActiveMQ port | RabbitMQ port | Console port |
|---|---|---|---|
| OpenWire (TLS) | 61617 | — | — |
| AMQP (TLS) | 5671 | 5671 | — |
| STOMP (TLS) | 61614 | 61614 | — |
| MQTT (TLS) | 8883 | 8883 | — |
| WSS (WebSocket TLS) | 61619 | 61619 | — |
| Web Console | — | — | 8162 (ActiveMQ) / 15671 (RabbitMQ) |

## Step 7 — Public access vs private

```text
Publicly accessible (publiclyAccessible = true):
  Broker gets a public endpoint. Reachable from outside the VPC.
  Risk: broker is internet-exposed. Mitigate with TLS + strong auth.

Private (publiclyAccessible = false):
  Broker only reachable from within the VPC (or via peering/TGW/VPN).
  Recommended default for production.
```

## Step 8 — CloudWatch alarms for broker metrics

Amazon MQ emits metrics to the `AWS/AmazonMQ` CloudWatch namespace.
Configure alarms for the critical broker metrics.

| Metric | Alarm threshold | What it indicates |
|---|---|---|
| CpuUtilization | > 80% for 5 min | Broker CPU near saturation; consider larger instance |
| MemoryUtilization | > 80% for 5 min | Broker memory near saturation; JVM heap pressure |
| EnqueueCount | Low or zero (unexpected) | Producers not sending messages; check connectivity |
| DequeueCount | Low or zero (unexpected) | Consumers not processing; check consumer health |
| QueueSize | Growing over time | Consumers can't keep up; backlog building |
| TotalConsumerCount | Drops to zero | All consumers disconnected; check consumer infra |
| TotalProducerCount | Drops to zero | All producers disconnected; check producer infra |

```bash
# Pattern: replicate this block for each metric (CpuUtilization,
# MemoryUtilization, EnqueueCount). Change --metric-name, --threshold,
# and --comparison-operator per the table above.
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-high-cpu" \
  --metric-name CpuUtilization \
  --namespace AWS/AmazonMQ \
  --statistic Average \
  --period 300 \
  --threshold 80 \
  --comparison-operator GreaterThanThreshold \
  --evaluation-periods 1 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"
```

## Step 9 — Maintenance window and auto minor version upgrade

**Auto minor version upgrade:** Amazon MQ can automatically apply
minor engine version upgrades during the maintenance window. Enabled
by default. Recommended for production.

```bash
aws mq create-broker \
  ... \
  --auto-minor-version-upgrade \
  --maintenance-window-start-time \
    '{"DayOfWeek": "SUNDAY", "TimeOfDay": "03:00", "TimeZone": "UTC"}'
```

**Maintenance window:** a recurring weekly window (day, time, time
zone) during which Amazon MQ applies pending updates. The broker may
briefly fail over during the window (active/standby and cluster
brokers handle this gracefully).

## Step 10 — Message persistence and destinations

**Message persistence:** messages are persisted to the broker's EBS
volume. On active/standby failover, the standby has a replicated copy
of the EBS volume, so messages survive failover. On cluster
(RabbitMQ), quorum queues replicate across all 3 brokers.

```text
ActiveMQ destinations:
  ├── Queue (point-to-point): one consumer gets each message.
  ├── Topic (pub/sub): all active subscribers get each message.
  │     Durable subscribers get messages even if disconnected.
  └── Created via: JMS API, broker.xml, or ActiveMQ Web Console.

RabbitMQ destinations:
  ├── Quorum queue (HA, Raft-replicated) — recommended.
  ├── Stream (append-only log, high-throughput replay).
  ├── Exchange (routes to queues: direct, topic, fanout, headers).
  └── Created via: AMQP API or definitions.json import.
```

## Step 11 — Recent features

- **RabbitMQ 3.13+ quorum queue maturity (2023-2024):** quorum queues
  now recommended HA queue type, replacing deprecated mirrored classic
  queues. Raft consensus replication across 3-broker cluster.

- **ActiveMQ 5.18 LTS (2023-2024):** current LTS version with JVM 17
  support, improved OpenWire performance, and security fixes.

- **RabbitMQ streams (2024-2025):** append-only logs with replay for
  high-throughput scenarios (event sourcing, audit logs).

- **Enhanced CloudWatch metrics (2024-2025):** per-queue metrics
  (QueueSize, EnqueueCount, DequeueCount per queue) now available.

- **Maintenance window flexibility (2024-2025):** maintenance window
  can now be modified after creation (previously required recreation).

## NEVER do these things

1. **NEVER assume ActiveMQ supports cluster deployment mode.**
   ActiveMQ supports only single-instance and active/standby. Cluster
   mode (3+ active brokers) is RabbitMQ only. Suggesting ActiveMQ
   cluster will fail at creation.

2. **NEVER create a production broker in single-instance mode.**
   Single-instance has no standby. AZ failure = broker down. For
   production HA, use active/standby (ActiveMQ) or cluster
   (RabbitMQ).

3. **NEVER provide fewer subnets than the deployment mode requires.**
   Active/standby requires exactly 2 subnets in 2 AZs; cluster
   requires exactly 3 subnets in 3 AZs. Fewer subnets = creation
   failure.

4. **NEVER use basic authentication for production without a rotation
   plan.** Basic auth has no central identity or audit per user. Use
   LDAP (ActiveMQ) or IAM (RabbitMQ) for federated identity and
   audit.

5. **NEVER forget the security group inbound ports for the protocols
   in use.** Each protocol (OpenWire, AMQP, STOMP, MQTT, WSS,
   Console) uses a different port. Missing a port = clients cannot
   connect.

6. **NEVER assume RabbitMQ IAM auth uses `authenticationStrategy =
   IAM`.** The strategy name is `LDAP` (counterintuitive). Setting
   `authenticationStrategy = LDAP` on a RabbitMQ broker enables IAM
   auth, not LDAP.

7. **NEVER disable TLS on an Amazon MQ broker.** TLS is enabled by
   default. Disabling it exposes message payloads in transit. All
   production brokers must use TLS.

8. **NEVER use the AWS-owned KMS key for production brokers.** Use a
   customer-managed CMK with a defined rotation policy and key
   policy. The AWS-owned key cannot be audited or controlled.

9. **NEVER set CloudWatch alarms only on CpuUtilization.** A broker
   can fail with normal CPU (e.g., consumer disconnect causing queue
   backlog). Monitor CpuUtilization, MemoryUtilization, EnqueueCount,
   DequeueCount, QueueSize, and consumer/producer counts.

10. **NEVER forget that engine choice is immutable.** Once created as
    ActiveMQ or RabbitMQ, the broker cannot be converted. Confirm the
    engine choice before creating the broker. A wrong choice means
    full recreation and message migration.

## Output format

```text
MQ_BROKER: <broker-name> (<engine-type>, <deployment-mode>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Engine: ActiveMQ | RabbitMQ
  [✓|✗] Deployment mode: Single-Instance | Active/Standby | Cluster
  [✓|✗] Instance type: <type> (<vCPU> vCPU, <RAM> GiB; ~<connections> connections)
  [✓|✗] Storage: <size> GiB EBS (encrypted with <kms-key>)
  [✓|✗] Encryption at-rest: Enabled (CMK <key-alias>) | AWS-owned key
  [✓|✗] Encryption in-transit (TLS): Enabled
  [✓|✗] Authentication: Basic | LDAP (<server>) | IAM (RabbitMQ)
  [✓|✗] Security group: <sg-id> (inbound <port-list>)
  [✓|✗] Subnet placement: <subnet-ids> (<az-count> AZs)
  [✓|✗] Public access: Private | Public
  [✓|✗] CloudWatch alarms: CpuUtilization, MemoryUtilization, EnqueueCount
  [✓|✗] Auto minor version upgrade: Enabled (maintenance window: <window>)
  [✓|✗] Maintenance window: <day> <time> <tz>
  [✓|✗] Message persistence: EBS volume (<size> GiB) | quorum queue replication
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws mq describe-broker --broker-id <broker-name>
  aws cloudwatch describe-alarms --alarm-names <alarm-names>
  aws kms describe-key --key-id <key-alias>
```

### Worked example — ActiveMQ active/standby with LDAP

```text
MQ_BROKER: prod-mq (ActiveMQ, Active/Standby)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: ActiveMQ
  [✓] Deployment mode: Active/Standby (standby in us-east-1b)
  [✓] Instance type: mq.m5.large (2 vCPU, 8 GiB; ~1,000 connections)
  [✓] Storage: 200 GiB EBS (encrypted with CMK alias/prod-mq-kms)
  [✓] Encryption at-rest: Enabled (CMK alias/prod-mq-kms)
  [✓] Encryption in-transit (TLS): Enabled
  [✓] Authentication: LDAP (Managed AD d-1234567890)
  [✓] Security group: sg-mq123 (inbound 61617, 5671, 8162)
  [✓] Subnet placement: subnet-aaa, subnet-bbb (2 AZs)
  [✓] Public access: Private
  [✓] CloudWatch alarms: CpuUtilization >80%, MemoryUtilization >80%, EnqueueCount anomaly
  [✓] Auto minor version upgrade: Enabled
  [✓] Maintenance window: SUN 03:00 UTC
  [✓] Message persistence: EBS volume (200 GiB, replicated to standby)
  [✓] Tags: Environment=production, App=order-processing
VERIFICATION_COMMANDS:
  aws mq describe-broker --broker-id prod-mq
  aws cloudwatch describe-alarms --alarm-names prod-mq-high-cpu prod-mq-high-memory prod-mq-no-enqueues
  aws kms describe-key --key-id alias/prod-mq-kms
```

## Error handling

### Broker creation fails: "insufficient subnets for deployment mode"
- Active/standby requires 2 subnets in 2 different AZs; cluster
  requires 3 subnets in 3 different AZs. Verify subnet AZ distribution.

### Broker stuck in CREATION_FAILED
- Check KMS key policy — the key must permit the Amazon MQ service
  principal. Check security group inbound rules allow internal
  communication ports.

### LDAP auth fails
- Verify network connectivity from the broker VPC to the LDAP server.
  Check security group outbound rules from broker SG to LDAP SG
  (ports 389/636). Verify LDAP server is reachable and credentials
  are correct.

### RabbitMQ IAM auth not working
- The `authenticationStrategy` must be set to `LDAP` (counterintuitive
  name) for RabbitMQ IAM auth. Verify IAM users/roles have
  `mq:Connect` permission via the broker resource policy.

### High CpuUtilization alarm fires
- Broker CPU near saturation. Consider upgrading instance type
  (`mq.m5.xlarge` or higher). Check for runaway producers or
  inefficient consumers holding connections open.

### High MemoryUtilization alarm fires
- JVM heap pressure. May indicate large message backlog. Check
  QueueSize metric. Consider increasing instance type or adding more
  consumers.

## Domain

AWS CloudOps / Amazon MQ Broker Provisioning & Managed Messaging.

## AWS documentation

- **Amazon MQ Developer Guide** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/welcome.html
- **Create broker (CLI)** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-creating-broker-cli.html
- **ActiveMQ deployment modes** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-broker-architecture.html
- **RabbitMQ cluster** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/rabbitmq-broker-architecture.html
- **Authentication (LDAP/IAM)** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-authentication.html
- **Encryption** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-encryption.html
- **CloudWatch metrics** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-cloudwatch-metrics.html
- **Maintenance window** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-maintenance-window.html
- **Broker instance types** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-broker-instance-types.html
