# Baseline (no-skill) — remediation-execute-api-lambda

> This is the response a model produces **without** the skill
> definition. It creates the document JSON but misses the execution
> role trust policy requirement for ssm.amazonaws.com, conflates the
> execution role with the instance role, omits rate control
> validation, and does not emit the READY_TO_DEPLOY checklist.
> Generated for with-skill-vs-baseline comparison.

---

Here's the SSM document JSON:

```json
{
  "schemaVersion": "0.3",
  "description": "Remediate EC2 instances",
  "mainSteps": [
    {
      "name": "Describe",
      "action": "aws:executeAwsApi",
      "inputs": {"Service": "ec2", "Api": "DescribeInstances"}
    },
    {
      "name": "InvokeLambda",
      "action": "aws:invokeLambdaFunction",
      "inputs": {"FunctionName": "remediation-handler"}
    }
  ]
}
```

Create it with `aws ssm create-document` and you should be good.
