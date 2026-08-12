# Baseline (no-skill) — lambda-sync-realtime

> This is the response a model produces **without** the skill
> definition. It picks StartDocumentAnalysis (async) instead of the
> synchronous AnalyzeDocument for a real-time single-page Lambda
> workload, misses the sync-vs-async distinction, and omits the IAM
> policy grants Textract needs. Generated for with-skill-vs-baseline
> comparison.

---

Create a Lambda that calls StartDocumentAnalysis on the S3 PUT event:

```python
import boto3
textract = boto3.client("textract")
def lambda_handler(event, context):
    bucket = event["Records"][0]["s3"]["bucket"]["name"]
    key = event["Records"][0]["s3"]["object"]["key"]
    response = textract.start_document_analysis(
        DocumentLocation={"S3Object": {"Bucket": bucket, "Name": key}},
        FeatureTypes=["FORMS", "TABLES"]
    )
    return {"job_id": response["JobId"]}
```

You will need to poll GetDocumentAnalysis from a downstream service.
