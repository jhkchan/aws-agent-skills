# Baseline (no-skill) response: deploy-al2023-wrong-product-filter-blocked

This file captures what a generic assistant produces WITHOUT the
ssm-patch-baseline-deployer skill loaded.

---

To create your Amazon Linux 2023 patch baseline, run:

```bash
aws ssm create-patch-baseline \
  --name al2023-prod-security \
  --operating-system AMAZON_LINUX_2023 \
  --approval-rules '{"PatchRules":[{"PatchFilterGroup":{"PatchFilters":[{"Key":"PRODUCT","Values":["Amazon Linux 2"]},{"Key":"CLASSIFICATION","Values":["Security"]}]},"ApproveAfterDays":7}]}'

aws ssm register-patch-baseline-for-patch-group \
  --baseline-id <id> \
  --patch-group al2023-prod-web
```

This will set up patching for your AL2023 instances.
