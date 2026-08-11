# Baseline (no-skill) response: deploy-inbound-endpoint-ready

This file captures what a generic assistant produces WITHOUT the
route53-resolver-deployer skill loaded.

---

To create your Route 53 Resolver inbound endpoint, run:

```bash
aws route53resolver create-resolver-endpoint \
  --name prod-inbound \
  --security-group-ids sg-0abc123 \
  --direction INBOUND \
  --ip-addresses '[{"SubnetId":"subnet-aaa","Ip":"10.0.1.10"},{"SubnetId":"subnet-bbb","Ip":"10.0.2.10"}]'
```

You can verify it was created with get-resolver-endpoint.
