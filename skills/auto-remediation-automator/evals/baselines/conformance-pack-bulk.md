# Baseline (no-skill) response: conformance-pack-bulk

This file captures what a generic assistant produces WITHOUT the
auto-remediation-automator skill loaded.

---

For a bulk S3 security baseline, you can deploy a conformance pack.
The pack YAML would include ConfigRule resources for each rule and
RemediationConfiguration resources pointing to the SSM runbooks.

You can deploy it with:

```
aws configservice put-conformance-pack --conformance-pack-name s3-baseline --template-body file://pack.yaml
```

Each remediation references the SSM document name and the parameters.
Make sure the SSM service role exists.
