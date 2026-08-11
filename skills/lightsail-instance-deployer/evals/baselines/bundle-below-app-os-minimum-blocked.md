# Baseline (no-skill) response: bundle-below-app-os-minimum-blocked

This file captures what a generic assistant produces WITHOUT the
lightsail-instance-deployer skill loaded — the contrast that proves
the skill catches the bundle-below-vendor-minimum blocker that the
baseline misses (nano_3_0 will install WordPress but MySQL OOMs
under load).

---

Here's a plan to set up WordPress on Lightsail with your selected
bundle.

The instance will:

- Run WordPress on a nano bundle
- Have a static IP
- DNS pointing to it
- Daily snapshots

Steps:

1. Create the instance with the WordPress blueprint on nano_3_0.
2. Attach the static IP.
3. Configure DNS.
4. Enable automatic snapshots.

Commands:

```
aws lightsail create-instances --instance-names prod-wp \
  --blueprint-id wordpress --bundle-id nano_3_0 ...
aws lightsail attach-static-ip ...
```

This keeps your monthly cost around $3.50. Let me know if you need
help with any of the steps.
