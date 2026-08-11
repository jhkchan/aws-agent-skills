# End-to-End Example: IoT Core Thing Deployment

A walkthrough showing how to use the `iot-core-thing-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an IoT Core thing for a factory floor temperature
sensor with X.509 certificate, IoT policy for MQTT pub/sub, topic rule
for telemetry processing, and device shadow for configuration sync.
The deployment needs:

- Thing: sensor-001 (type: temperature-sensor)
- Certificate: X.509 with AWS-generated key pair
- Policy: connect (client ID sensor-*), publish (device/+/telemetry),
  subscribe (device/+/commands)
- Topic rule: telemetry-to-timestream (SQL SELECT + Timestream + republish)
- Device shadow: classic (config sync)
- Thing group: factory-floor-sensors
- Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-iot-core-thing
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an IoT thing sensor-001 in us-east-1 with X.509
      certificate. Policy for connect, publish to telemetry,
      subscribe to commands. Attach cert to thing and policy
      to cert. Create a topic rule to Timestream. Set up
      classic device shadow."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an iot thing"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
IOT_THING: sensor-001 (arn:aws:iot:us-east-1:123456789012:thing/sensor-001)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Thing: sensor-001 — created
  [✓] Thing type: temperature-sensor
  [✓] Thing group: factory-floor-sensors
  [✓] Certificate (X.509): a1b2c3d4e5 — ACTIVE
  [✓] Certificate attached to thing: YES
  [✓] IoT policy: sensor-publish-policy — created
  [✓] Policy attached to certificate: YES
  [✓] Topic rule: telemetry-to-timestream — SQL: SELECT temperature FROM 'device/+/telemetry'
  [✓] Topic rule IAM role: arn:aws:iam::123456789012:role/IoTTopicRuleRole
  [✓] Topic rule actions: Timestream, Republish
  [✓] Device shadow: classic
  [✓] Fleet indexing: REGISTRY_AND_SHADOW
  [✓] Protocol: MQTT (port 8883)
  [✓] Tags: Environment=production, DeviceType=sensor
VERIFICATION_COMMANDS:
  aws iot describe-thing --thing-name sensor-001 --region us-east-1
  aws iot list-thing-principals --thing-name sensor-001 --region us-east-1
  aws iot describe-certificate --certificate-id a1b2c3d4e5 --region us-east-1
  aws iot get-topic-rule --rule-name telemetry-to-timestream --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the thing
aws iot create-thing \
  --thing-name "sensor-001" \
  --thing-type-name "temperature-sensor" \
  --region us-east-1

# Step 2: Create the thing group and add thing
aws iot create-thing-group --thing-group-name "factory-floor-sensors" --region us-east-1
aws iot add-thing-to-thing-group \
  --thing-name "sensor-001" \
  --thing-group-name "factory-floor-sensors" --region us-east-1

# Step 3: Create the X.509 certificate
CERT_ARN=$(aws iot create-keys-and-certificate \
  --set-as-active \
  --public-key-outfile public.key \
  --private-key-outfile private.key \
  --certificate-pem-outfile certificate.pem \
  --query 'certificateArn' --output text \
  --region us-east-1)

# Step 4: Create the IoT policy
aws iot create-policy \
  --policy-name "sensor-publish-policy" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect":"Allow","Action":["iot:Connect"],"Resource":"arn:aws:iot:us-east-1:123456789012:client/sensor-*"},
      {"Effect":"Allow","Action":["iot:Publish"],"Resource":"arn:aws:iot:us-east-1:123456789012:topic/device/+/telemetry"},
      {"Effect":"Allow","Action":["iot:Subscribe"],"Resource":"arn:aws:iot:us-east-1:123456789012:topicfilter/device/+/commands"},
      {"Effect":"Allow","Action":["iot:Receive"],"Resource":"arn:aws:iot:us-east-1:123456789012:topic/device/+/commands"}
    ]
  }' --region us-east-1

# Step 5: CRITICAL — Bind cert to thing
aws iot attach-thing-principal \
  --thing-name "sensor-001" \
  --principal "$CERT_ARN" --region us-east-1

# Step 6: CRITICAL — Bind policy to cert
aws iot attach-policy \
  --policy-name "sensor-publish-policy" \
  --target "$CERT_ARN" --region us-east-1

# Step 7: Create the topic rule
aws iot create-topic-rule \
  --rule-name "telemetry-to-timestream" \
  --topic-rule-payload '{
    "sql": "SELECT temperature, humidity, device_id FROM '\''device/+/telemetry'\'' WHERE temperature > 30",
    "ruleDisabled": false,
    "actions": [
      {"timestream":{"roleArn":"arn:aws:iam::123456789012:role/IoTTopicRuleRole","databaseName":"sensors","tableName":"telemetry","dimensions":[{"name":"device_id","value":"${device_id}"}]}}
    ]
  }' --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Thing exists
aws iot describe-thing --thing-name sensor-001 --region us-east-1

# Cert is attached to thing
aws iot list-thing-principals --thing-name sensor-001 --region us-east-1

# Policy is attached to cert
aws iot list-principal-policies --principal "$CERT_ARN" --region us-east-1

# Topic rule is active
aws iot get-topic-rule --rule-name telemetry-to-timestream --region us-east-1

# Shadow is accessible
aws iot-data get-thing-shadow --thing-name sensor-001 --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Cert-to-thing binding | Not attached | attach-thing-principal | Device cannot connect without principal |
| Policy-to-cert binding | Attached to thing | Attached to cert | Policies attach to certificates, not things |
| Topic rule SQL | Database-style SQL | Payload-based SQL | Rules engine evaluates MQTT payload, not tables |
| Device shadow | Not configured | Classic/named shadow | Enables offline state sync via delta |
| Private key handling | Stored in plaintext | Stored in secrets mgr | Private key is returned ONCE |
| Protocol | Defaults to HTTPS | MQTT port 8883 | MQTT supports pub/sub; HTTPS is request-response |

---

## Related artifacts

- **Skill definition:** `skills/iot-core-thing-deployer/SKILL.md`
- **Certificate and policy guide:** `skills/iot-core-thing-deployer/references/certificate-and-policy.md`
- **Topic rule and shadow guide:** `skills/iot-core-thing-deployer/references/topic-rule-and-shadow.md`
- **Slash command:** `commands/aws/deploy-iot-core-thing.md`
- **Eval suite:** `skills/iot-core-thing-deployer/evals/evals.json`
- **Legacy test cases:** `skills/iot-core-thing-deployer/eval/test-cases.yaml`
