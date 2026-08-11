# Baseline (no-skill) — missing-parameter-binding

> This is the response a model produces **without** the skill
> definition. It creates the document without catching that the step
> references {{ UndefinedParam }} which is not declared in the
> parameters section. The automation will fail at execution time
> when it cannot resolve the parameter. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-baseline
> comparison.

---

Here's the document:

```json
{
  "schemaVersion": "0.3",
  "mainSteps": [
    {
      "name": "Describe",
      "action": "aws:executeAwsApi",
      "inputs": {
        "Service": "ec2",
        "Api": "DescribeInstances",
        "InstanceIds": ["{{ UndefinedParam }}"]
      }
    }
  ]
}
```

Create it and run it.
