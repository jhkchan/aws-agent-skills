# End-to-End Example: Amazon MQ Broker Deployment

A walkthrough showing how to use the `mq-broker-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a production ActiveMQ broker in active/standby
mode with LDAP authentication, KMS encryption, and CloudWatch alarms.
The broker needs:

- Broker name: prod-mq
- Engine: ActiveMQ
- Deployment mode: Active/Standby (2 AZs)
- Instance type: mq.m5.large
- Authentication: LDAP (Managed AD d-1234567890)
- Encryption: CMK alias/prod-mq-kms
- Protocols: OpenWire (61617), AMQP (5671), Web Console (8162)
- Subnets: subnet-aaa (us-east-1a), subnet-bbb (us-east-1b)
- Security group: sg-mq123 (inbound from sg-app456)
- CloudWatch alarms: CpuUtilization >80%, MemoryUtilization >80%, EnqueueCount anomaly
- Maintenance window: SUN 03:00 UTC

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-mq-broker
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a production Amazon MQ ActiveMQ broker prod-mq in
      us-east-1. Active/standby HA. mq.m5.large. LDAP auth
      against Managed AD d-1234567890. CMK alias/prod-mq-kms.
      OpenWire + AMQP protocols. CloudWatch alarms for CPU and
      memory. Subnets subnet-aaa, subnet-bbb."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an amazon mq broker"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

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

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the KMS key (if not existing)
aws kms create-key --description "prod-mq broker encryption key"
aws kms create-alias --alias-name alias/prod-mq-kms --target-key-id <key-id>

# Step 2: Create the ActiveMQ configuration with LDAP
CONFIG_ID=$(aws mq create-configuration \
  --name prod-mq-ldap-config \
  --engine-type ActiveMQ \
  --engine-version 5.18.0 \
  --query 'Id' --output text)

# Step 3: Create the broker
BROKER_ID=$(aws mq create-broker \
  --broker-name prod-mq \
  --engine-type ActiveMQ \
  --engine-version 5.18.0 \
  --host-instance-type mq.m5.large \
  --deployment-mode ACTIVE_STANDBY \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-groups sg-mq123 \
  --storage-type ebs \
  --encryption-options '{"UseAwsOwnedKey": false, "KmsKeyId": "alias/prod-mq-kms"}' \
  --auto-minor-version-upgrade \
  --maintenance-window-start-time \
    '{"DayOfWeek": "SUNDAY", "TimeOfDay": "03:00", "TimeZone": "UTC"}' \
  --users '[{"Username": "admin", "Password": "<password>", "ConsoleAccess": true}]' \
  --configuration '{"Id": "'"$CONFIG_ID"'", "Revision": 1}' \
  --query 'BrokerId' --output text)

echo "Broker ID: $BROKER_ID"

# Step 4: Create CloudWatch alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-high-cpu" \
  --metric-name CpuUtilization \
  --namespace AWS/AmazonMQ \
  --statistic Average --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 1 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"

aws cloudwatch put-metric-alarm \
  --alarm-name "prod-mq-high-memory" \
  --metric-name MemoryUtilization \
  --namespace AWS/AmazonMQ \
  --statistic Average --period 300 --threshold 80 \
  --comparison-operator GreaterThanThreshold --evaluation-periods 1 \
  --dimensions Name=Broker,Value=prod-mq \
  --alarm-actions "arn:aws:sns:us-east-1:123456789012:mq-alerts"
```

---

## Step 4 — Post-deployment verification

```bash
# Broker status — should be RUNNING
aws mq describe-broker --broker-id prod-mq \
  --query 'BrokerState'

# Broker instances and endpoints
aws mq describe-broker --broker-id prod-mq \
  --query 'BrokerInstances[*].{ConsoleURL:ConsoleURL,Endpoints:Endpoints}'

# Verify CloudWatch alarms exist
aws cloudwatch describe-alarms \
  --alarm-names prod-mq-high-cpu prod-mq-high-memory prod-mq-no-enqueues \
  --query 'MetricAlarms[*].{Name:AlarmName,State:StateValue}'

# Verify KMS key
aws kms describe-key --key-id alias/prod-mq-kms \
  --query 'KeyMetadata.{Enabled:Enabled,Rotation:KeyRotationEnabled}'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Subnet count | Single subnet for active/standby | 2 subnets in 2 AZs | Active/standby requires exactly 2 AZs; wrong count = creation failure |
| LDAP connectivity | Not verified | LDAP server reachability check | Broker must reach LDAP on 389/636 |
| CloudWatch alarms | Not configured | Alarms for CPU, memory, enqueue count | Alarms are a separate CloudWatch API call, not MQ |
| KMS key policy | Uses AWS-owned key | Customer CMK with service principal policy | AWS-owned key has no audit or rotation control |
| IAM auth naming | Tries `authenticationStrategy=IAM` | `authenticationStrategy=LDAP` | Counterintuitive: "LDAP" enables IAM for RabbitMQ |
| Engine immutability | Not flagged | Explicit engine choice confirmation | ActiveMQ cannot convert to RabbitMQ later |

---

## Related artifacts

- **Skill definition:** `skills/mq-broker-deployer/SKILL.md`
- **Engine and topology guide:** `skills/mq-broker-deployer/references/engine-and-topology.md`
- **Security and monitoring guide:** `skills/mq-broker-deployer/references/security-and-monitoring.md`
- **Slash command:** `commands/aws/deploy-mq-broker.md`
- **Eval suite:** `skills/mq-broker-deployer/evals/evals.json`
- **Legacy test cases:** `skills/mq-broker-deployer/eval/test-cases.yaml`
