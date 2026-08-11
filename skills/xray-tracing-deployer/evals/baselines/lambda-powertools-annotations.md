# Baseline (no-skill) — lambda-powertools-annotations

> This is the response a model produces **without** the skill definition.
> It produces a basic Powertools setup but misses the custom sampling
> rule, the boto3 auto-patching note, the annotation vs metadata
> distinction, the execution role permission check, and the structured
> checklist.

---

To enable X-Ray on your Lambda function with Powertools:

```bash
pip install aws-lambda-powertools
```

```python
from aws_lambda_powertools import Tracer

tracer = Tracer(service="checkout-handler-prod")

@tracer.capture_lambda_handler
def handler(event, context):
    # your code here
    pass
```

Enable tracing on the Lambda configuration:

```bash
aws lambda update-function-configuration \
  --function-name checkout-handler-prod \
  --tracing-config Mode=Active
```

You can add annotations with `tracer.put_annotation()`.
