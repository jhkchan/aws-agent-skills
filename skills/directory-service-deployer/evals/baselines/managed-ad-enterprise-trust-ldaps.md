# Baseline (no-skill) — managed-ad-enterprise-trust-ldaps

> This is the response a model produces **without** the skill
> definition. It creates the directory and lists CLI commands but
> misses the trust direction semantics (one-way vs two-way from
> whose perspective), the conditional forwarder requirement on BOTH
> sides, the LDAPS certificate authority lifecycle (expiry
> monitoring), and the READY_TO_DEPLOY checklist format. Generated
> for with-skill-vs-baseline comparison.

---

Create the Managed AD directory:

```bash
aws ds create-microsoft-ad \
  --name corp.example.com \
  --short-name corp \
  --password 'Adm1nP@ss!' \
  --edition Enterprise \
  --vpc-settings VpcId=vpc-aaa11122,SubnetIds=subnet-aaa111,subnet-bbb222
```

Then create a trust and enable LDAPS.
