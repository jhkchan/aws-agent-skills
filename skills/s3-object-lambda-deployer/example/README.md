# End-to-End Example: S3 Object Lambda Deployment (PII Redaction)

A walkthrough showing how to use the `s3-object-lambda-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a PII redaction Object Lambda Access Point on a
shared data lake bucket. Analysts query CSV exports that contain SSN,
email, and phone patterns. The Object Lambda must redact these on
retrieval without maintaining a second sanitized copy of each file.

- Bucket: `prod-data-lake`
- Standard AP: `dlake-team-a-ap` (pre-existing)
- OLAP name: `pii-redact-olap`
- Transform Lambda: `pii-redact-fn`
- IAM role: `olap-exec`
- Reserved concurrency: 50
- Operations: GetObject
- Region: `us-east-1`, Account: `111111111111`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-s3-object-lambda
```

Then paste the Object Lambda requirements.

### Option B: Natural language

> Set up an Object Lambda AP called pii-redact-olap on
> prod-data-lake. The supporting standard AP dlake-team-a-ap already
> exists. Create the IAM role olap-exec and the transform Lambda
> pii-redact-fn that redacts SSN/email/phone. Set reserved
> concurrency to 50. GetObject only.

---

## Step 2 — Skill pre-flight

The skill validates prerequisites:

1. Bucket `prod-data-lake` baseline (BPA, SSE-KMS, versioning) — all pass
2. Standard AP `dlake-team-a-ap` exists with AP policy allowing the
   Lambda role to GetObject — confirmed
3. IAM role `olap-exec` will be created with trust
   `s3-object-lambda.amazonaws.com` and `WriteGetObjectResponse`
4. Transform Lambda `pii-redact-fn` will use `WriteGetObjectResponse`
   (NOT `return`)
5. Reserved concurrency 50 set before traffic starts
6. No dual-operation gap (GetObject explicitly listed)

All prerequisites pass.

---

## Step 3 — Expected output

```text
OBJECT_LAMBDA_SPEC: pii-redact-olap
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Bucket baseline: prod-data-lake, BPA all 4 True, SSE-KMS, versioning Enabled
  [✓] Supporting standard AP: dlake-team-a-ap with Lambda-read policy on arn:aws:iam::111111111111:role/olap-exec
  [✓] IAM execution role: olap-exec, trust=s3-object-lambda.amazonaws.com, perms include s3-object-lambda:WriteGetObjectResponse
  [✓] Transform Lambda: pii-redact-fn (python3.12, index.handler, uses WriteGetObjectResponse)
  [✓] Reserved concurrency: 50 (expected peak ~40 GETs/sec)
  [✓] Object Lambda AP: pii-redact-olap, SupportingAccessPoint=arn:aws:s3:us-east-1:111111111111:accesspoint/dlake-team-a-ap
  [✓] TransformationConfiguration: operations=[GetObject]
  [OPTIONAL] Multi-region / GetObjectACL / range downloads: none
VERIFICATION_COMMANDS:
  aws s3control get-access-point --account-id 111111111111 --name dlake-team-a-ap
  aws s3control get-access-point-policy --account-id 111111111111 --name dlake-team-a-ap
  aws s3control get-access-point-for-object-lambda --account-id 111111111111 --name pii-redact-olap
  aws s3control get-access-point-configuration-for-object-lambda --account-id 111111111111 --name pii-redact-olap
  aws lambda get-function --function-name pii-redact-fn
  aws lambda get-function-concurrency --function-name pii-redact-fn
```

---

## Step 4 — Provisioning commands

```bash
# IAM role
aws iam create-role --role-name olap-exec --assume-role-policy-document file://trust.json
aws iam put-role-policy --role-name olap-exec --policy-name ObjectLambdaExec --policy-document file://exec.json

# Transform Lambda
zip transform.zip index.py
aws lambda create-function \
  --function-name pii-redact-fn \
  --runtime python3.12 \
  --role arn:aws:iam::111111111111:role/olap-exec \
  --handler index.handler --zip-file fileb://transform.zip \
  --timeout 30 --memory-size 512

# Reserved concurrency (BEFORE traffic starts)
aws lambda put-function-concurrency --function-name pii-redact-fn --reserved-concurrent-executions 50

# Object Lambda Access Point
aws s3control create-access-point-for-object-lambda \
  --account-id 111111111111 --name pii-redact-olap \
  --configuration SupportingAccessPoint=arn:aws:s3:us-east-1:111111111111:accesspoint/dlake-team-a-ap

# TransformationConfiguration
aws s3control put-access-point-configuration-for-object-lambda \
  --account-id 111111111111 --name pii-redact-olap \
  --configuration '{"SupportingAccessPoint":"arn:aws:s3:us-east-1:111111111111:accesspoint/dlake-team-a-ap","TransformationConfigurations":[{"Actions":["GetObject"],"ContentTransformation":{"AwsLambda":{"FunctionArn":"arn:aws:lambda:us-east-1:111111111111:function:pii-redact-fn"}}}]}'
```

---

## Step 5 — Post-deployment verification

```bash
# Confirm the OLAP and TransformationConfiguration
aws s3control get-access-point-configuration-for-object-lambda \
  --account-id 111111111111 --name pii-redact-olap

# Confirm reserved concurrency
aws lambda get-function-concurrency --function-name pii-redact-fn

# Invoke a real GET against the OLAP hostname and verify the transform fires
aws s3api get-object \
  --bucket arn:aws:s3-object-lambda:us-east-1:111111111111:accesspoint/pii-redact-olap \
  --key sample.csv output.csv

# CloudWatch Lambda invocations (transform fired)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda --metric-name Invocations \
  --dimensions Name=FunctionName,Value=pii-redact-fn \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum

# CloudWatch Lambda throttles (concurrency exhausted — should be 0)
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda --metric-name Throttles \
  --dimensions Name=FunctionName,Value=pii-redact-fn \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum
```

---

## Common pitfalls to verify after deployment

1. **Lambda uses `WriteGetObjectResponse`, not `return`.** A Lambda
   that `return`s the body produces a clean exit and an empty client
   response. Verify in CloudWatch Logs that
   `write_get_object_response` is called with `RequestRoute` and
   `RequestToken` from the event.

2. **IAM role includes `s3-object-lambda:WriteGetObjectResponse`.**
   Without it, the Lambda exits cleanly and the client receives an
   empty object — no error surfaced. Verify with
   `aws iam get-role-policy --role-name olap-exec`.

3. **Reserved concurrency is set before traffic starts.** A traffic
   spike without reserved concurrency throttles the Lambda; clients
   see S3-shaped `AccessDenied`. Verify with
   `aws lambda get-function-concurrency`.

4. **Operations list is explicit.** Operations not listed in the
   TransformationConfiguration bypass the transform silently. If
   HeadObject should also be transformed, add it to the actions list.
