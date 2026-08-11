---
description: Provision an Amazon MQ broker (ActiveMQ or RabbitMQ) with production-grade defaults (engine selection, deployment mode, instance type, EBS+KMS encryption, VPC networking, LDAP/IAM auth, CloudWatch alarms, maintenance window). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create amazon mq broker"
  - "provision activemq broker"
  - "provision rabbitmq broker"
  - "deploy amazon mq"
  - "amazon mq activemq"
  - "amazon mq rabbitmq"
  - "amazon mq active/standby"
  - "amazon mq cluster mode"
  - "amazon mq single instance"
  - "amazon mq broker type"
  - "mq.t3.micro"
  - "mq.m5.large"
  - "amazon mq ldap"
  - "rabbitmq iam auth"
  - "amazon mq cloudwatch alarms"
  - "amazon mq kms encryption"
  - "amazon mq maintenance window"
  - "amazon mq message persistence"
  - "broker cpuutilization alarm"
  - "broker memoryutilization alarm"
  - "broker enqueue count alarm"
routes_to: mq-broker-deployer
---

# /aws:deploy-mq-broker

Activate the `mq-broker-deployer` skill and provision an Amazon MQ
broker (ActiveMQ or RabbitMQ) with production-grade defaults.

## What it does

The skill walks an 11-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Engine selection (ActiveMQ vs RabbitMQ — immutable)
2. Deployment mode (single-instance vs active/standby vs cluster)
3. Instance type sizing (mq.t3.micro to mq.m5.16xl)
4. Storage + KMS encryption (EBS, encrypted at rest)
5. Authentication (LDAP, IAM for RabbitMQ, mTLS, basic)
6. Network + security groups (VPC, subnet, SG, ports)
7. Public access vs private broker
8. CloudWatch alarms (CpuUtilization, MemoryUtilization, EnqueueCount)
9. Maintenance window + auto minor version upgrade
10. Message persistence + queues/topics
11. Recent features (quorum queues, RabbitMQ streams)

## When to use

- You need to create a new Amazon MQ broker with production defaults.
- You are choosing between ActiveMQ and RabbitMQ for a workload.
- You need to design an active/standby HA topology.
- You need to wire RabbitMQ with AWS IAM authentication.
- You need ActiveMQ with LDAP authentication.
- You need CloudWatch alarms for broker metrics.
- You want to validate that a broker design meets production baseline.

## When NOT to use

- **Amazon MSK (Managed Streaming for Kafka)** — different service.
- **Amazon Kinesis** — streaming, not message broker.
- **Amazon SQS / SNS** — serverless messaging, no broker management.
- **Self-managed Kafka/RabbitMQ on EC2** — not Amazon MQ.

## How to invoke

### Slash command

```
/aws:deploy-mq-broker
```

Then provide: broker name, region, engine choice (ActiveMQ or
RabbitMQ), deployment mode (single, active/standby, cluster),
instance type, authentication preference (LDAP, IAM, mTLS, basic),
encryption preference (CMK), CloudWatch alarm requirements,
maintenance window, and tags.

### Natural language

Any of these routes to the same skill:

- "create a production Amazon MQ ActiveMQ broker"
- "provision a RabbitMQ cluster with IAM auth"
- "deploy an ActiveMQ broker with LDAP authentication"
- "set up Amazon MQ with CloudWatch alarms for broker metrics"
- "provision a single-instance ActiveMQ broker for development"

### CLI routing

```bash
node cli/bin/cli.js route "create an amazon mq broker"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or harden
Amazon MQ brokers. The output checklist feeds into verification
pipelines and audit skills.

## Example

```
You: /aws:deploy-mq-broker

     Provision a production Amazon MQ ActiveMQ broker "prod-mq" in
     us-east-1. Active/standby HA. mq.m5.large. LDAP auth against
     Managed AD d-1234567890. CMK alias/prod-mq-kms. TLS. OpenWire +
     AMQP protocols. CloudWatch alarms for CpuUtilization >80%,
     MemoryUtilization >80%, EnqueueCount anomaly. Subnet prod-mq-subnet
     spans 2 AZs. Security group sg-mq123 inbound 61617, 5671, 8162
     from sg-app456. Account: 123456789012.

Skill:
  MQ_BROKER: prod-mq (ActiveMQ, Active/Standby)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Engine: ActiveMQ
    [✓] Deployment mode: Active/Standby (standby in us-east-1b)
    [✓] Instance type: mq.m5.large (2 vCPU, 8 GiB; ~1,000 connections)
    [✓] Storage: 200 GiB EBS (encrypted with CMK alias/prod-mq-kms)
    [✓] Authentication: LDAP (Managed AD d-1234567890)
    [✓] CloudWatch alarms: CpuUtilization >80%, MemoryUtilization >80%
    [✓] Maintenance window: SUN 03:00 UTC
  VERIFICATION_COMMANDS:
    aws mq describe-broker --broker-id prod-mq
    aws cloudwatch describe-alarms --alarm-names prod-mq-high-cpu prod-mq-high-memory
```

## References

- Skill definition: `skills/mq-broker-deployer/SKILL.md`
- Engine and topology guide: `skills/mq-broker-deployer/references/engine-and-topology.md`
- Security and monitoring guide: `skills/mq-broker-deployer/references/security-and-monitoring.md`
- Eval suite: `skills/mq-broker-deployer/evals/evals.json`
