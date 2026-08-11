# Baseline (no-skill) response: deploy-macos-baseline-missing-instance-role

This file captures what a generic assistant produces WITHOUT the
ssm-patch-baseline-deployer skill loaded.

---

To create your macOS patch baseline, run:

```bash
aws ssm create-patch-baseline \
  --name macos-prod-baseline \
  --operating-system MACOS \
  --approval-rules '{"PatchRules":[{"PatchFilterGroup":{"PatchFilters":[{"Key":"PRODUCT","Values":["macOS"]},{"Key":"CLASSIFICATION","Values":["Security"]}]},"ApproveAfterDays":3}]}'

aws ssm register-patch-baseline-for-patch-group \
  --baseline-id <id> \
  --patch-group macos-prod-fleet
```

Your macOS instances will now be patched via SSM.
