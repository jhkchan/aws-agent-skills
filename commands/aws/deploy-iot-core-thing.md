---
description: Provision an AWS IoT Core thing and device pipeline with production-grade defaults (X.509 certificate, IoT policy for MQTT pub/sub, triple binding cert-thing-policy, topic rule with SQL SELECT to Lambda/S3/SQS/DynamoDB/Timestream, device shadow classic and named, IoT jobs for OTA firmware, fleet indexing, custom authorizer, Greengrass component deployment, CloudWatch metrics). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create iot thing"
  - "deploy iot thing"
  - "device certificate x509"
  - "iot policy pub sub"
  - "iot topic rule"
  - "topic rule sql republish"
  - "device shadow"
  - "iot jobs ota firmware"
  - "fleet indexing"
  - "custom authorizer lambda"
  - "mutual tls mqtt"
  - "greengrass component deployment"
  - "iot core"
  - "iot device"
routes_to: iot-core-thing-deployer
---

# /aws:deploy-iot-core-thing

Activate the `iot-core-thing-deployer` skill and provision an AWS IoT
Core thing and device pipeline with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Thing creation, type, and group
2. Device certificate (X.509) — AWS-generated or CSR
3. IoT policy attachment (connect, publish, subscribe, receive)
4. Thing-to-policy binding (attach principal — CRITICAL)
5. Topic rule (SQL SELECT, republish to Lambda/S3/SQS/DynamoDB/Timestream)
6. Device shadow (classic vs named, delta state)
7. IoT jobs (OTA firmware update, rollout config)
8. Fleet indexing (registry, shadow, connectivity)
9. Custom authorizer (Lambda-based authentication)
10. MQTT vs HTTPS broker (protocol selection)
11. Greengrass component deployment (edge compute)
12. CloudWatch metrics (Connect, PublishIn, PublishOut)

## When to use

- You need to create an IoT thing and provision device credentials.
- You need to attach IoT policies for MQTT pub/sub.
- You need to create topic rules to process device messages.
- You need to configure device shadows for state sync.
- You need to deploy IoT jobs for OTA firmware updates.
- You need fleet indexing for thing discovery.
- You need custom authorizers for non-X.509 authentication.
- You need to deploy Greengrass components to edge devices.

## When NOT to use

- **AWS IoT Greengrass standalone** — use Greengrass-specific skills if
  not using IoT Core thing management.
- **AWS IoT Events** — for event detection from IoT messages.
- **AWS IoT SiteWise** — for industrial data collection and analysis.
- **Auditing existing IoT things** — use IoT audit skills.

## How to invoke

### Slash command

```
/aws:deploy-iot-core-thing
```

Then provide: thing name, certificate strategy (AWS-generated or CSR),
IoT policy JSON (connect/publish/subscribe resources), topic rule SQL
and actions, device shadow type (classic/named), IoT job details (if
OTA), fleet indexing mode, custom authorizer details (if custom auth),
protocol (MQTT/HTTPS), Greengrass component (if edge), tags.

### Natural language

Any of these routes to the same skill:

- "create an iot thing with x509 certificate"
- "attach iot policy for mqtt pub sub"
- "create a topic rule to send data to timestream"
- "configure device shadow for offline sync"
- "deploy greengrass component to edge devices"
- "set up fleet indexing for thing search"

### CLI routing

```bash
node cli/bin/cli.js route "create an iot thing"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create IoT things
or device pipelines. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-iot-core-thing

     Create an IoT thing sensor-001 in us-east-1 with X.509
     certificate. Policy for connect, publish to telemetry,
     subscribe to commands. Attach cert to thing and policy
     to cert. Create topic rule to Timestream.

Skill:
  IOT_THING: sensor-001
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Thing: sensor-001 — created
    [✓] Certificate (X.509): ACTIVE
    [✓] Certificate attached to thing: YES
    [✓] Policy attached to certificate: YES
    [✓] Topic rule: telemetry-to-timestream
  VERIFICATION_COMMANDS:
    aws iot describe-thing --thing-name sensor-001 --region us-east-1
    aws iot list-thing-principals --thing-name sensor-001 --region us-east-1
```

## References

- Skill definition: `skills/iot-core-thing-deployer/SKILL.md`
- Certificate and policy guide: `skills/iot-core-thing-deployer/references/certificate-and-policy.md`
- Topic rule and shadow guide: `skills/iot-core-thing-deployer/references/topic-rule-and-shadow.md`
- Eval suite: `skills/iot-core-thing-deployer/evals/evals.json`
