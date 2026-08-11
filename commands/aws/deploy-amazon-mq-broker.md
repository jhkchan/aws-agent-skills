---
description: Provision an Amazon MQ broker (ActiveMQ or RabbitMQ) with production-grade defaults (engine selection, deployment mode, instance type, EBS+KMS encryption, VPC networking, LDAP/IAM/mTLS auth, configuration, audit logging). Emits a READY_TO_DEPLOY checklist with verification commands.
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
  - "mq.m5.16xl"
  - "amazon mq ldap"
  - "rabbitmq iam auth"
  - "amazon mq mutual tls"
  - "amazon mq encryption"
  - "amazon mq kms"
  - "amazon mq audit logging"
  - "amazon mq transit gateway"
  - "activemq stomp mqtt amqp"
  - "activemq openwire"
  - "rabbitmq definitions json"
  - "activemq broker.xml"
  - "amazon mq automatic minor version upgrade"
  - "amazon mq configuration"
routes_to: amazon-mq-broker-deployer
---

# /aws:deploy-amazon-mq-broker

Activate the `amazon-mq-broker-deployer` skill and provision an
Amazon MQ broker (ActiveMQ or RabbitMQ) with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Engine selection (ActiveMQ vs RabbitMQ — immutable)
2. Deployment mode (single instance vs active/standby vs cluster)
3. Instance type sizing (mq.t3.micro to mq.m5.16xl)
4. Storage + KMS encryption (EBS, encrypted at rest)
5. Network + security (VPC, subnet, security group, ports)
6. Authentication (LDAP, AWS IAM for RabbitMQ, mTLS)
7. Configuration (XML for ActiveMQ, definitions JSON for RabbitMQ)
8. Logs (CloudWatch general + audit logs)
9. Upgrades + maintenance (automatic minor version upgrades)
10. Transit gateway / protocol surface (latest features)

## When to use

- You need to create a new Amazon MQ broker with production defaults.
- You are choosing between ActiveMQ and RabbitMQ for a workload.
- You need to design an active/standby HA topology.
- You need to wire RabbitMQ with AWS IAM authentication.
- You need ActiveMQ with LDAP or the full multi-protocol surface
  (OpenWire, STOMP, MQTT, AMQP, WS).
- You want to validate that a broker design meets production baseline.
- You need copy-pasteable provisioning commands or IaC templates.

## How to invoke

### Slash command

```
/aws:deploy-amazon-mq-broker
```

Then provide: broker name, region, engine choice (ActiveMQ or
RabbitMQ), deployment mode (single instance, active/standby, cluster),
instance type, workload description (protocol, connection count,
message rate), authentication preference (LDAP, IAM, mTLS, basic),
encryption preference, and any optional features (audit logs, transit
gateway).

### Natural language

Any of these routes to the same skill:

- "create a production Amazon MQ ActiveMQ broker"
- "provision a RabbitMQ cluster with IAM auth"
- "deploy an ActiveMQ broker with LDAP authentication"
- "set up an Amazon MQ broker with audit logging"
- "provision a RabbitMQ broker with transit gateway cross-account access"

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
You: /aws:deploy-amazon-mq-broker

     Provision a production Amazon MQ ActiveMQ broker "prod-mq" in
     us-east-1. Active/standby HA. mq.m5.large. LDAP auth against
     Managed AD d-1234567890. CMK alias/prod-mq-kms. TLS. OpenWire +
     STOMP + MQTT protocols. CloudWatch general + audit logs. Subnet
     prod-mq-subnet spans 2 AZs. Security group sg-mq123 inbound 61617,
     61614, 8883, 8162 from sg-app456. Account: 123456789012.

Skill:
  BROKER: prod-mq
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Engine: ActiveMQ
    [✓] Deployment mode: Active/Standby (standby in us-east-1b)
    [✓] Instance type: mq.m5.large (8 GiB; ~1,000 connections)
    [✓] EBS storage: 200 GiB (encrypted with CMK alias/prod-mq-kms)
    [✓] Subnet: prod-mq-subnet (2 AZs)
    [✓] Security group: sg-mq123 (inbound 61617, 61614, 8883, 8162)
    [✓] Encryption at rest: Enabled (customer CMK alias/prod-mq-kms)
    [✓] Encryption in transit (TLS): Enabled
    [✓] Authentication: LDAP (Managed AD d-1234567890)
    [✓] General logs: Enabled (CloudWatch)
    [✓] Audit logs: Enabled (CloudWatch)
    [✓] Automatic minor version upgrades: Enabled (SUN 03:00 UTC)
  VERIFICATION_COMMANDS:
    aws mq describe-broker --broker-id prod-mq
    aws mq describe-configuration --configuration-id <config-id>
    aws kms describe-key --key-id alias/prod-mq-kms
```

## References

- Skill definition: `skills/amazon-mq-broker-deployer/SKILL.md`
- Engine and topology guide: `skills/amazon-mq-broker-deployer/references/engine-and-topology.md`
- Provisioning CLI commands: `skills/amazon-mq-broker-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/amazon-mq-broker-deployer/evals/evals.json`
