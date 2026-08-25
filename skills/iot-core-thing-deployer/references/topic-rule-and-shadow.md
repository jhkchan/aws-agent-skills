# Topic Rules and Device Shadow — IoT Core Thing Deployer

Deep reference on topic rule SQL syntax (payload evaluation, wildcard
filters, action types, IAM roles), device shadow mechanics (classic vs
named, delta state, offline sync), and common pitfalls. Loaded on
demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Topic rule SQL

### How the rules engine works

The rules engine intercepts MQTT messages published to the IoT Core
message broker. For each incoming message, it evaluates all active
topic rules whose SQL topic filter matches the message topic. If the
WHERE clause is satisfied, the rule triggers its actions.

```text
Message flow:
  Device publishes → MQTT topic 'device/sensor-001/telemetry'
                   → Payload: {"temperature": 35.2, "humidity": 60}
                       ↓
  Rules engine evaluates ALL rules with matching topic filters:
    Rule 1: SELECT * FROM 'device/+/telemetry' WHERE temperature > 30
            → MATCH (temperature 35.2 > 30) → Action: Timestream write
    Rule 2: SELECT device_id FROM 'device/+/status' WHERE status = 'online'
            → NO MATCH (topic filter does not match)
                       ↓
  Rule actions execute: Timestream write, Lambda invoke, republish, etc.
```

**Critical:** the SQL evaluates against the message PAYLOAD (JSON), not
a database. The FROM clause is a topic filter, not a table name.

### SQL syntax

```sql
SELECT [field1, field2, * | function(...)]
FROM 'topic/filter/with/+wildcards'
[WHERE condition]
```

### SQL functions

| Function | Description |
|---|---|
| `cast(field as type)` | Type conversion |
| `concat(s1, s2)` | String concatenation |
| `get(thingShadow, propertyName)` | Get shadow property |
| `isnull(field, default)` | Null coalescing |
| `substring(s, start, length)` | Substring |
| `lower(s)` / `upper(s)` | Case conversion |
| `truncate(number, digits)` | Truncate decimal |
| `convert_time(epoch)` | Convert epoch to ISO 8601 |
| `topic(n)` | Extract nth topic level |
| `clientid()` | Get client ID |
| `timestamp()` | Get message timestamp |
| `timestamputc()` | Get UTC timestamp |

### Wildcard topic filters

| Filter | Matches | Does NOT match |
|---|---|---|
| `device/+/telemetry` | `device/sensor-001/telemetry` | `device/sensor-001/telemetry/extra` |
| `device/#` | `device/sensor-001/telemetry`, `device/a/b/c` | `other/sensor-001` |
| `device/sensor-001/telemetry` | exact match only | `device/sensor-002/telemetry` |

### Rule actions

| Action | Configuration | Notes |
|---|---|---|
| Republish | topic, roleArn, qos | Publish to another IoT topic |
| Lambda | functionArn, roleArn | Invoke Lambda function |
| S3 | bucketName, key, roleArn | Write to S3 |
| SQS | queueUrl, roleArn, useBase64 | Send to SQS queue |
| DynamoDB | tableName, roleArn, hashKeyField, rangeKeyField | Write to DynamoDB |
| Timestream | databaseName, tableName, dimensions, roleArn | Write to Timestream |
| SNS | targetArn, roleArn | Publish to SNS |
| Kinesis Firehose | deliveryStreamName, roleArn | Write via Firehose |
| CloudWatch Alarm | alarmName, roleArn, stateReason, stateValue | Trigger alarm |
| CloudWatch Logs | roleArn, logGroupName | Write logs |
| Elasticsearch | endpoint, index, type, id, roleArn | Write to ES |
| Step Functions | stateMachineName, executionNamePrefix, roleArn | Start execution |
| IoT Events | inputName, roleArn | Send to IoT Events |
| IoT Analytics | channelName, roleArn | Send to IoT Analytics |

### Error action

Each rule can have an error action that triggers when the main action
fails:

```json
"errorAction": {
  "republish": {
    "roleArn": "arn:aws:iam::123456789012:role/IoTTopicRuleRole",
    "topic": "device/errors",
    "qos": 1
  }
}
```

### IAM role for topic rules

The IAM role must have a trust policy allowing `iot.amazonaws.com`:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": { "Service": "iot.amazonaws.com" },
      "Action": "sts:AssumeRole"
    }
  ]
}
```

And permissions for each downstream action:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["timestream:WriteRecords"],
      "Resource": "arn:aws:timestream:us-east-1:123456789012:database/sensors/table/telemetry"
    },
    {
      "Effect": "Allow",
      "Action": ["iot:Publish"],
      "Resource": "arn:aws:iot:us-east-1:123456789012:topic/device/*"
    },
    {
      "Effect": "Allow",
      "Action": ["lambda:InvokeFunction"],
      "Resource": "arn:aws:lambda:us-east-1:123456789012:function:iot-processor"
    }
  ]
}
```

## Device shadow

### Classic shadow

Each thing has ONE classic shadow. The shadow stores desired and
reported state.

**Shadow topics (classic):**

```text
$aws/things/<thingName>/shadow/update        — update state
$aws/things/<thingName>/shadow/update/accepted — update confirmed
$aws/things/<thingName>/shadow/update/rejected — update rejected
$aws/things/<thingName>/shadow/update/delta   — delta notification
$aws/things/<thingName>/shadow/get           — get current state
$aws/things/<thingName>/shadow/delete        — delete shadow
```

**Shadow document structure:**

```json
{
  "state": {
    "desired": {
      "led": "on",
      "threshold": 30
    },
    "reported": {
      "led": "off",
      "threshold": 25
    },
    "delta": {
      "led": "on",
      "threshold": 30
    }
  },
  "metadata": {
    "desired": {
      "led": { "timestamp": 1630000000 },
      "threshold": { "timestamp": 1630000000 }
    }
  },
  "timestamp": 1630000000,
  "version": 5
}
```

### Named shadows

Named shadows allow multiple independent shadow documents per thing.

**Shadow topics (named):**

```text
$aws/things/<thingName>/shadow/name/<shadowName>/update
$aws/things/<thingName>/shadow/name/<shadowName>/update/delta
$aws/things/<thingName>/shadow/name/<shadowName>/get
$aws/things/<thingName>/shadow/name/<shadowName>/delete
```

**Use cases for named shadows:**
- Separate configuration from firmware state
- Multiple sensors with independent state
- Reduce shadow document size (classic is limited to one document)

### Delta state mechanism

The delta is the difference between desired and reported:

```text
Cloud sets desired: { "led": "on" }
Device reports:     { "led": "off" }

Delta (auto-generated): { "led": "on" }

Device subscribes to delta topic → receives delta notification
Device acts on delta (turns LED on)
Device updates reported: { "led": "on" }

Delta is now empty → sync complete
```

**Key:** the device MUST subscribe to the delta topic and update its
reported state to clear the delta. Without this, the delta persists
indefinitely.

### Shadow via REST API

```bash
# Get shadow
aws iot-data get-thing-shadow --thing-name sensor-001 --region us-east-1

# Update shadow
aws iot-data update-thing-shadow \
  --thing-name sensor-001 \
  --payload '{"state":{"desired":{"led":"on"}}}' \
  --region us-east-1

# Delete shadow
aws iot-data delete-thing-shadow --thing-name sensor-001 --region us-east-1
```

### Named shadow via REST API

```bash
aws iot-data get-thing-shadow \
  --thing-name sensor-001 \
  --shadow-name config \
  --region us-east-1
```

### Shadow versioning

Every shadow update increments the version number. Use version to
detect conflicts:

```json
{
  "state": { "reported": { "led": "on" } },
  "version": 5,
  "timestamp": 1630000000
}
```

If the client sends an update with a stale version, the update is
rejected. This prevents concurrent update conflicts.

## Common pitfalls

### Pitfall 1: Policy attached to thing instead of certificate

**Cause:** operator runs `attach-policy` with the thing ARN as target
instead of the certificate ARN.

**Fix:** the policy target MUST be the certificate ARN, not the thing
ARN. Use `attach-policy --target <cert-arn>`.

### Pitfall 2: Topic rule SQL uses database syntax

**Cause:** operator writes `SELECT * FROM sensors_table` instead of
`SELECT * FROM 'device/+/telemetry'`.

**Fix:** the FROM clause is a topic filter (MQTT topic with wildcards),
not a table name. The SQL evaluates against the message payload.

### Pitfall 3: Shadow delta not clearing

**Cause:** device does not subscribe to the delta topic, or does not
update reported state after acting on the delta.

**Fix:** device must subscribe to `$aws/things/<thing>/shadow/update/
delta` and update reported state to match desired after acting.

### Pitfall 4: Job targets empty thing group

**Cause:** things added to the group after the snapshot job was
created do not receive the job.

**Fix:** for continuous jobs (not snapshot), things added later WILL
receive the job. For snapshot jobs, add things to the group first,
then create the job.

## Expert heuristic: topic rule SQL evaluates against message payload (moved from SKILL.md)

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

## Expert heuristic: device shadow delta state (moved from SKILL.md)

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

## Step 5 — Topic rule (SQL SELECT, republish) CLI (moved from SKILL.md)

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

## Step 6 — Device shadow (classic vs named) (moved from SKILL.md)

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
