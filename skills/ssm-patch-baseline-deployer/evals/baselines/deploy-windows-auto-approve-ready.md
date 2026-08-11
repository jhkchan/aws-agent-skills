# Baseline (no-skill) response: deploy-windows-auto-approve-ready

This file captures what a generic assistant produces WITHOUT the
ssm-patch-baseline-deployer skill loaded.

---

To create your Windows patch baseline, run:

```bash
aws ssm create-patch-baseline \
  --name win-prod-critical \
  --operating-system WINDOWS_SERVER \
  --approval-rules '{"PatchRules":[{"PatchFilterGroup":{"PatchFilters":[{"Key":"PRODUCT","Values":["WindowsServer2022"]},{"Key":"CLASSIFICATION","Values":["Security Updates"]}]},"ApproveAfterDays":0}]}' \
  --rejected-patches '["KB5012345"]'
```

This will approve Windows Server 2022 security updates immediately.
