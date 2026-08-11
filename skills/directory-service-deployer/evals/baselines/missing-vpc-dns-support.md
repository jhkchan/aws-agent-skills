# Baseline (no-skill) — missing-vpc-dns-support

> This is the response a model produces **without** the skill
> definition. It attempts to create the directory without flagging
> the missing enableDnsSupport prerequisite on the VPC, which would
> cause directory creation to fail. Does not emit a
> PREREQUISITES_MISSING verdict. Generated for with-skill-vs-
> baseline comparison.

---

Sure, here is the directory creation command:

```bash
aws ds create-microsoft-ad \
  --name corp.example.com \
  --short-name corp \
  --password 'Adm1nP@ss!' \
  --edition Standard \
  --vpc-settings VpcId=vpc-nodns,SubnetIds=subnet-ggg777,subnet-hhh888
```

Then configure trust and LDAPS.
