# Baseline (no-skill) response: recover-pending-stuck-awspending-completed

This file captures what a generic assistant produces WITHOUT the
secrets-rotation-operator skill loaded.

---

To recover the stuck AWSPENDING version on `prod/api-gateway-token`, you
can promote the pending version to AWSCURRENT. Since you've confirmed the
AWSPENDING credential is the live one, use:

```bash
aws secretsmanager update-secret-version-stage \
  --secret-id prod/api-gateway-token \
  --version-stage AWSCURRENT \
  --move-to-version-id a1b2c3d4 \
  --remove-from-version-id i9j0k1l2
```

Then verify the version stages with `list-secret-version-ids`.
