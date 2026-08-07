# Baseline (no-skill) response: install-blocked-no-patch-group

This file captures what a generic assistant produces WITHOUT the
ssm-patch-operator skill loaded.

---

To install patches on your Amazon Linux 2 instance:

```bash
aws ssm send-command \
  --instance-ids i-0fedcba9876543210 \
  --document-name "AWS-RunPatchBaseline" \
  --parameters '{"Operation":["Install"]}'
```

The instance will use the default Amazon Linux 2 patch baseline. You can
monitor the result with `aws ssm get-command-invocation`.
