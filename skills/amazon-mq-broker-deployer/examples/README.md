# End-to-End Example: Amazon MQ Broker Deployment

A walkthrough showing how to use the `amazon-mq-broker-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production ActiveMQ broker with active/standby
HA. The broker needs:

- Engine: ActiveMQ (JMS-style messaging, OpenWire clients)
- Deployment mode: Active/Standby (standby in us-east-1b)
- Instance type: mq.m5.large (8 GiB; ~1,000 connections)
- LDAP authentication (AWS Managed Microsoft AD d-1234567890)
- Customer-managed CMK for encryption at rest (alias/prod-mq-kms)
- TLS enabled
- Protocols: OpenWire (61617), STOMP (61614), MQTT (8883), Web Console (8162)
- CloudWatch general + audit logs
- Automatic minor version upgrades, window SUN 03:00 UTC

Broker name: `prod-mq`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-amazon-mq-broker
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production Amazon MQ ActiveMQ broker named prod-mq in
      us-east-1. Active/standby HA. mq.m5.large. LDAP auth against
      Managed AD d-1234567890. CMK alias/prod-mq-kms. TLS. OpenWire +
      STOMP + MQTT protocols. CloudWatch general + audit logs. Subnet
      prod-mq-subnet spans 2 AZs. Security group sg-mq123 inbound 61617,
      61614, 8883, 8162 from sg-app456. Account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an amazon mq activemq broker"
```

Output:

```
[Phase: Deploy | Skills routed: amazon-mq-broker-deployer]

Primary route: amazon-mq-broker-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
BROKER: prod-mq
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Engine: ActiveMQ
  [✓] Deployment mode: Active/Standby (standby in us-east-1b)
  [✓] Instance type: mq.m5.large (8 GiB; ~1,000 connections)
  [✓] EBS storage: 200 GiB (encrypted with customer CMK alias/prod-mq-kms)
  [✓] Subnet: prod-mq-subnet (2 AZs: us-east-1a, us-east-1b)
  [✓] Security group: sg-mq123 (inbound 61617, 61614, 8883, 8162 from sg-app456)
  [✓] Encryption at rest: Enabled (customer CMK alias/prod-mq-kms)
  [✓] Encryption in transit (TLS): Enabled
  [✓] Authentication: LDAP (AWS Managed Microsoft AD d-1234567890)
  [✓] Configuration: XML (OpenWire + STOMP + MQTT protocols enabled)
  [✓] General logs: Enabled (CloudWatch: /aws/amazonmq/broker/prod-mq/general)
  [✓] Audit logs: Enabled (CloudWatch: /aws/amazonmq/broker/prod-mq/audit)
  [✓] Automatic minor version upgrades: Enabled (window: SUN 03:00 UTC)
  [✓] Transit gateway: N/A
VERIFICATION_COMMANDS:
  aws mq describe-broker --broker-id prod-mq
  aws mq describe-configuration --configuration-id <config-id>
  aws ec2 describe-security-groups --group-ids sg-mq123
  aws kms describe-key --key-id alias/prod-mq-kms
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create the ActiveMQ configuration (BEFORE the broker)
aws mq create-configuration \
  --configuration-name prod-activemq-config \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0"

# Update with XML (base64-encoded broker.xml)
BROKER_XML=$(cat broker.xml | base64)
aws mq update-configuration \
  --configuration-id <config-id> \
  --configuration-data "$BROKER_XML"

# Step 2: Create the broker
aws mq create-broker \
  --broker-name prod-mq \
  --broker-instance-type mq.m5.large \
  --engine-type ACTIVEMQ \
  --engine-version "5.18.0" \
  --deployment-mode ACTIVE_STANDBY_MULTI_AZ \
  --subnet-ids subnet-0aaa subnet-0bbb \
  --security-groups sg-mq123 \
  --storage-type ebs \
  --ebs-volume-size 200 \
  --kms-key-id arn:aws:kms:us-east-1:123456789012:alias/prod-mq-kms \
  --configuration-id <config-id> \
  --configuration-revision 1 \
  --users Username=admin,Password=SecurePass123,ConsoleAccess=true,Groups=admin \
  --logs General=true,Audit=true \
  --auto-minor-version-upgrade true \
  --maintenance-window-start-time \
    DayOfWeek=SUNDAY,TimeOfDay=03:00,TimeZone=UTC \
  --tags Environment=production,Workload=messaging

# Step 3: Wait for RUNNING state
aws mq describe-broker --broker-id prod-mq --query 'BrokerState'
```

---

## Step 4 — Post-deployment verification

```bash
# Broker state, endpoints, encryption, logs, configuration
aws mq describe-broker --broker-id prod-mq

# Configuration details (revision, data)
aws mq describe-configuration --configuration-id <config-id>

# Security group rules
aws ec2 describe-security-groups --group-ids sg-mq123

# KMS key state
aws kms describe-key --key-id alias/prod-mq-kms

# CloudWatch log groups
aws logs describe-log-groups \
  --log-group-name-prefix /aws/amazonmq/broker/prod-mq
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Engine choice | Defaults to RabbitMQ for "simplicity" | ActiveMQ (JMS/OpenWire needed) | RabbitMQ does NOT support OpenWire or JMS. Migration is a full client rewrite. |
| Deployment mode | Picks single instance (simpler) | Active/Standby | Single instance has NO failover. Going single → active/standby triggers a reboot with downtime. Default to HA for production. |
| IAM auth timing | "Add IAM auth later" | IAM auth is creation-time-only | A RabbitMQ broker created with basic auth CANNOT be converted to IAM auth without deletion + recreation. |
| Audit logs | Enables only general logs | General + audit logs | General logs capture engine errors, NOT user actions. Audit logs required for compliance. |
| Subnet AZs | Forgets to verify | Confirms subnet spans >=2 AZs | Active/standby requires the standby in a different AZ. Single-AZ silently blocks HA. |
| Configuration order | Creates broker first | Creates config first, references at broker creation | A broker without a configuration uses engine defaults. Config must precede broker. |
| Security group ports | Forgets protocol-specific ports | Lists OpenWire (61617), STOMP (61614), MQTT (8883), WS (61619) | Each protocol needs a separate inbound rule. Missing rules = silent connectivity failure. |
| RabbitMQ cluster size | Creates 2-node cluster | 3 nodes minimum (quorum) | A 2-node RabbitMQ cluster loses quorum on any single node failure. |

---

## Related artifacts

- **Skill definition:** `skills/amazon-mq-broker-deployer/SKILL.md`
- **Engine and topology guide:** `skills/amazon-mq-broker-deployer/references/engine-and-topology.md`
- **Provisioning CLI commands:** `skills/amazon-mq-broker-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-amazon-mq-broker.md`
- **Eval suite:** `skills/amazon-mq-broker-deployer/evals/evals.json`
- **Legacy test cases:** `skills/amazon-mq-broker-deployer/eval/test-cases.yaml`
