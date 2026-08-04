# Eval prompt: missing-resource-limits

Audit the following ECS task definition for security exposure. Emit the
standard VERDICT block (TASK, VERDICT, REASON, FINDINGS, REMEDIATION).

Task definition family: missing-resource-limits
networkMode: awsvpc

containerDefinitions:

```json
[
  {
    "name": "batch-job",
    "image": "111111111111.dkr.ecr.us-east-1.amazonaws.com/batch-job:latest",
    "user": "1000",
    "essential": true,
    "environment": [
      {"name": "BATCH_SIZE", "value": "100"},
      {"name": "OUTPUT_BUCKET", "value": "my-batch-results"}
    ]
  }
]
```
