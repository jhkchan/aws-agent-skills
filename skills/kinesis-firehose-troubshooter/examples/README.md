# End-to-end usage scenario: kinesis-firehose-troubleshooter

A walkthrough showing the skill diagnosing two Firehose problems in
the same account: a ROOT_CAUSE_FOUND delivery-to-S3 KMS gap and an
ESCALATE OpenSearch circuit breaker. Demonstrates the 5-layer Firehose
health check and the 8-symptom decision tree.

## Input (user prompt)

> Diagnose two Firehose delivery problems: (1) prod-events-delivery
> to S3 has DeliveryToS3.Success at 0% with KMS AccessDenied; (2)
> prod-events-to-opensearch has the circuit breaker engaged because
> the cluster is RED.

```
Diagnosis reference: prod-firehose-triage
Account: 111111111111
Region: us-east-1

Problem 1: Delivery to S3 fails
  Delivery-stream: prod-events-delivery
  Destination: s3 (extended)
  Symptom: DeliveryToS3Fails
  Recent output:
    CloudTrail PutObject: errorMessage "AccessDenied: kms:GenerateDataKey
      on arn:aws:kms:us-east-1:111111111111:key/abc123"
    aws kms get-key-policy: Principal =
      {"AWS": "arn:aws:iam::111111111111:root"} only
    aws s3api head-bucket: 200 (bucket exists)
    DeliveryToS3.Success: 0% for 30 min
    CloudWatch logging: Enabled

Problem 2: Delivery to OpenSearch fails
  Delivery-stream: prod-events-to-opensearch
  Destination: opensearch
  Domain: prod-events-search
  Symptom: OpenSearchFails
  Recent output:
    DeliveryToOpenSearch.Success: 0% for 45 min
    Firehose log: circuit breaker engaged after 5 min sustained 429
    describe-domain-health: ClusterHealth=Red
    2/5 data nodes below disk watermark
    OpenSearch access policy: includes Firehose role (auth OK)
```

## Skill output

```text
DIAGNOSIS: prod-firehose-triage (problem 1)
DELIVERY_STREAM: prod-events-delivery
DESTINATION: s3 (extended)
SYMPTOM: DeliveryToS3Fails
ROOT_CAUSE: KMS key policy on arn:aws:kms:us-east-1:111111111111:key/abc123
            does not grant the Firehose service principal
            kms:GenerateDataKey. The key policy allows only the
            customer account root.
EVIDENCE:
  - CloudTrail PutObject: errorMessage "AccessDenied: kms:GenerateDataKey on arn:aws:kms:us-east-1:111111111111:key/abc123"
  - aws kms get-key-policy: Statement Principal = {"AWS": "arn:aws:iam::111111111111:root"} only
LAYER_CHECK:
  - Source: PASS - IncomingBytes > 0; stream type DirectPut
  - Transform: N/A - no Lambda processing configured
  - Convert: N/A - no format conversion
  - Deliver: FAIL - KMS key policy denies Firehose service principal
  - Observability: PASS - CloudWatch logging enabled
FIX:
  - Add the Firehose service principal to the KMS key policy:
    aws kms put-key-policy --key-id arn:aws:kms:us-east-1:111111111111:key/abc123 --policy-name default --policy '{"Id":"firehose-key-policy","Version":"2012-10-17","Statement":[{"Sid":"Enable IAM permissions","Effect":"Allow","Principal":{"AWS":"arn:aws:iam::111111111111:root"},"Action":"kms:*","Resource":"*"},{"Sid":"Allow Firehose","Effect":"Allow","Principal":{"Service":"firehose.amazonaws.com"},"Action":["kms:GenerateDataKey","kms:Decrypt"],"Resource":"*"}]}'
  - No Firehose-side change; the key policy is the only gap.
VERIFICATION:
  - aws cloudwatch get-metric-statistics --namespace AWS/Firehose --metric-name DeliveryToS3.Success --dimensions Name=DeliveryStreamName,Value=prod-events-delivery --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) --period 60 --statistics Average --output table
  - Expect: Average >= 1.0 within 5-10 minutes of the key policy update.
VERDICT: ROOT_CAUSE_FOUND
NEXT_STEP: None
ESCALATION_PATH: None

DIAGNOSIS: prod-firehose-triage (problem 2)
DELIVERY_STREAM: prod-events-to-opensearch
DESTINATION: opensearch
SYMPTOM: OpenSearchFails
ROOT_CAUSE: OpenSearch domain prod-events-search is in RED cluster
            health. Two data nodes are below the disk watermark.
            Firehose cannot deliver until the cluster returns to
            GREEN or YELLOW.
EVIDENCE:
  - describe-domain-health: ClusterHealth=Red
  - 2/5 nodes show free_storage_below_watermark
  - DeliveryToOpenSearch.Success: 0% for 45 min
  - Firehose log: circuit breaker engaged after 5 min of sustained 429
LAYER_CHECK:
  - Source: PASS - IncomingBytes steady
  - Transform: N/A
  - Convert: N/A
  - Deliver: FAIL - OpenSearch cluster red, circuit breaker engaged
  - Observability: PASS
FIX: Cannot remediate from Firehose side alone - the OpenSearch
  cluster needs disk cleanup, node expansion, or index lifecycle
  action. The Firehose circuit breaker will recover automatically
  once OpenSearch returns to sustained success.
VERIFICATION: After OpenSearch returns to GREEN:
  aws opensearch describe-domain-health --domain-name prod-events-search --query 'DomainStatus.ClusterHealth' --output text --profile opensearch-admin
  Expect: Green. Then Firehose circuit breaker will reset within the configured window.
VERDICT: ESCALATE
NEXT_STEP: Provide the OpenSearch admin with this remediation:
  1. Identify oversized indices: GET _cat/indices?v&s=store.size:desc
  2. Delete or snapshot old indices via the Index State Management policy
  3. Add EBS storage or instance count to free disk above the watermark
ESCALATION_PATH: OpenSearch domain administrator must restore
  prod-events-search to GREEN. Firehose will resume automatically
  once the circuit breaker window clears.
```

**Account-level aggregate verdict: ROOT_CAUSE_FOUND for problem 1
(KMS key policy fix) and ESCALATE for problem 2 (requires
OpenSearch admin action).**

## What the skill caught that a generic assistant misses

1. **The 5-layer health check.** A generic assistant treats each
   symptom in isolation. The skill always runs the 5-layer check
   (source, transform, convert, deliver, observability) first -
   for problem 1 this isolated the deliver-layer KMS gap. For
   problem 2, the layer check confirmed the deliver layer was
   the only failure.

2. **The KMS-service-principal distinction.** A generic assistant
   says "fix the KMS policy." The skill notes that the KMS key
   policy must grant `kms:GenerateDataKey` to the Firehose
   service principal (`firehose.amazonaws.com`), and provides the
   exact policy JSON.

3. **The OpenSearch circuit breaker.** A generic assistant
   recommends restarting the Firehose stream. The skill recognizes
   the circuit breaker engages on sustained 429 and will recover
   automatically - the action is on the OpenSearch side.

4. **The ESCALATE verdict.** A generic assistant attempts a
   remediation that cannot work from Firehose. The skill ESCALATES
   because the OpenSearch cluster state change requires the
   OpenSearch admin.

5. **The verdict shapes.** A generic assistant produces prose. The
   skill emits a deterministic VERDICT (ROOT_CAUSE_FOUND, ESCALATE)
   per problem, enabling downstream automation.

## Slash-command invocation

```
/aws:troubleshoot-kinesis-firehose
```

Or via the orchestrator:

```
/aws:pipeline
You: "why is my Firehose delivery stream failing"
```

## CLI routing

```bash
node cli/bin/cli.js route "Firehose delivery fails"
# [Phase: Troubleshoot | Skills routed: kinesis-firehose-troubleshooter]
```

## Live-account invocation (requires AWS CLI)

```bash
# Run the 5-layer Firehose health check
aws firehose describe-delivery-stream --delivery-stream-name <stream-name> \
  --query 'DeliveryStreamDescription.[DeliveryStreamStatus,DeliveryStreamType,Destinations[0].DestinationId]' \
  --output table --region us-east-1 --profile default

# Per-destination Success metric
aws cloudwatch get-metric-statistics --namespace AWS/Firehose \
  --metric-name DeliveryToS3.Success \
  --dimensions Name=DeliveryStreamName,Value=<stream-name> \
  --start-time $(date -u -v-15M +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average --output table --profile default

# DataFreshness (lag indicator)
aws cloudwatch get-metric-statistics --namespace AWS/Firehose \
  --metric-name DeliveryToS3.DataFreshnessSec \
  --dimensions Name=DeliveryStreamName,Value=<stream-name> \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 60 --statistics Average,Maximum --output table --profile default

# KMS key policy (delivery-to-S3 failures)
aws kms get-key-policy --key-id <key-id> --policy-name default --output text --profile default

# Lambda transform errors
aws logs filter-log-events --log-group-name /aws/lambda/<lambda-function-name> \
  --filter-pattern "ERROR" --start-time $(date -u -v-1H +%s)000 --output table --profile default

# OpenSearch domain health
aws opensearch describe-domain-health --domain-name <domain-name> \
  --query 'DomainStatus.[ClusterHealth,Nodes]' --output table --profile default

# Redshift COPY errors
# (connect to Redshift and run)
# SELECT * FROM stl_load_errors WHERE start_time > dateadd(hour, -1, getdate()) ORDER BY start_time DESC LIMIT 20;

# CloudTrail for AccessDenied
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --start-time $(date -u -v-1H +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --query 'Events[*].[EventTime,Username,ResourceName]' --output table --profile default
```

Then paste the output into the skill for diagnosis.
