# Advanced patterns — iot-core-thing-deployer

Dependency-graph heuristics, fleet operations (Step 7), and advanced provisioning (Step 8), moved verbatim from SKILL.md for progressive disclosure. Load on demand.


## Configuration dependency graph (novel heuristic) (moved from SKILL.md)

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

## Step 7 — IoT jobs, fleet indexing, and monitoring (moved from SKILL.md)

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

## Step 8 — Custom authorizer, protocol, Greengrass (moved from SKILL.md)

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
