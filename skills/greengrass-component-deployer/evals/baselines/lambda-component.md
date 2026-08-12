# Baseline (no-skill) — lambda-component

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the aws.lambda HARD
> dependency requirement (without it the Lambda runtime is not
> available on the device), the component-from-function-ARN creation
> path, and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create a component from the Lambda:

```bash
aws greengrassv2 create-component-version \
  --lambda-function '{"lambdaArn": "arn:aws:lambda:us-east-1:123456789012:function:edge-data-processor:5"}'
```

Then deploy it:

```bash
aws greengrassv2 create-deployment \
  --target-arn "arn:aws:iot:us-east-1:123456789012:thinggroup/DataProcessors" \
  --components '{"com.example.EdgeDataProcessor": {"componentVersion": "1.0.0"}}'
```
