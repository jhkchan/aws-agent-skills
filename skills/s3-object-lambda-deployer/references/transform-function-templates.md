# Transform Function Templates Reference

Supplementary reference for the S3 Object Lambda Deployer skill. Use
when authoring the transform Lambda for PII redaction, data enrichment,
format conversion, and multi-operation transforms.

## Common event structure

The Object Lambda service delivers this event to the transform function:

```json
{
  "xAmzRequestId": "abc-123",
  "getObjectContext": {
    "inputS3Url": "https://...",
    "outputRoute": "...",
    "outputToken": "..."
  },
  "configuration": {
    "accessPointArn": "arn:aws:s3-object-lambda:...",
    "supportingAccessPointArn": "arn:aws:s3:...",
    "payload": "{}"
  },
  "userRequest": {
    "url": "/sample.txt",
    "headers": {"Range": "bytes=0-1023", "x-amz-acl": "..."}
  },
  "userIdentity": {"accountId": "111111111111", "...": "..."},
  "protocolVersion": "1.00"
}
```

**Key fields:**
- `inputS3Url` — presigned GetObject URL for the original object
- `outputRoute` / `outputToken` — required by `WriteGetObjectResponse`
- `userRequest.headers` — includes `Range` for range downloads

## PII redaction transform (Python)

```python
import boto3, urllib.request, re, json

s3 = boto3.client("s3")

def handler(event, context):
    # Fetch the original object via presigned URL
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        body = resp.read().decode("utf-8")

    # Transform: redact SSN, email, phone
    body = re.sub(r"\d{3}-\d{2}-\d{4}", "***-**-****", body)
    body = re.sub(r"[\w.-]+@[\w.-]+\.\w+", "[REDACTED]", body)
    body = re.sub(r"\+1-\d{3}-\d{3}-\d{4}", "+1-***-***-****", body)

    # Write back via WriteGetObjectResponse (NOT return)
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=body
    )
```

## Data enrichment transform

Append metadata from DynamoDB or another source to each GetObject
response. Useful for adding watermark or audit metadata.

```python
import boto3, urllib.request, json

s3 = boto3.client("s3")
ddb = boto3.client("dynamodb")

def handler(event, context):
    object_key = event["userRequest"]["url"].lstrip("/")

    # Fetch original
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        body = json.loads(resp.read().decode("utf-8"))

    # Enrich: attach classification from DDB
    meta = ddb.get_item(
        TableName="object-metadata",
        Key={"objectKey": {"S": object_key}}
    ).get("Item", {})
    body["_classification"] = meta.get("classification", {"S": "unknown"}).get("S")

    # Write back
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=json.dumps(body)
    )
```

## Format conversion: CSV to JSON

Convert a CSV file on-the-fly to a JSON array.

```python
import boto3, urllib.request, csv, json, io

s3 = boto3.client("s3")

def handler(event, context):
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        csv_text = resp.read().decode("utf-8")

    reader = csv.DictReader(io.StringIO(csv_text))
    rows = list(reader)

    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=json.dumps(rows)
    )
```

## HeadObject transform

HeadObject returns only metadata (no body). The transform Lambda must
still call `WriteGetObjectResponse` but with `Body=""` and modified
metadata headers.

```python
import boto3

s3 = boto3.client("s3")

def handler(event, context):
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body="",
        Metadata={"x-redacted-by": "object-lambda"},
        ContentType="application/json"
    )
```

**Common mistake:** omitting `Body=""`. The WriteGetObjectResponse
call requires either `Body` or an explicit status code signaling no
content.

## Range download transform

Handle `Range` headers by fetching only the requested byte range and
writing it back with `ContentRange`.

```python
import boto3, urllib.request

s3 = boto3.client("s3")

def handler(event, context):
    range_header = event["userRequest"]["headers"].get("Range", "")
    presigned_url = event["getObjectContext"]["inputS3Url"]

    # Pass the Range header through to the original GET
    req = urllib.request.Request(presigned_url)
    if range_header:
        req.add_header("Range", range_header)

    with urllib.request.urlopen(req) as resp:
        body = resp.read()
        content_range = resp.headers.get("Content-Range", "")

    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=body,
        ContentRange=content_range
    )
```

## Multi-operation transformation configuration

A single OLAP can transform multiple operations. Each operation can
route to a different Lambda function:

```json
{
  "SupportingAccessPoint": "arn:aws:s3:us-east-1:111111111111:accesspoint/dlake-ap",
  "TransformationConfigurations": [
    {
      "Actions": ["GetObject"],
      "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:us-east-1:111111111111:function:pii-redact"}}
    },
    {
      "Actions": ["HeadObject"],
      "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:us-east-1:111111111111:function:head-metadata"}}
    },
    {
      "Actions": ["ListObjects"],
      "ContentTransformation": {"AwsLambda": {"FunctionArn": "arn:aws:lambda:us-east-1:111111111111:function:list-filter"}}
    }
  ]
}
```

**Verify the actions list** before applying — operations not listed
bypass the transform silently.

## Step 4 transform: PII redaction handler (moved from SKILL.md)

```python
# transform.py — PII redaction example
import boto3, urllib.request, re

s3 = boto3.client("s3")

def handler(event, context):
    # Fetch the original object via the presigned URL
    presigned_url = event["getObjectContext"]["inputS3Url"]
    with urllib.request.urlopen(presigned_url) as resp:
        body = resp.read().decode("utf-8")

    # Transform: redact SSN pattern
    transformed = re.sub(r"\d{3}-\d{2}-\d{4}", "***-**-****", body)

    # Write back via WriteGetObjectResponse (NOT return)
    s3.write_get_object_response(
        RequestRoute=event["getObjectContext"]["outputRoute"],
        RequestToken=event["getObjectContext"]["outputToken"],
        Body=transformed
    )
```

