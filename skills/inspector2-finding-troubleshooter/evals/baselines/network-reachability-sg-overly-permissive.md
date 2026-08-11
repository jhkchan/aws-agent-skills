# Baseline (no-skill) — network-reachability-sg-overly-permissive

> This is the response a model produces **without** the skill definition.
> It mentions the SG but conflates the finding with a package CVE, misses
> the explicit revoke-and-scope SG remediation, and does not emit the
> ROOT_CAUSE_FOUND / FINDING_TYPE:NETWORK_REACHABILITY /
> LAYER:SG_OVERLY_PERMISSIVE diagnostic block. Generated for
> with-skill-vs-baseline comparison.

---

Your instance has port 3306 open to the internet. You should fix
the security group. Also make sure you patch the OS:

```bash
aws ssm send-command --instance-ids i-db99 \
  --document-name AWS-RunPatchBaseline
```

Update the security group to be more restrictive.
