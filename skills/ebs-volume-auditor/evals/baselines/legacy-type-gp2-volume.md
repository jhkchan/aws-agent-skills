# Baseline (no-skill) response: legacy-type-gp2-volume

This file captures what a generic assistant produces WITHOUT the
ebs-volume-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, online-modify reasoning,
gp3-baseline cost-delta framing).

---

This EBS volume is using the `gp2` volume type, which is an older
generation. It is encrypted and attached to an instance.

You can upgrade to `gp3` which is newer and generally cheaper:

```
aws ec2 modify-volume --volume-id vol-0eee555legacy-gp2-volume --volume-type gp3
```

The upgrade happens online with no downtime.
