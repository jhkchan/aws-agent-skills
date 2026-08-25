# Diagnostic Commands — S3 Object Lambda Deployer

Verification and diagnostic command listings moved from SKILL.md. Load on demand.

## Step 9: post-deploy verification commands

```bash
aws s3control get-access-point --account-id <ACCOUNT_ID> --name <STANDARD_AP_NAME>
aws s3control get-access-point-policy --account-id <ACCOUNT_ID> --name <STANDARD_AP_NAME>
aws s3control get-access-point-for-object-lambda --account-id <ACCOUNT_ID> --name <OLAP_NAME>
aws s3control get-access-point-configuration-for-object-lambda --account-id <ACCOUNT_ID> --name <OLAP_NAME>
aws lambda get-function --function-name <FUNC_NAME>
aws lambda get-function-concurrency --function-name <FUNC_NAME>
# Invoke a real GET against the OLAP hostname and verify the transform fires
aws s3api get-object --bucket arn:aws:s3-object-lambda:<REGION>:<ACCOUNT>:accesspoint/<OLAP_NAME> --key sample.txt output.txt
aws cloudwatch get-metric-statistics --namespace AWS/Lambda --metric-name Invocations \
  --dimensions Name=FunctionName,Value=<FUNC_NAME> \
  --start-time $(date -u -v1H +%Y-%m-%dT%H:%M:%SZ) --end-time $(date -u +%Y-%m-%dT%H:%M:%SZ) \
  --period 300 --statistics Sum
```

