# Baseline (no-skill) response: scan-association-missing-patches

This file captures what a generic assistant produces WITHOUT the
ssm-patch-operator skill loaded.

---

Your association is working correctly (Status: Success). If you're still
NON_COMPLIANT, you probably need to install the missing patches manually:

```bash
aws ssm send-command \
  --instance-ids i-0a1b2c3d4e5f67890 \
  --document-name "AWS-RunPatchBaseline" \
  --parameters '{"Operation":["Install"]}'
```

Or delete the current association and recreate it with Install.
