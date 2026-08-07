# Baseline (no-skill) response: install-blocked-disk-full

This file captures what a generic assistant produces WITHOUT the
ssm-patch-operator skill loaded.

---

To install patches on your RHEL 9 instance:

```bash
aws ssm send-command \
  --instance-ids i-0full00000012345 \
  --document-name "AWS-RunPatchBaseline" \
  --parameters '{"Operation":["Install"]}'
```

If the command fails, check the output for details. You may need to
free up disk space on the instance first.
