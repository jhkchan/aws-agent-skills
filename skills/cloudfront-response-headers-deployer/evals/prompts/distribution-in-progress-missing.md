# Eval prompt: distribution-in-progress-missing

Attach a managed policy to a distribution and emit the standard VERDICT
block.

Operation: attach
Policy: managed SecurityHeadersPolicy
Distribution: E27TVSIEXAMPLE

```json
{
  "RequirementChecks": {
    "cloudfront.get-distribution.E27TVSIEXAMPLE": {
      "Status": "InProgress"
    }
  }
}
```
