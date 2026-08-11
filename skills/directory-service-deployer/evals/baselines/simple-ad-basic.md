# Baseline (no-skill) — simple-ad-basic

> This is the response a model produces **without** the skill
> definition. It creates the Simple AD but misses the Simple AD
> limitations (no trusts, no LDAPS, no schema extensions), the size
> immutability after creation, and the READY_TO_DEPLOY checklist
> format. Generated for with-skill-vs-baseline comparison.

---

Create the Simple AD:

```bash
aws ds create-directory \
  --name internal.example.com \
  --short-name internal \
  --password 'Adm1nP@ss!' \
  --size Large \
  --vpc-settings VpcId=vpc-eee55566,SubnetIds=subnet-eee555,subnet-fff666
```

Then connect SSO.
