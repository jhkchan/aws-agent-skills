# Baseline (no-skill) — custom-domain-third-party-dns

> This is the response a model produces **without** the skill definition.
> It misses the manual DNS CNAME validation step required for third-party
> DNS (GoDaddy), assumes Route 53 auto-validation applies, and does not
> flag that the cert is PENDING_VALIDATION. Generated for
> with-skill-vs-baseline comparison.

---

Add the custom domain in the console:

```bash
aws amplify create-domain-association --app-id dXXXX \
  --domain-name example.com \
  --sub-domain-settings '[{"prefix":"portal","branchName":"main"}]'
```

Amplify will validate it automatically.
