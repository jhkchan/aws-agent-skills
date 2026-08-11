# Baseline (no-skill) response: deploy-outbound-endpoint-single-az-blocked

This file captures what a generic assistant produces WITHOUT the
route53-resolver-deployer skill loaded.

---

To create your outbound endpoint, run:

```bash
aws route53resolver create-resolver-endpoint \
  --name prod-outbound \
  --security-group-ids sg-0def456 \
  --direction OUTBOUND \
  --ip-addresses '[{"SubnetId":"subnet-aaa"},{"SubnetId":"subnet-ccc"}]'
```

This will create the endpoint with two IP addresses.
