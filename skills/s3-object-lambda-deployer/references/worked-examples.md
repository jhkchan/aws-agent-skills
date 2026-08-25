# Worked Examples — S3 Object Lambda Deployer

Full worked outputs moved from SKILL.md. Load on demand.

## Output format (checklist template)

```
OBJECT_LAMBDA_SPEC: <olap-name>
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Bucket baseline (BPA, SSE, versioning): verified
  [✓|✗] Supporting standard AP: created (<STANDARD_AP_NAME>) with Lambda-read policy
  [✓|✗] IAM execution role: trust=s3-object-lambda, perms include WriteGetObjectResponse
  [✓|✗] Transform Lambda: authored (runtime, handler, uses WriteGetObjectResponse)
  [✓|✗] Reserved concurrency: set (<n>) to expected peak GET rate
  [✓|✗] Object Lambda AP: created, SupportingAccessPoint=<STANDARD_AP_NAME> ARN
  [✓|✗] TransformationConfiguration: operations=[GetObject, HeadObject, ...]
  [✓|✗] Optional: multi-region | GetObjectACL | range downloads | none
VERIFICATION_COMMANDS:
  <copy-pasteable verification commands>
```

## Primary example extended: CSV-to-JSON Lambda source and CloudFront integration

CSV-to-JSON transform Lambda (uses WriteGetObjectResponse, NOT return):

```python
import boto3, urllib.request, csv, io, json

s3 = boto3.client("s3")

def handler(event, context):
    # Fetch original CSV via the presigned URL from Object Lambda event
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        csv_body = resp.read().decode("utf-8")

    # Transform: CSV rows -> JSON array (one object per row)
    reader = csv.DictReader(io.StringIO(csv_body))
    json_output = json.dumps(list(reader), indent=2)

    # Write back via WriteGetObjectResponse (return is a silent no-op)
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=json_output,
        ContentType="application/json"
    )
```

CloudFront integration (cache transform output at edge to reduce
Lambda invocations):

```bash
aws cloudfront create-distribution \
  --origin-domain-name csv-json-olap-444455556666.s3-object-lambda.us-east-1.amazonaws.com \
  --default-cache-behavior 'TargetOriginId=csv-json-olap-origin,ViewerProtocolPolicy=redirect-to-https,DefaultTTL=3600,MinTTL=0,MaxTTL=86400'
```

## Perfect example output - PREREQUISITES_MISSING

```text
OBJECT_LAMBDA_SPEC: pii-redact-olap
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Bucket baseline: prod-data-lake, BPA all 4 True, SSE-KMS
  [✓] Supporting standard AP: dlake-team-a-ap with Lambda-read policy
  [✗] IAM execution role: trust policy only has lambda.amazonaws.com — add s3-object-lambda.amazonaws.com principal
  [✗] Transform Lambda: not yet authored — create function with WriteGetObjectResponse call
  [✗] Reserved concurrency: not set — Lambda will throttle under load and clients will see S3 AccessDenied
  [OPTIONAL] Object Lambda AP: pending (waiting on role + Lambda + TransformationConfiguration)
  [OPTIONAL] Multi-region / GetObjectACL / range downloads: none
VERIFICATION_COMMANDS:
  aws iam get-role --role-name olap-exec
  aws lambda list-functions --query 'Functions[?FunctionName==`pii-redact-fn`]`
```

