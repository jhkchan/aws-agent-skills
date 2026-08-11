# Baseline (no-skill) — network-firewall-policy-remediation

> This is the response a model produces **without** the skill
> definition. It creates a Network Firewall policy but misses the subnet
> mapping requirement (without subnets no firewall is created), the
> remediation grace period, and the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Create the Network Firewall policy:

```bash
aws fms put-policy \
  --policy-name org-nfw-inspection \
  --security-service-policy-data Type=NETWORK_FIREWALL \
  --include-map ORG_UNIT=ou-workloads-abcdef
```

Add the rule groups and you should be good.
