# Baseline (no-skill) — ad-connector-onprem-dns

> This is the response a model produces **without** the skill
> definition. It creates the AD Connector but misses the VPN/DX
> connectivity prerequisite verification, the AD Connector limitations
> (no trusts, no LDAPS, dependent on on-prem availability), and the
> READY_TO_DEPLOY checklist format. Generated for with-skill-vs-
> baseline comparison.

---

Create the AD Connector:

```bash
aws ds connect-directory \
  --name corp.example.com \
  --short-name corp \
  --password 'Adm1nP@ss!' \
  --dns-ip-addrs 10.0.1.53 10.0.2.53 \
  --vpc-settings VpcId=vpc-ccc33344,SubnetIds=subnet-ccc333,subnet-ddd444
```

Then set up SSO.
