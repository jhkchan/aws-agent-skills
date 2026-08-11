# Baseline (no-skill) response: missing-reserved-concurrency-missing

This file captures what a generic assistant produces WITHOUT the
s3-object-lambda-deployer skill loaded. The contrast proves the skill
catches the missing-reserved-concurrency prerequisite (Lambda throttle
surface as S3 AccessDenied) — the baseline provisions without flagging.

---

Here's the Object Lambda AP for your enrichment workload:

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id 111111111111 --name enrichment-olap \
  --configuration SupportingAccessPoint=arn:aws:s3:us-east-1:111111111111:accesspoint/dlake-team-b-ap

aws s3control put-access-point-configuration-for-object-lambda \
  --account-id 111111111111 --name enrichment-olap \
  --configuration '{"TransformationConfigurations":[{"Actions":["GetObject"],"ContentTransformation":{"AwsLambda":{"FunctionArn":"arn:aws:lambda:us-east-1:111111111111:function:enrich-fn"}}}]}'
```

Lambda will scale automatically with the account concurrency pool, so
no reserved concurrency is needed.
