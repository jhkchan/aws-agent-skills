---
name: amazon-mq-broker-deployer
description: 'Provisions Amazon MQ brokers (ActiveMQ or RabbitMQ) with production defaults: engine selection (ActiveMQ for JMS/OpenWire/STOMP/MQTT/AMQP/WS, RabbitMQ for AMQP 0-9-1/MQTT/STOMP high-throughput), deployment mode (single instance, active/standby HA, cluster for RabbitMQ horizontal scale), instance type sizing (mq.t3.micro to mq.m5.16xl), EBS storage with KMS encryption, VPC networking, authentication (LDAP, AWS IAM for RabbitMQ, mTLS), configuration (ActiveMQ XML, RabbitMQ definitions JSON), automatic minor version upgrades, CloudWatch general and audit logs, RabbitMQ transit gateway cross-account. Emits a READY_TO_DEPLOY checklist with verification commands. Use when creating an Amazon MQ broker, choosing ActiveMQ vs RabbitMQ, designing HA topology, wiring RabbitMQ IAM auth, or generating provisioning CLI / IaC templates. Triggers: create Amazon MQ, provision ActiveMQ, provision RabbitMQ, Amazon MQ active/standby, mq.t3, mq.m5, Amazon MQ LDAP, RabbitMQ IAM auth, transit gateway, audit logging.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with mq, ec2, kms, iam, and secretsmanager access. Works with Terraform aws_mq_broker / aws_mq_configuration resources and CloudFormation AWS::AmazonMQ::Broker templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, amazon-mq, activemq, rabbitmq, cloudops, deploy, appintegration, messaging, provisioning, active-standby, broker-cluster, encryption, audit-logging
  dependencies: aws-orchestrator
  keywords: aws, amazon mq, activemq, rabbitmq, cloudops, deploy, provisioning, message broker, active/standby, cluster, single instance, mq.t3, mq.m5, ldap, iam authentication, mutual tls, stomp, mqtt, amqp, ws, openwire, transit gateway, audit logging, broker.xml, definitions json, automatic minor version upgrade
  when_to_use: Invoke when the user wants to create a new Amazon MQ broker (ActiveMQ or RabbitMQ), design an active/standby HA topology, choose between ActiveMQ and RabbitMQ for a workload, wire RabbitMQ with AWS IAM authentication, configure ActiveMQ with LDAP / JAAS, enable audit logging, size broker instance types, set up cross-account access via transit gateway, harden a broker before production (encryption, MUTUAL TLS, audit logs), or generate provisioning CLI commands / IaC templates. Do NOT invoke for self-managed ActiveMQ / RabbitMQ on EC2, Amazon MSK (Kafka), Amazon SNS/SQS, or Amazon MQ event auditing (use amazon-mq-broker-auditor).
---

# Amazon MQ Broker Deployer

An AWS CloudOps agent skill that provisions Amazon MQ brokers (ActiveMQ or
RabbitMQ) with correct defaults. The skill walks the operator through a
10-step provisioning procedure, captures the operator's engine, topology,
security, and capacity decisions, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification commands.

## What this skill does

Provisions Amazon MQ brokers with production-grade defaults across engine
(ActiveMQ vs RabbitMQ), deployment mode (single instance, active/standby,
cluster), instance type, EBS storage with KMS encryption, VPC networking,
authentication (LDAP, IAM, mTLS), configuration (XML / definitions JSON),
automatic minor version upgrades, and CloudWatch general + audit logging.
The output is a READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create Amazon MQ, provision ActiveMQ, provision RabbitMQ, Amazon MQ
deployment, active/standby broker, cluster deployment, single instance
broker, broker instance type, mq.t3.micro, mq.m5.large, mq.m5.16xl,
Amazon MQ LDAP, RabbitMQ IAM authentication, mutual TLS, broker.xml,
definitions JSON, STOMP, MQTT, AMQP, WS, OpenWire, Amazon MQ audit
logging, automatic minor version upgrade, transit gateway, Amazon MQ
encryption, Amazon MQ KMS.

## Invocation contract (hard requirement)

When this skill is invoked with a broker-provisioning request (broker
name, engine choice, workload shape, region, or a partial configuration),
the agent MUST respond with the READY_TO_DEPLOY checklist defined in
§"Output format" using the literal all-caps labels `BROKER:`, `VERDICT:`,
`CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface the checklist
with prose, headings, or disclaimers — emit the block as the first lines
of the response. This contract is what assertion-based evals and
downstream provisioning pipelines rely on; deviating from the literal
labels breaks automation silently.

## Mindset

**One-line takeaway:** Amazon MQ correctness is decided at creation time.
Engine choice (ActiveMQ vs RabbitMQ), deployment mode (single instance vs
active/standby vs cluster), and the encryption + authentication bundle
are impossible or disruptive to change later — the provisioning procedure
treats each as a one-way door and forces an explicit decision before the
`create-broker` call.

Three misconceptions dominate Amazon MQ misdesign at provisioning time:

- **"ActiveMQ and RabbitMQ are interchangeable message brokers."** This
  is wrong at the protocol and semantics level. ActiveMQ supports
  OpenWire, STOMP, MQTT, AMQP, and WS — five wire-level protocols with
  JMS-style durable subscribers, queue browsers, and virtual topics.
  RabbitMQ supports AMQP 0-9-1, AMQP 1.0, MQTT, and STOMP with
  exchanges (direct, fanout, topic, headers), queue bindings, and
  consumer prefetch. The client libraries, topology model, and retry
  semantics differ. Migrating between engines is a full application
  rewrite, not a reconfiguration.

- **"Single instance is the safe default for dev — easy to upgrade
  later."** The deployment mode is set at creation. Going from single
  instance to active/standby is a `reboot-broker` that causes downtime.
  Going from active/standby to cluster (RabbitMQ only) requires deleting
  and recreating the broker. For any production workload, default to
  active/standby up front.

- **"Audit logging is optional; enable it if compliance asks."** Amazon
  MQ audit logs capture every administrative and publish/subscribe
  action. Enabling them post-creation is possible but the gap between
  creation and enablement is an unaudited window. For regulated
  workloads (PCI-DSS, HIPAA, FedRAMP), enable general AND audit logs at
  creation.

## Quick navigation

| Section | When to read |
|---|---|
| §"Prerequisites" | Always — verify before provisioning |
| §"Step 1 — Engine selection" | Picking ActiveMQ vs RabbitMQ |
| §"Step 2 — Deployment mode" | Single instance vs active/standby vs cluster |
| §"Step 3 — Instance type sizing" | Picking mq.t3 / mq.m5 |
| §"Step 4 — Storage + KMS encryption" | EBS, encryption at rest |
| §"Step 5 — Network + security" | VPC, subnet, security group, ports |
| §"Step 6 — Authentication" | LDAP, IAM, mTLS |
| §"Step 7 — Configuration" | XML for ActiveMQ, definitions JSON for RabbitMQ |
| §"Step 8 — Logs" | CloudWatch general + audit logs |
| §"Step 9 — Upgrades + maintenance" | Automatic minor version upgrades |
| §"Step 10 — Transit gateway / protocols" | Latest 2024-2026 features |
| §"NEVER do these things" | Review before signing off |
| §"Output format" | The literal checklist template |
| references/engine-and-topology.md | Deep ActiveMQ-vs-RabbitMQ + topology |
| references/provisioning-cli-commands.md | Copy-pasteable CLI sequence |

## Reasoning framework (why provisioning order matters)

Amazon MQ configurations have **dependency and immutability semantics**
that make the provisioning order non-trivial:

1. **Engine BEFORE the first message** — ActiveMQ and RabbitMQ are NOT
   interchangeable. Protocol surface, topology model, and client
   libraries differ entirely. Migration is a full application rewrite.
2. **Deployment mode BEFORE production traffic** — single instance has
   no failover. Active/standby → cluster conversion requires broker
   deletion + recreation. Single → active/standby triggers a
   `reboot-broker` with downtime.
3. **Encryption + authentication BEFORE the first production message** —
   enabling TLS post-creation triggers `reboot-broker`. IAM auth is
   creation-time-only for RabbitMQ.
4. **Subnet BEFORE active/standby** — HA requires >=2 AZs. A single-AZ
   subnet silently prevents HA placement.
5. **Instance type BEFORE production traffic** — changing type later
   requires `reboot-broker` (downtime).
6. **Configuration BEFORE the broker** — create via
   `create-configuration` first, reference at `create-broker` via
   `--configuration`.

## Amazon MQ configuration dependency graph (novel heuristic)

Many Amazon MQ configurations are **immutable** after creation or
silently downgrade. The four load-bearing rows — engine, deployment
mode (active/standby → cluster), IAM auth for RabbitMQ, and
configuration revision semantics — are decided at creation time. The
procedure forces an explicit decision on each before `create-broker`.

| Configuration | Immutability / silent failure |
|---|---|
| Engine (ActiveMQ / RabbitMQ) | **IMMUTABLE** — migration = full broker swap + client rewrite |
| Deployment mode (single → active/standby) | `reboot-broker` with downtime; active/standby → cluster requires delete + recreate |
| IAM auth (RabbitMQ) | **Creation-time-only** — cannot add to existing broker without recreation |
| Encryption in transit (TLS) | Enabling post-creation triggers `reboot-broker` (client disconnects) |
| Subnet AZs | Single-AZ subnet silently blocks active/standby HA placement |
| Configuration revision | Immutable once applied; changes require new revision + reboot |
| Audit logging | Can be enabled post-creation (gap = unaudited window) |

**Cross-dependency gotchas:**
- ActiveMQ active/standby uses shared EBS replication — the standby
  does NOT accept connections until promoted (5-15 minutes). Clients
  must use `failover:(ssl://...)` URI for automatic reconnect.
- RabbitMQ cluster mode requires 3 brokers minimum (quorum). A 2-node
  cluster loses quorum on any single failure.
- IAM authentication for RabbitMQ is creation-time-only. A basic-auth
  broker CANNOT be converted to IAM auth without recreation.

## Expert heuristic: instance type and connection sizing

Amazon MQ markets instance types by vCPU and memory, but the limiting
factor is **connection count** and **message throughput**, not raw
memory. Size by connections first, throughput second, memory third.

| Instance type | Memory | ActiveMQ connections | RabbitMQ connections | Approx throughput |
|---|---|---|---|---|
| mq.t3.micro | 1 GiB | ~1,000 | ~500 | ~100-200 msg/s |
| mq.m5.large | 8 GiB | ~1,000 | ~2,000 | ~1,000-5,000 msg/s |
| mq.m5.2xlarge | 32 GiB | ~3,000 | ~10,000 | ~5,000-30,000 msg/s |
| mq.m5.4xlarge | 64 GiB | ~5,000 | ~20,000 | ~10,000-60,000 msg/s |
| mq.m5.16xlarge | 256 GiB | ~15,000 | — | ~30,000+ msg/s |

**Common mistake:** sizing by memory. A 64 GiB broker at 5,000
connections is CPU-bound on connection management long before memory
fills. See references/engine-and-topology.md for full failover
semantics (ActiveMQ 5-15 min EBS promotion; RabbitMQ 10-30 sec quorum
election) and detailed sizing tables.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING** with a
specific gap citation.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| AWS account with Amazon MQ access | Can't provision without it | `aws sts get-caller-identity` |
| Region selected | Brokers, configurations, logs are region-scoped | `aws configure get region` |
| VPC ID + at least 2 subnets in different AZs (for active/standby) | Amazon MQ is VPC-only; HA requires multi-AZ | `aws ec2 describe-subnets --filters "Name=vpc-id,Values=<vpc>"` — confirm >=2 distinct `AvailabilityZone` values |
| Broker name unique in this account+region | Names are account+region-unique | `aws mq describe-broker --broker-id <name>` returns `NotFoundException` |
| KMS key ARN (if encryption at rest with customer CMK) | Custom encryption requires a CMK in the same region | `aws kms describe-key --key-id <cmk-id>` |
| Security group with correct ports inbound from application SG | Network isolation; wrong port = silent connectivity failure | `aws ec2 describe-security-groups --group-ids <sg>` — verify inbound rules |
| LDAP directory details (if ActiveMQ LDAP auth) | LDAP requires a reachable directory endpoint | `aws ds describe-directories` (AWS Managed Microsoft AD / Simple AD) |
| Configuration ID (if custom broker.xml or definitions JSON) | Configuration must be created before broker | `aws mq describe-configuration --configuration-id <id>` |
| Workload description (protocol, connection count, message rate) | Drives engine, deployment mode, instance type decisions | Captured in the prompt or follow-up question |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## 10-step provisioning procedure

### Step 1 — Engine selection (immutable — decide BEFORE create)

The engine decision is the highest-impact Amazon MQ design choice and
is **immutable** without a full migration.

**Decision tree:**

```text
Does the workload need OpenWire, JMS, virtual topics, or ActiveMQ-specific
durable subscriber semantics?
├── YES → ActiveMQ  (the only engine that supports OpenWire / JMS)
│         Note: ActiveMQ also supports STOMP, MQTT, AMQP, WS protocols.
└── NO → Does the workload need RabbitMQ exchanges (direct, fanout, topic,
│        headers), AMQP 0-9-1, or AWS IAM authentication?
    ├── YES → RabbitMQ  (native exchange model, IAM auth, cluster mode)
    └── NO  → ActiveMQ  (broader protocol surface; default for greenfield)
```

**Feature comparison:**

| Feature | ActiveMQ | RabbitMQ |
|---|---|---|
| Protocols | OpenWire, STOMP, MQTT, AMQP 1.0, WS | AMQP 0-9-1, AMQP 1.0, MQTT, STOMP |
| Topology model | Queues, Topics, Virtual Topics, Durable Subscribers | Exchanges (direct, fanout, topic, headers) + Queues + Bindings |
| HA mode | Active/Standby (shared EBS) | Active/Standby OR Cluster (3+ nodes, quorum) |
| Horizontal scaling | NO (single active instance) | YES (cluster mode) |
| Encryption at rest | YES (KMS) | YES (KMS) |
| Encryption in transit (TLS) | YES | YES |
| AWS IAM authentication | NO | YES (creation-time-only) |
| LDAP authentication | YES (JAAS) | YES (via backend) |
| Mutual TLS | YES | YES |
| Audit logging | YES (CloudWatch) | YES (CloudWatch) |
| Automatic minor version upgrades | YES (default on) | YES (default on) |

**Common mistake:** picking RabbitMQ for "IAM auth" then needing JMS or
OpenWire. RabbitMQ does NOT support OpenWire or JMS. Conversely, picking
ActiveMQ for "multi-protocol" then needing RabbitMQ exchanges — ActiveMQ
AMQP support is limited compared to RabbitMQ's native AMQP 0-9-1.

### Step 2 — Deployment mode (immutable for cluster — decide BEFORE create)

The deployment mode determines HA and scaling behavior.

**Decision tree:**

```text
Is the workload production / HA-required?
├── NO → Single instance  (dev/test; no failover; EBS persistence)
└── YES → Which engine?
    ├── ActiveMQ → Active/Standby  (shared EBS; standby in different AZ)
    └── RabbitMQ → Is horizontal scaling needed (high connection count, high throughput)?
        ├── YES → Cluster mode  (3+ nodes; quorum queues; horizontal scale)
        └── NO  → Active/Standby  (2 nodes; standby in different AZ)
```

**ActiveMQ active/standby specifics:**
- 1 active broker + 1 standby in a different AZ.
- Shared EBS storage — the standby does NOT accept connections.
- Failover: 5-15 minutes (EBS volume promotion + restart).
- Clients must use `failover:(ssl://...)` URI for automatic reconnect.

**RabbitMQ cluster mode specifics:**
- 3 nodes minimum (quorum requirement).
- Nodes in different AZs for HA.
- Quorum queues provide automatic leader election (10-30 seconds).
- Horizontal scaling: connections distribute across nodes.
- Going from active/standby to cluster REQUIRES broker deletion +
  recreation. Decide at creation.

**Common mistake:** provisioning an ActiveMQ single-instance broker for
production, then needing HA. Going from single instance to active/standby
triggers a `reboot-broker` with downtime. Default to active/standby for
any production workload.

### Step 3 — Instance type sizing

Amazon MQ offers `mq.t3` and `mq.m5` families. Choose based on
connection count and throughput, not just memory.

**Size by workload:**
- **Dev / test / prototype:** `mq.t3.micro` (1 GiB, ~1,000 connections).
  Free-tier eligible; burst CPU.
- **Small production (< 1,000 connections, < 1,000 msg/s):**
  `mq.m5.large` (8 GiB, ~1,000-2,000 connections).
- **Mid production (2,000-5,000 connections, 1,000-10,000 msg/s):**
  `mq.m5.2xlarge` (32 GiB).
- **Large production (5,000-10,000 connections, 10,000+ msg/s):**
  `mq.m5.4xlarge` (64 GiB).
- **Very large (10,000+ connections):** `mq.m5.8xlarge` or
  `mq.m5.16xlarge`. For RabbitMQ, prefer cluster mode with multiple
  `mq.m5.2xlarge` nodes over a single large node.

**Common mistake:** sizing by memory. Connection-handling overhead and
file-handle limits are the real bottleneck. A 64 GiB broker hitting
5,000 connections will be CPU-bound before memory fills.

### Step 4 — Storage + KMS encryption

Amazon MQ uses EBS-backed storage for message persistence.

**EBS storage:**
- `--storage-type ebs` (default).
- `--ebs-volume-size` (GiB, minimum 10, varies by engine/type).

**Encryption at rest (KMS):**
- Enabled by default with AWS-managed key.
- Customer CMK via `--kms-key-id`.
- Can be added post-creation via modify (requires reboot).
- **Cannot be removed** once enabled.

```bash
aws mq create-broker \
  --broker-name prod-broker \
  --broker-instance-type mq.m5.large \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0" \
  --storage-type ebs \
  --ebs-volume-size 200 \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-mq-kms \
  ...
```

**Common mistake:** not sizing EBS for message backlog. If the broker
buffers messages (consumer lag), EBS fills and the broker stalls. Size
EBS for peak backlog, not average throughput.

### Step 5 — Network + security (VPC, subnet, security group)

Amazon MQ is **VPC-only** for private brokers. There is no public
endpoint by default (publicly accessible flag exists but is off by
default for production).

**Subnet requirements:**
- Active/standby: subnets in at least 2 AZs.
- RabbitMQ cluster: subnets in at least 3 AZs (one per node).

**Security group ports:**

| Protocol | Port | ActiveMQ | RabbitMQ |
|---|---|---|---|
| OpenWire (SSL) | 61617 | YES | NO |
| AMQP (SSL) | 5671 | YES (limited) | YES |
| STOMP (SSL) | 61614 | YES | YES |
| MQTT (SSL) | 8883 | YES | YES |
| WSS (WebSocket) | 61619 | YES | YES |
| ActiveMQ Web Console | 8162 | YES | NO |
| RabbitMQ Management | 15671 | NO | YES |

```bash
# Inbound: allow the application's SG to reach the broker ports
aws ec2 authorize-security-group-ingress \
  --group-id sg-mq123 \
  --protocol tcp \
  --port 61617 \
  --source-security-group-id sg-app456
```

**NEVER** open broker ports to `0.0.0.0/0` — even with TLS and auth,
this exposes the broker to internet scanning.

**Common mistake:** forgetting the Web Console / Management port. The
ActiveMQ Web Console (8162) and RabbitMQ Management UI (15671) need
inbound rules for operator access.

### Step 6 — Authentication (LDAP, IAM, mTLS)

Authentication is engine-specific and, for RabbitMQ IAM, creation-time.

**ActiveMQ authentication options:**
- **Username/password (basic):** `--users` array with ConsoleAccess and
  Groups.
- **LDAP (JAAS):** configure LDAP server in broker.xml. Requires a
  reachable directory service (AWS Managed Microsoft AD, Simple AD, or
  on-prem AD via Direct Connect/VPN).
- **Mutual TLS:** client cert validation at the TLS layer.

**RabbitMQ authentication options:**
- **Username/password (basic):** `--users` array.
- **AWS IAM:** `--authentication-strategy ldap` is NOT used; instead,
  IAM auth is enabled via the broker creation flag. IAM auth allows
  AWS principals (users, roles) to connect using SigV4-signed
  credentials. **Creation-time-only** — cannot add to an existing
  broker without recreation.
- **Mutual TLS:** client cert validation.

```bash
# RabbitMQ with IAM authentication (creation-time-only)
aws mq create-broker \
  --broker-name prod-rabbit \
  --engine-type RABBITMQ \
  --engine-version "3.13" \
  --authentication-strategy ldap \
  ...
```

**Common mistake:** creating a RabbitMQ broker with basic auth, then
needing IAM auth. IAM auth is a creation-time-only setting. The broker
must be deleted and recreated. Decide at creation.

### Step 7 — Configuration (XML for ActiveMQ, definitions JSON for RabbitMQ)

Configuration is engine-specific and must be created BEFORE the broker.

**ActiveMQ configuration (XML):**

```bash
# Create a configuration revision
aws mq create-configuration \
  --configuration-name prod-activemq-config \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0"

# Update the configuration with XML
aws mq update-configuration \
  --configuration-id <config-id> \
  --configuration-data "<base64-encoded-broker.xml>"
```

The broker.xml controls destinations, plugins, slow consumer handling,
and destination policies. Example:

```xml
<broker xmlns="http://activemq.apache.org/schema/core">
  <destinationPolicy>
    <policyMap>
      <policyEntries>
        <policyEntry topic=">" producerFlowControl="true"
                     memoryLimit="1gb">
          <pendingSubscriberPolicy>
            <vmCursor/>
          </pendingSubscriberPolicy>
        </policyEntry>
      </policyEntries>
    </policyMap>
  </destinationPolicy>
</broker>
```

**RabbitMQ configuration (definitions JSON):**

RabbitMQ uses a definitions JSON for exchanges, queues, bindings, and
users. Upload via the RabbitMQ Management UI or embed at creation.

```bash
# RabbitMQ definitions are applied via the management UI or
# a configuration revision (engine-type RABBITMQ)
aws mq create-configuration \
  --configuration-name prod-rabbit-config \
  --engine-type RABBITMQ \
  --engine-version "3.13"

aws mq update-configuration \
  --configuration-id <config-id> \
  --configuration-data "<base64-encoded-definitions.json>"
```

**Common mistake:** creating the broker before the configuration. The
configuration ID must be referenced at `create-broker` via
`--configuration`. A broker created without a configuration uses engine
defaults, which may not match the intended topology.

### Step 8 — Logs (CloudWatch general + audit)

Amazon MQ publishes two log types to CloudWatch:

- **General logs:** broker engine logs (INFO level by default).
- **Audit logs:** administrative and publish/subscribe actions
  (ActiveMQ) or connection / channel events (RabbitMQ).

**Enable at creation:**

```bash
aws mq create-broker \
  --broker-name prod-broker \
  --logs General=true \
  --logs Audit=true \
  ...
```

**Audit logging is critical for compliance:**
- PCI-DSS, HIPAA, FedRAMP require an audit trail of all broker access.
- Audit logs capture user logins, destination creation, message
  publishes, and administrative actions.
- Enable at creation to avoid an unaudited gap.

**Common mistake:** enabling only general logs. General logs capture
engine errors, NOT user actions. Audit logs are required for compliance.

### Step 9 — Automatic minor version upgrades + maintenance

Amazon MQ applies minor version upgrades automatically during a
maintenance window.

**Defaults:**
- `--auto-minor-version-upgrade true` (default on).
- Maintenance window: Amazon MQ selects a random window if not
  specified.

**Override the maintenance window:**

```bash
aws mq create-broker \
  --broker-name prod-broker \
  --maintenance-window-start-time \
    DayOfWeek=SUNDAY,TimeOfDay=03:00,TimeZone=UTC \
  ...
```

**Common mistake:** disabling automatic upgrades for "stability." This
leaves the broker unpatched against security vulnerabilities. Keep
upgrades enabled and set an explicit maintenance window.

### Step 10 — Transit gateway / protocol surface (latest features)

**RabbitMQ transit gateway (2024-2026):**
- Cross-account / cross-VPC broker access via AWS Transit Gateway.
- Configure the TGW attachment, route tables, and security group rules.
- Use RAM (Resource Access Manager) to share the TGW across accounts.

```bash
# Share the transit gateway with the consuming account
aws ram create-resource-share \
  --name mq-tgw-share \
  --resource-arns arn:aws:ec2:us-east-1:123456789012:transit-gateway/tgw-0abc \
  --principals 123456789012
```

**ActiveMQ protocol surface (STOMP, MQTT, AMQP, WS):**
- ActiveMQ supports OpenWire (61617), AMQP (5671), STOMP (61614),
  MQTT (8883), and WSS (61619) simultaneously.
- Enable the protocols in broker.xml.
- Each protocol needs a security group inbound rule.

```xml
<!-- broker.xml: enable all protocols -->
<transportConnectors>
  <transportConnector name="openwire" uri="ssl://0.0.0.0:61617"/>
  <transportConnector name="amqp" uri="amqp+ssl://0.0.0.0:5671"/>
  <transportConnector name="stomp" uri="stomp+ssl://0.0.0.0:61614"/>
  <transportConnector name="mqtt" uri="ssl+mqtt://0.0.0.0:8883"/>
  <transportConnector name="ws" uri="wss://0.0.0.0:61619"/>
</transportConnectors>
```

**Common mistake:** provisioning a RabbitMQ broker expecting ActiveMQ
protocols (OpenWire, WS console). RabbitMQ does NOT support OpenWire.
Verify the protocol surface matches the engine choice.

## NEVER do these things (top 5)

1. **NEVER pick RabbitMQ for a workload that needs OpenWire, JMS, or
   ActiveMQ virtual topics.** RabbitMQ does NOT support these. Migration
   is a full application rewrite. Pick ActiveMQ for JMS / OpenWire
   workloads.

2. **NEVER create a RabbitMQ broker with basic auth then need IAM auth.**
   IAM authentication is a creation-time-only setting. Converting
   requires deleting and recreating the broker. Decide at creation.

3. **NEVER provision a single-AZ subnet for active/standby.** HA
   requires the standby in a different AZ. Verify
   `aws ec2 describe-subnets` shows >=2 distinct AZs before
   `create-broker`.

4. **NEVER open broker ports to `0.0.0.0/0`.** Even with TLS and auth,
   internet exposure invites scanning and brute-force attacks. Always
   scope inbound to the application's SG.

5. **NEVER disable automatic minor version upgrades on a production
   broker.** This leaves the broker unpatched against security
   vulnerabilities. Keep upgrades enabled with an explicit maintenance
   window.

**Additional critical mistakes:** never enable only general logs for
compliance brokers (audit logs required for PCI-DSS/HIPAA); never
create a 2-node RabbitMQ cluster (quorum requires 3); never attempt
active/standby → cluster conversion by modify (requires broker
deletion + recreation); never size by memory alone (connection count is
the real limit); never create the broker before the configuration
(reference at `create-broker` via `--configuration`); never forget the
Web Console (8162) / Management (15671) ports; never assume single
instance has failover; never use plain TCP for ActiveMQ failover
(clients need `failover:(ssl://...)` URI).

## Output format

```text
BROKER: <broker-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Engine: ActiveMQ | RabbitMQ
  [✓|✗] Deployment mode: Single instance | Active/Standby | Cluster (<N> nodes)
  [✓|✗] Instance type: mq.<family>.<size> (<memory> GiB; <max-connections> connections)
  [✓|✗] EBS storage: <size> GiB (encrypted with <KMS-key-arn | AWS-managed>)
  [✓|✗] Subnet: <name> (spans <N> AZs)
  [✓|✗] Security group: <sg-id> (inbound ports: <port-list> from <app-sg>)
  [✓|✗] Encryption at rest: Enabled (customer CMK <key-arn>) | AWS-managed
  [✓|✗] Encryption in transit (TLS): Enabled | Disabled
  [✓|✗] Authentication: <LDAP | IAM (RabbitMQ) | Username/password | mTLS>
  [✓|✗] Configuration: <config-id> revision <N> (XML / definitions JSON)
  [✓|✗] General logs: Enabled (CloudWatch log group: <name>)
  [✓|✗] Audit logs: Enabled (CloudWatch log group: <name>)
  [✓|✗] Automatic minor version upgrades: Enabled (window: <UTC-range>)
  [✓|✗] Transit gateway: <tgw-id> (cross-account) | N/A
VERIFICATION_COMMANDS:
  aws mq describe-broker --broker-id <name>
  aws mq describe-configuration --configuration-id <config-id>
  aws ec2 describe-security-groups --group-ids <sg-id>
  aws kms describe-key --key-id <cmk-id>
```

### Worked example — production ActiveMQ active/standby

```text
BROKER: prod-mq
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: ActiveMQ
  [✓] Deployment mode: Active/Standby (standby in us-east-1b)
  [✓] Instance type: mq.m5.large (8 GiB; ~1,000 connections)
  [✓] EBS storage: 200 GiB (encrypted with customer CMK alias/prod-mq-kms)
  [✓] Subnet: prod-mq-subnet (2 AZs: us-east-1a, us-east-1b)
  [✓] Security group: sg-mq123 (inbound 61617, 8162 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-mq-kms)
  [✓] Encryption in transit (TLS): Enabled
  [✓] Authentication: LDAP (AWS Managed Microsoft AD d-1234567890)
  [✓] Configuration: c-abc123 revision 1 (XML: OpenWire + STOMP + MQTT)
  [✓] General logs: Enabled (CloudWatch: /aws/amazonmq/broker/prod-mq/general)
  [✓] Audit logs: Enabled (CloudWatch: /aws/amazonmq/broker/prod-mq/audit)
  [✓] Automatic minor version upgrades: Enabled (window: SUN 03:00 UTC)
  [✓] Transit gateway: N/A
VERIFICATION_COMMANDS:
  aws mq describe-broker --broker-id prod-mq
  aws mq describe-configuration --configuration-id c-abc123
  aws ec2 describe-security-groups --group-ids sg-mq123
  aws kms describe-key --key-id alias/prod-mq-kms
```

## Error handling

| Error | Cause | Fix |
|---|---|---|
| `BrokerAlreadyExists` | Broker name in use | `describe-broker` — if config matches, emit READY_TO_DEPLOY; if differs, modify (mutable: instance type, SG, logs) or create NEW broker |
| `Subnet does not span multiple AZs` | All subnets in one AZ | Add subnets in different AZs; verify with `describe-subnets` |
| `IAM authentication requires RabbitMQ engine` | IAM auth on ActiveMQ | Use LDAP/basic for ActiveMQ; IAM is RabbitMQ-only and creation-time |
| `Configuration revision not compatible` | Engine-type/version mismatch | Create new configuration with correct engine-type + version |
| Broker stuck in `REBOOT_IN_PROGRESS` | Modify triggered reboot | Wait for `RUNNING` via `describe-broker --query 'BrokerState'` |

## Recent AWS features (2024-2026)

- **Amazon MQ for RabbitMQ with transit gateway (2024-2025):**
  Cross-account and cross-VPC broker access via AWS Transit Gateway.
  Configure TGW attachments, route tables, and RAM principal
  associations for sharing.
- **Amazon MQ for ActiveMQ multi-protocol (STOMP, MQTT, AMQP, WS):**
  Full protocol surface enabled in broker.xml. OpenWire, AMQP, STOMP,
  MQTT, and WebSocket simultaneously. Each protocol needs a security
  group inbound rule.
- **RabbitMQ IAM authentication (2023-2024):** AWS principals (users,
  roles) connect using SigV4-signed credentials. Creation-time-only
  setting. Eliminates password management for AWS-native workloads.
- **Automatic minor version upgrades (2023-2024):** Amazon MQ applies
  minor version upgrades automatically during a maintenance window.
  Override the window with `--maintenance-window-start-time`.
- **Amazon MQ audit logging (2023-2024):** CloudWatch audit logs capture
  every administrative and publish/subscribe action. Enable at creation
  for compliance-regulated workloads.
- **RabbitMQ 3.13 / 3.12 support (2024):** Quorum queues, classic
  mirrored queues, stream queues. Provisioning tip: use quorum queues
  for HA (3-node cluster minimum).
- **ActiveMQ 5.18 support (2024):** Updated STOMP, MQTT, and AMQP
  protocol adapters. Java 11 runtime.

## Domain

AWS CloudOps / Amazon MQ Broker Provisioning & Messaging Topology Design.

## AWS documentation

- **Amazon MQ Developer Guide** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/welcome.html
- **ActiveMQ broker configuration** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/activemq-configuration-settings.html
- **RabbitMQ broker configuration** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/rabbitmq-configuration-settings.html
- **Amazon MQ authentication** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-authentication.html
- **Amazon MQ logging** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-logging-and-monitoring.html
- **Amazon MQ best practices** — https://docs.aws.amazon.com/amazon-mq/latest/developer-guide/amazon-mq-best-practices.html
