# Baseline (no-skill) response: distribution-with-static-origin-ready

This file captures what a generic assistant produces WITHOUT the
lightsail-instance-deployer skill loaded — the contrast that proves
the skill adds structure (Lightsail distribution origin validation,
ACM cert region check, cache behavior policy, deterministic VERDICT
block with pre-checks for origin reachability).

---

Here's a plan to set up a Lightsail distribution in front of your
static-site instance.

The distribution will:

- Front your prod-static-site instance
- Serve over HTTPS with your ACM cert
- Cache static assets at the edge

Steps:

1. Create the distribution with the instance as origin.
2. Attach the ACM certificate.
3. Configure the default cache behavior.

Commands:

```
aws lightsail create-distribution --distribution-name prod-cdn \
  --origin ... --default-cache-behavior ...
```

This should speed up your static site. Let me know if you need help.
