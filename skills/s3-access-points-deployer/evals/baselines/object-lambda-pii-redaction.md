# Baseline (no-skill) — object-lambda-pii-redaction

> This is the response a model produces **without** the skill definition.
> It creates the Object Lambda access point but omits the supporting
> standard AP requirement, the Lambda invocation policy grant, and the
> reserved-concurrency setting that prevents client-visible throttling.
> Generated for with-skill-vs-baseline comparison.

---

To set up an Object Lambda access point:

```bash
aws s3control create-access-point-for-object-lambda \
  --account-id 123456789012 \
  --name pii-redacted-olap \
  --configuration SupportingAccessPoint=arn:aws:s3:us-east-1:123456789012:accesspoint/raw-customer-ap,TransformationConfigurations='[{Action=GetObject,ContentTransformation=AWSLambda:{FunctionArn=arn:aws:lambda:us-east-1:123456789012:function:pii-redact-fn}}]'
```

That should redact PII on GET.
