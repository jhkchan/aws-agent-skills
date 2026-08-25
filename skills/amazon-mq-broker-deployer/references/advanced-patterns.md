# Advanced Patterns — Amazon MQ Broker Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset misconceptions

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
