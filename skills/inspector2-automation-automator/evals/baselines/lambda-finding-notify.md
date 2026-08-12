# Baseline (no-skill) response: lambda-finding-notify

This file captures what a generic assistant produces WITHOUT the
inspector2-automation-automator skill loaded.

---

For the Lambda finding, update the lodash dependency in your
build pipeline and redeploy the function. Inspector scanned the
code at deploy time so a redeploy with the fixed version will
resolve the finding.

```
aws lambda update-function-code --function-name order-processor-prod ...
```

Send a notification to the app team so they know to update the
package.json.
