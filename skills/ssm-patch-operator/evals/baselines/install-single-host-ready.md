# Baseline (no-skill) response: install-single-host-ready

This file captures what a generic assistant produces WITHOUT the
ssm-patch-operator skill loaded.

---

You can install patches on your Amazon Linux 2 instance with:

```bash
aws ssm send-command \
  --instance-ids i-0abc123def456789a \
  --document-name "AWS-RunPatchBaseline" \
  --parameters '{"Operation":["Install"]}'
```

Wait for the command to complete and check the output. Reboot the instance
afterwards if you want the patches to take effect.
