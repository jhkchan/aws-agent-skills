---
name: iot-core-thing-deployer
description: 'Provisions AWS IoT Core things and device pipelines: thing creation, thing type, thing group, device certificate (X.509) with key pair generation, IoT policy attachment (pub/sub to MQTT topics), topic rule (SQL SELECT republish to Lambda/S3/SQS/DynamoDB/Timestream), device shadow (classic vs named), IoT jobs (OTA firmware update), fleet indexing, custom authorizer (Lambda), mutual TLS, message broker (MQTT vs HTTPS), rules engine SQL, Greengrass component deployment, CloudWatch metrics (Connect, PublishIn, PublishOut), and thing-to-policy binding. Emits a READY_TO_DEPLOY checklist. Triggers: create iot thing, device certificate x509, iot policy pub sub, topic rule sql republish, device shadow classic named, iot jobs ota firmware, fleet indexing, custom authorizer lambda, mutual tls mqtt https, greengrass component deployment.'
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with iot access. Works with Terraform aws_iot_thing / aws_iot_certificate / aws_iot_policy / aws_iot_topic_rule resources and CloudFormation AWS::IoT::Thing / AWS::IoT::TopicRule templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: Networking
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, iot-core, iot-thing, cloudops, deploy, networking, provisioning, mqtt, x509, device-shadow, topic-rule, greengrass
  dependencies: aws-orchestrator
  keywords: aws, iot core, iot thing, device certificate, x.509, iot policy, topic rule, device shadow, cloudops, deploy, provisioning, mqtt, greengrass, fleet indexing, custom authorizer
  when_to_use: Invoke when the user wants to create an IoT thing, provision device certificates, attach IoT policies for MQTT pub/sub, create topic rules with SQL SELECT to republish to Lambda/S3/SQS/DynamoDB/ Timestream, configure device shadows, deploy IoT jobs for OTA firmware, enable fleet indexing, set up custom authorizers, or deploy Greengrass components. Do NOT invoke for AWS IoT Greengrass standalone, AWS IoT Events, or AWS IoT SiteWise.
---

# IoT Core Thing Deployer

An AWS CloudOps agent skill that provisions AWS IoT Core things and
device pipelines with correct defaults. The skill walks the operator
through thing creation, device certificate (X.509) provisioning, IoT
policy attachment for MQTT pub/sub, topic rules with SQL SELECT,
device shadow configuration (classic vs named), IoT jobs for OTA
firmware, fleet indexing, custom authorizers, mutual TLS, message
broker selection (MQTT vs HTTPS), Greengrass component deployment,
and CloudWatch metrics — captures device topology decisions, explains
why each default matters, and emits a READY_TO_DEPLOY checklist.

## Activation keywords

create IoT thing, device certificate X.509, IoT policy pub sub, topic
rule SQL republish, device shadow classic named, IoT jobs OTA firmware,
fleet indexing, custom authorizer Lambda, mutual TLS MQTT HTTPS,
Greengrass component deployment.

## STRICT output contract

When this skill is invoked with an IoT-Core-provisioning request, the
agent MUST respond with the READY_TO_DEPLOY checklist defined in the
"Output format" section using the literal all-caps labels `IOT_THING:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from
the literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### Decision tree leading to the output

```text
1. Does the thing exist (create-thing returned a thingArn)?
   ├─ YES → go to 2
   └─ NO  → VERDICT: PREREQ_MISSING ([✗] Thing: not created)
2. Does the certificate exist AND is it ACTIVE?
   ├─ YES → go to 3
   └─ NO  → VERDICT: PREREQ_MISSING ([✗] Certificate: missing or not ACTIVE)
3. Is the certificate ATTACHED to the thing (attach-thing-principal)?
   ├─ YES → go to 4
   └─ NO  → VERDICT: PREREQ_MISSING ([✗] Certificate attached to thing: NO)
4. Is the IoT policy ATTACHED to the CERTIFICATE (attach-policy,
        NOT attach-thing-principal)?
   ├─ YES → go to 5
   └─ NO  → VERDICT: PREREQ_MISSING ([✗] Policy attached to certificate: NO)
5. If a topic rule is requested, does the IAM role exist with trust
   policy for iot.amazonaws.com AND downstream action perms?
   ├─ YES → go to 6
   └─ NO  → VERDICT: PREREQ_MISSING ([✗] Topic rule IAM role: missing)
6. Emit CHECKLIST with [✓] on every line + VERIFICATION_COMMANDS.
```

### FORBIDDEN output patterns

1. **NEVER preface the block with prose, greetings, or "Here is...".**
   The first line of the response MUST be `IOT_THING:`.
2. **NEVER emit `VERDICT: READY_TO_DEPLOY` when any CHECKLIST line is
   `[✗]`.** A single `[✗]` forces `VERDICT: PREREQUISITES_MISSING`.
3. **NEVER use placeholder text** (`<thing-name>`, `<cert-id>`, `XXX`)
   in a worked example. Use real thing names, real certificate ARNs,
   real policy names, and real SQL statements.
4. **NEVER list the policy as "attached to thing".** IoT policies attach
   to the CERTIFICATE (principal), not the thing. The CHECKLIST line
   MUST read `Policy attached to certificate: YES`.
5. **NEVER show a topic rule SQL without quoting the topic filter.**
   SQL MUST use real MQTT topic filters with `+`/`#` wildcards, e.g.
   `SELECT temperature FROM 'device/+/telemetry' WHERE temperature > 30`.
6. **NEVER omit the certificate ARN.** A bare cert-id without the full
   `arn:aws:iot:region:account:cert/<id>` ARN is unresolvable downstream.
7. **NEVER list a topic rule action without the IAM role ARN.** Every
   action (Timestream, Lambda, S3, republish) needs a role ARN.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Thing creation, type, and group | Core thing model |
| Step 2 — Device certificate (X.509) | Certificate provisioning |
| Step 3 — IoT policy attachment (pub/sub) | MQTT authorization |
| Step 4 — Thing-to-policy binding (attach principal) | Linking cert+policy+thing |
| Step 5 — Topic rule (SQL SELECT, republish) | Rules engine |
| Step 6 — Device shadow (classic vs named) | Device state |
| Step 7 — IoT jobs, fleet indexing, and monitoring | Fleet ops |
| Step 8 — Custom authorizer, protocol, Greengrass | Advanced |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/certificate-and-policy.md | Cert + policy + binding detail |
| references/topic-rule-and-shadow.md | Rules engine + shadow detail |

## Mindset

**One-line takeaway:** An IoT thing is a digital representation of a
physical device. To connect securely, the thing needs an X.509
certificate, an IoT policy granting MQTT pub/sub permissions, and the
certificate must be ATTACHED to both the thing and the policy. Topic
rules process messages via SQL SELECT. Device shadow stores desired
and reported state for offline sync.

Three misconceptions dominate IoT Core misdesign at provisioning time:

- **"Creating a thing is enough to connect."** It is not. A thing
  alone has no credentials. You need: (1) a thing, (2) an X.509
  certificate, (3) an IoT policy, AND (4) the certificate attached to
  BOTH the thing and the policy. Missing any binding = connection
  refused.

- **"The topic rule SQL runs against the database."** It does not.
  The rules engine SQL evaluates against the MQTT message PAYLOAD
  (JSON), not a database. `SELECT * FROM 'topic/filter'` selects
  message payload fields, not table rows.

- **"Device shadow and topic rules are the same."** They are not.
  Topic rules react to incoming messages (event-driven). Device shadow
  is a key-value store for device state (desired vs reported). The
  shadow has a delta state that triggers when desired and reported
  diverge.

## Configuration dependency graph (novel heuristic)

IoT Core configurations are NOT independent. The certificate must exist
before it can be attached to a thing. The policy must exist before it
can be attached to a certificate. Topic rules need an IAM role for
downstream actions. Device shadow is enabled per-thing.

| Configuration | Hard dependencies | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Thing | IAM `iot:CreateThing` | name is immutable | cert attachment, shadow, jobs |
| Thing group | IAM `iot:CreateThingGroup` | supports hierarchical groups | bulk job targeting |
| Certificate (X.509) | CSR or AWS-generated key pair | cert ARN required for all attachments; must be ACTIVE | thing binding, policy binding |
| IoT policy | JSON policy document | defines MQTT connect/publish/subscribe/resource ARN patterns | certificate attachment |
| Attach cert→thing | thing + cert exist; IAM `iot:AttachThingPrincipal` | REQUIRED — without it cert is not bound to thing | device connection |
| Attach policy→cert | cert + policy exist; IAM `iot:AttachPolicy` | REQUIRED — without it cert has no permissions | MQTT authorization |
| Topic rule | IAM role for action; SQL statement | SQL evaluates against message PAYLOAD; role needs downstream perms | message-to-Lambda/S3/SQS/etc |
| Device shadow | Thing exists | created on first update; classic uses standard topics; named uses /name/<name>/ | offline state sync |
| IoT job | Job document; target things/groups | job doc must be valid JSON; rollout per config | OTA firmware, config updates |
| Fleet indexing | IAM `iot:CreateIndex` | indexing takes time to build | thing search and discovery |
| Custom authorizer | Lambda function; IAM role | Lambda must return auth result; authorizer must be ACTIVE | custom device authentication |
| Greengrass component | Core device registered; recipe | deployed to thing group; async | edge compute |

**The certificate-thing-policy binding row is the one a baseline model
misses.** Creating a thing, certificate, and policy is necessary but
NOT sufficient. The certificate must be ATTACHED to the thing
(`attach-thing-principal`) AND the policy must be ATTACHED to the
certificate (`attach-policy`). Missing either binding = device cannot
connect.

**Cross-dependency gotchas:**
- The IoT policy is attached to the CERTIFICATE (principal), not the
  thing. A thing can have multiple certificates; each has its own
  policy set.
- Topic rule SQL evaluates message payload JSON, NOT a database.
- Device shadow classic uses topic `$aws/things/<thingName>/shadow/`.
  Named shadows use
  `$aws/things/<thingName>/shadow/name/<shadowName>/`.
- Custom authorizers are invoked BEFORE the IoT policy — the authorizer
  authenticates, then the policy authorizes.

## Expert heuristic: the cert-policy-thing triple binding

A baseline model says "create a thing and a certificate." The correct
heuristic recognizes that three artifacts must be created AND two
bindings must be established for a device to connect.

```text
Device connection requires:
  1. Thing created:     aws iot create-thing
  2. Certificate:       aws iot create-keys-and-certificate (or CSR)
  3. Policy created:    aws iot create-policy
  4. Bind cert→thing:   aws iot attach-thing-principal
  5. Bind policy→cert:  aws iot attach-policy

  Missing step 4 → device connects but thing has no principal
  Missing step 5 → device connects but has no pub/sub permissions
  Missing BOTH   → device gets connection refused

  Certificate = identity (who), Policy = authorization (what),
  Thing = representation (where). All three must be linked.
```

**Key implication:** the #1 cause of "my device can't connect to IoT
Core" is a missing cert-to-thing or policy-to-cert attachment.

## Expert heuristic: topic rule SQL evaluates against message payload

A baseline model writes topic rule SQL like database SQL. The correct
heuristic recognizes that the rules engine SQL operates on MQTT message
payloads (JSON), not tables.

```text
Incoming MQTT message:
  Topic: 'device/sensor-001/telemetry'
  Payload: {"temperature": 35.5, "humidity": 60, "device_id": "sensor-001"}

SQL: SELECT temperature, device_id FROM 'device/+/telemetry'
       WHERE temperature > 30

Result (when temperature > 30):
  {"temperature": 35.5, "device_id": "sensor-001"}

Rule action: republish to 'device/alerts'
OR: invoke Lambda, write to S3/SQS/DynamoDB/Timestream

Key: SQL runs on the PAYLOAD, not any database.
Wildcards: + = single level, # = multi level in topic filter.
```

## Expert heuristic: device shadow delta state

```text
Shadow state machine:
  Reported (device → cloud):  device reports actual state
  Desired (cloud → device):   cloud tells device target state
  Delta:                       desired != reported

  When desired != reported → delta non-empty → device notified
  When device updates reported to match → delta empty → sync done

  Classic: $aws/things/<thing>/shadow/update
  Named:   $aws/things/<thing>/shadow/name/<name>/update
```

**Key implication:** the delta state is the sync mechanism. The device
must subscribe to the delta topic and update reported to clear it.

## Prerequisites (verify before provisioning)

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| IoT Core endpoint | Devices need account-specific endpoint | `aws iot describe-endpoint --endpoint-type iot:Data-ATS` |
| Certificate strategy | CSR or AWS-generated key pair | Decide approach |
| IAM role for topic rules | Rule actions need permissions | `aws iam get-role --role-name <name>` |
| Lambda function (if authorizer) | Authorizer Lambda must exist | `aws lambda get-function` |
| Greengrass core (if Greengrass) | Core device must be registered | `aws greengrassv2 list-core-devices` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`.

## Step 1 — Thing creation, type, and group

```bash
# Create a thing
aws iot create-thing --thing-name "sensor-001" --region us-east-1

# Create thing type and associate
aws iot create-thing-type --thing-type-name "temperature-sensor"
aws iot update-thing --thing-name "sensor-001" --thing-type-name "temperature-sensor"

# Create thing group and add thing
aws iot create-thing-group --thing-group-name "factory-floor-sensors"
aws iot add-thing-to-thing-group \
  --thing-name "sensor-001" \
  --thing-group-name "factory-floor-sensors" --region us-east-1
```

Thing groups support hierarchical nesting and bulk job targeting.

## Step 2 — Device certificate (X.509)

**Option A: AWS-generated key pair:**

```bash
CERT_ARN=$(aws iot create-keys-and-certificate \
  --set-as-active \
  --public-key-outfile public.key \
  --private-key-outfile private.key \
  --certificate-pem-outfile certificate.pem \
  --query 'certificateArn' --output text \
  --region us-east-1)
```

**Option B: CSR (device generates own key — more secure):**

```bash
CERT_ARN=$(aws iot create-certificate-from-csr \
  --certificate-signing-request file://device.csr \
  --set-as-active \
  --query 'certificateArn' --output text \
  --region us-east-1)
```

**Critical:** the private key is returned ONLY once. Store it securely.
If lost, the certificate must be revoked and re-created.

## Step 3 — IoT policy attachment (pub/sub)

```bash
aws iot create-policy \
  --policy-name "sensor-publish-policy" \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect":"Allow","Action":["iot:Connect"],
       "Resource":"arn:aws:iot:us-east-1:123456789012:client/sensor-*"},
      {"Effect":"Allow","Action":["iot:Publish"],
       "Resource":"arn:aws:iot:us-east-1:123456789012:topic/device/+/telemetry"},
      {"Effect":"Allow","Action":["iot:Subscribe"],
       "Resource":"arn:aws:iot:us-east-1:123456789012:topicfilter/device/+/commands"},
      {"Effect":"Allow","Action":["iot:Receive"],
       "Resource":"arn:aws:iot:us-east-1:123456789012:topic/device/+/commands"}
    ]
  }' --region us-east-1
```

**Policy actions:** `iot:Connect` (client ID), `iot:Publish` (topic),
`iot:Subscribe` (topic filter), `iot:Receive` (subscribed topics),
`iot:RetainPublish`, shadow actions (`Get/Update/DeleteThingShadow`).

**Attach policy to certificate:**

```bash
aws iot attach-policy \
  --policy-name "sensor-publish-policy" \
  --target "$CERT_ARN" --region us-east-1
```

## Step 4 — Thing-to-policy binding (attach principal)

The certificate must be attached to the thing (as its principal).

```bash
aws iot attach-thing-principal \
  --thing-name "sensor-001" \
  --principal "$CERT_ARN" --region us-east-1
```

**Verify the complete binding:**

```bash
aws iot list-thing-principals --thing-name "sensor-001" --region us-east-1
aws iot list-principal-policies --principal "$CERT_ARN" --region us-east-1
aws iot describe-certificate --certificate-id "<cert-id>" --region us-east-1
```

The triple binding: thing ← certificate → policy. All three links
verified.

## Step 5 — Topic rule (SQL SELECT, republish)

```bash
aws iot create-topic-rule \
  --rule-name "telemetry-to-timestream" \
  --topic-rule-payload '{
    "sql": "SELECT temperature, humidity, device_id FROM '\''device/+/telemetry'\'' WHERE temperature > 30",
    "ruleDisabled": false,
    "awsIotSqlVersion": "2016-03-23",
    "actions": [
      {"timestream": {
        "roleArn": "arn:aws:iam::123456789012:role/IoTTopicRuleRole",
        "databaseName": "sensors", "tableName": "telemetry",
        "dimensions": [{"name":"device_id","value":"${device_id}"}]
      }},
      {"republish": {
        "roleArn": "arn:aws:iam::123456789012:role/IoTTopicRuleRole",
        "topic": "device/alerts", "qos": 1
      }}
    ],
    "errorAction": {
      "republish": {
        "roleArn": "arn:aws:iam::123456789012:role/IoTTopicRuleRole",
        "topic": "device/errors", "qos": 1
      }
    }
  }' --region us-east-1
```

**Available actions:** republish, Lambda, S3, SQS, DynamoDB, Timestream,
SNS, Kinesis Firehose, CloudWatch Alarm/Logs, Elasticsearch, Step
Functions, IoT Events, IoT Analytics.

**Topic rule IAM role** needs trust policy for `iot.amazonaws.com` and
permissions for each downstream action (e.g., `timestream:WriteRecords`,
`iot:Publish`, `lambda:InvokeFunction`).

## Step 6 — Device shadow (classic vs named)

**Classic shadow** — one shadow per thing:

```text
Topics: $aws/things/<thing>/shadow/update | /get | /delete
```

**Named shadow** — multiple shadows per thing:

```text
Topics: $aws/things/<thing>/shadow/name/<name>/update | /get | /delete
```

**Shadow document:**

```json
{
  "state": {
    "desired": { "led": "on", "threshold": 30 },
    "reported": { "led": "off", "threshold": 25 }
  },
  "version": 3, "timestamp": 1630000000
}
```

**Delta:** when desired != reported, the delta is non-empty. Devices
subscribe to `.../shadow/update/delta` to receive notifications and
update reported to clear the delta.

## Step 7 — IoT jobs, fleet indexing, and monitoring

### IoT jobs (OTA firmware update)

```bash
aws iot create-job \
  --job-id "firmware-update-v2-1" \
  --targets "arn:aws:iot:us-east-1:123456789012:thinggroup/factory-floor-sensors" \
  --document-source "s3://my-job-bucket/firmware-update-v2.1.json" \
  --target-selection "SNAPSHOT" \
  --job-execution-rollout-config '{"maximumPerMinute": 10}' \
  --region us-east-1
```

`maximumPerMinute` controls deployment rate. For continuous jobs
(`CONTINUOUS`), things added to the group later also receive the job.

### Fleet indexing

```bash
aws iot update-indexing-configuration \
  --thing-indexing-configuration '{
    "thingIndexingMode": "REGISTRY_AND_SHADOW",
    "thingConnectivityIndexingMode": "STATUS",
    "namedShadowIndexingMode": "ON"
  }' --region us-east-1

aws iot search-index \
  --index-name "AWS_Things" \
  --query-string "connectivity.connected:true" \
  --region us-east-1
```

### CloudWatch metrics

IoT Core publishes: `Connect.AuthError`, `Connect.Success`,
`PublishIn.Success`, `PublishOut.Success`, `Subscribe.Success`,
`Rules.Executed`, `Rules.Failed`.

```bash
aws cloudwatch put-metric-alarm \
  --alarm-name "IoT-Connection-Auth-Errors" \
  --metric-name "Connect.AuthError" --namespace "AWS/IoT" \
  --statistic "Sum" --period 300 --threshold 10 \
  --comparison-operator "GreaterThanThreshold" \
  --evaluation-periods 1 --region us-east-1
```

## Step 8 — Custom authorizer, protocol, Greengrass

### Custom authorizer (Lambda)

Custom authorizers authenticate devices using custom logic beyond
X.509. The Lambda function returns `isAuthenticated`, `principalId`,
and `policyDocuments`.

```bash
aws iot create-authorizer \
  --authorizer-name "custom-device-auth" \
  --authorizer-function-arn "arn:aws:lambda:us-east-1:123456789012:function:iot-authorizer" \
  --token-key-name "token" \
  --token-signing-public-keys '{"key-1":"-----BEGIN PUBLIC KEY-----\n...\n-----END PUBLIC KEY-----"}' \
  --status "ACTIVE" --region us-east-1
```

The IAM role for IoT to invoke Lambda needs trust policy for
`iot.amazonaws.com` and `lambda:InvokeFunction` permission. The
authorizer must be ACTIVE to be invoked.

### MQTT vs HTTPS broker

| Protocol | Use case | Port | Notes |
|---|---|---|---|
| MQTT over TLS | Persistent, low latency, pub/sub | 8883 | Recommended for devices |
| MQTT over WSS | Through firewalls/proxies | 443 | Web-based devices |
| HTTPS | Request-response only | 443 | Simple ingestion |

**QoS levels:** QoS 0 (at most once), QoS 1 (at least once), QoS 2
(exactly once). Use QoS 1+ for critical commands.

### Greengrass component deployment

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/factory-edge-devices" \
  --deployment-name "deploy-telemetry-component" \
  --components '{
    "com.example.TelemetryAgent": {
      "componentVersion": "1.0.0",
      "configurationUpdate": {"MERGE": {"sampleRate": "5s"}}
    }
  }' --region us-east-1
```

Core device must be registered and online to receive the deployment.

## NEVER do these things

1. **NEVER assume creating a thing is enough to connect.** The thing
   needs a certificate AND a policy, with BOTH bindings established
   (cert→thing and policy→cert). Missing either = connection refused.

2. **NEVER attach an IoT policy to a thing.** Policies attach to the
   CERTIFICATE (principal), not the thing. Use `attach-policy` with
   the certificate ARN.

3. **NEVER write topic rule SQL like database SQL.** The SQL evaluates
   against MQTT message PAYLOAD (JSON). FROM is a topic filter, not a
   table name.

4. **NEVER store the private key insecurely.** The private key from
   `create-keys-and-certificate` is returned ONCE. Store in secrets
   manager. If lost, revoke and re-create.

5. **NEVER use HTTPS for high-frequency pub/sub.** HTTPS is
   request-response only. MQTT (port 8883) supports persistent
   connections and pub/sub.

6. **NEVER confuse device shadow with topic rules.** Shadow stores
   device state (desired/reported/delta). Topic rules react to
   incoming messages. Different purposes.

7. **NEVER create a job targeting a thing group before things are in
   the group.** For snapshot jobs, add things first. Continuous jobs
   reach later additions.

8. **NEVER leave a custom authorizer in DRAFT status.** Must be ACTIVE
   to be invoked. Devices fail to connect otherwise.

9. **NEVER deploy Greengrass components without verifying the core
   device is online.** Deployments are async; errors surface only
   when the device reconnects.

10. **NEVER use QoS 0 for critical commands.** QoS 0 is fire-and-forget.
    Use QoS 1 (at least once) or QoS 2 (exactly once) for critical
    device commands.

## Output format

```text
IOT_THING: <thing-name> (<thing-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Thing: <thing-name> — created
  [✓|✗] Thing type: <type-name> | none
  [✓|✗] Thing group: <group-name> | none
  [✓|✗] Certificate (X.509): <cert-id> — ACTIVE
  [✓|✗] Certificate attached to thing: YES (principal linked)
  [✓|✗] IoT policy: <policy-name> — created
  [✓|✗] Policy attached to certificate: YES (authorization linked)
  [✓|✗] Topic rule: <rule-name> — SQL: <sql-summary>
  [✓|✗] Topic rule IAM role: <role-arn>
  [✓|✗] Topic rule actions: <action-list>
  [✓|✗] Device shadow: <classic|named:<name>> | none
  [✓|✗] IoT job: <job-id> — <status> | none
  [✓|✗] Fleet indexing: <mode> | disabled
  [✓|✗] Custom authorizer: <name> — ACTIVE | none
  [✓|✗] Protocol: MQTT (port 8883) | HTTPS (port 443)
  [✓|✗] Greengrass: <component>:<version> deployed to <target> | none
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws iot describe-thing --thing-name <thing-name> --region <region>
  aws iot list-thing-principals --thing-name <thing-name> --region <region>
  aws iot describe-certificate --certificate-id <cert-id> --region <region>
  aws iot get-topic-rule --rule-name <rule-name> --region <region>
```

### Worked example — sensor thing with cert, policy, Timestream rule, shadow

```text
IOT_THING: sensor-001 (arn:aws:iot:us-east-1:123456789012:thing/sensor-001)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Thing: sensor-001 — created
  [✓] Thing type: temperature-sensor
  [✓] Thing group: factory-floor-sensors
  [✓] Certificate (X.509): arn:aws:iot:us-east-1:123456789012:cert/a1b2c3d4e5f6g7h8i9j0 — ACTIVE
  [✓] Certificate attached to thing: YES (attach-thing-principal verified)
  [✓] IoT policy: sensor-publish-policy — created
      Policy JSON:
        {
          "Version": "2012-10-17",
          "Statement": [
            {"Effect":"Allow","Action":["iot:Connect"],
             "Resource":"arn:aws:iot:us-east-1:123456789012:client/sensor-*"},
            {"Effect":"Allow","Action":["iot:Publish"],
             "Resource":"arn:aws:iot:us-east-1:123456789012:topic/device/+/telemetry"},
            {"Effect":"Allow","Action":["iot:Subscribe"],
             "Resource":"arn:aws:iot:us-east-1:123456789012:topicfilter/device/+/commands"},
            {"Effect":"Allow","Action":["iot:Receive"],
             "Resource":"arn:aws:iot:us-east-1:123456789012:topic/device/+/commands"}
          ]
        }
  [✓] Policy attached to certificate: YES (attach-policy target=cert ARN)
  [✓] Topic rule: telemetry-to-timestream
      SQL: SELECT temperature, humidity, device_id FROM 'device/+/telemetry'
             WHERE temperature > 30
  [✓] Topic rule IAM role: arn:aws:iam::123456789012:role/IoTTopicRuleRole
      (trust: iot.amazonaws.com; perms: timestream:WriteRecords, iot:Publish)
  [✓] Topic rule actions: Timestream (database=sensors, table=telemetry),
        Republish (topic=device/alerts, qos=1); errorAction: Republish
        (topic=device/errors)
  [✓] Device shadow: classic
      (topics: $aws/things/sensor-001/shadow/update | /get | /delete)
  [✓] IoT job: none
  [✓] Fleet indexing: REGISTRY_AND_SHADOW (connectivity=STATUS, namedShadow=ON)
  [✓] Custom authorizer: none
  [✓] Protocol: MQTT over TLS (port 8883), QoS 1 for telemetry
  [✓] Greengrass: none
  [✓] Tags: Environment=production, DeviceType=sensor, Site=factory-floor
VERIFICATION_COMMANDS:
  aws iot describe-thing --thing-name sensor-001 --region us-east-1
  aws iot list-thing-principals --thing-name sensor-001 --region us-east-1
  aws iot describe-certificate --certificate-id a1b2c3d4e5f6g7h8i9j0 --region us-east-1
  aws iot list-principal-policies --principal arn:aws:iot:us-east-1:123456789012:cert/a1b2c3d4e5f6g7h8i9j0 --region us-east-1
  aws iot get-topic-rule --rule-name telemetry-to-timestream --region us-east-1
  aws iot-data get-thing-shadow --thing-name sensor-001 --region us-east-1
```

## Error handling

### Device cannot connect (connection refused)
- Verify certificate is ACTIVE. Verify policy is attached to the
  CERTIFICATE (not the thing). Verify certificate is attached to the
  thing as a principal. Check `iot:Connect` resource matches client ID.

### Topic rule not triggering
- Verify SQL topic filter matches the MQTT topic. Check IAM role
  permissions. Look at the error action topic. Verify rule is enabled.

### Device shadow delta not clearing
- Device must update reported state to match desired. If device is
  offline, delta persists until reconnection and update.

### Job not reaching devices
- Verify things are in the target group. Check rollout rate. Verify
  job is IN_PROGRESS. For snapshot jobs, things added later do not
  receive the job.

### Custom authorizer errors
- Verify authorizer is ACTIVE. Check Lambda logs. Verify signing keys.
  Test with `iot test-invoke-authorizer`.

## Domain

AWS CloudOps / AWS IoT Core Thing & Device Pipeline Provisioning.

## AWS documentation

- **IoT Core Developer Guide** — https://docs.aws.amazon.com/iot/latest/developerguide/what-is-aws-iot.html
- **Thing management** — https://docs.aws.amazon.com/iot/latest/developerguide/iot-thing-management.html
- **X.509 certificates** — https://docs.aws.amazon.com/iot/latest/developerguide/x509-certs.html
- **IoT policies** — https://docs.aws.amazon.com/iot/latest/developerguide/iot-policies.html
- **Topic rules** — https://docs.aws.amazon.com/iot/latest/developerguide/iot-rules.html
- **Device shadow** — https://docs.aws.amazon.com/iot/latest/developerguide/iot-device-shadows.html
- **IoT jobs** — https://docs.aws.amazon.com/iot/latest/developerguide/iot-jobs.html
- **Custom authorizers** — https://docs.aws.amazon.com/iot/latest/developerguide/custom-authentication.html
- **Greengrass V2** — https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html
