# Baseline (no-skill) response: deploy-outbound-forwarding-rule-ready

This file captures what a generic assistant produces WITHOUT the
route53-resolver-deployer skill loaded.

---

To create your outbound endpoint and forwarding rule, run:

```bash
aws route53resolver create-resolver-endpoint \
  --name prod-outbound \
  --security-group-ids sg-0def456 \
  --direction OUTBOUND \
  --ip-addresses '[{"SubnetId":"subnet-aaa"},{"SubnetId":"subnet-bbb"}]'

aws route53resolver create-resolver-rule \
  --name forward-corp-local \
  --rule-type FORWARD \
  --domain-name corp.example.local \
  --target-ips '[{"Ip":"10.99.1.5","Port":53},{"Ip":"10.99.2.5","Port":53}]'
```

Then associate the rule with your VPC.
