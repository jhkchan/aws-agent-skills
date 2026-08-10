# Baseline (no-skill) response: deploy-conformance-pack-ready

This file captures what a generic assistant produces WITHOUT the
config-rule-deployer skill loaded.

---

To deploy a conformance pack for the CIS benchmark, use:

```bash
aws configservice put-conformance-pack \
  --conformance-pack-name "cis-aws-foundations-benchmark" \
  --template-body file://conformance-pack.yaml
```

You can find CIS conformance pack templates in the AWS Config documentation.
