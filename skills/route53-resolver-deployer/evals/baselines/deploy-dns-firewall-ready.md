# Baseline (no-skill) response: deploy-dns-firewall-ready

This file captures what a generic assistant produces WITHOUT the
route53-resolver-deployer skill loaded.

---

To set up DNS Firewall with the managed malware list, run:

```bash
aws route53resolver create-firewall-rule-group --name prod-firewall-rules

aws route53resolver create-firewall-rule \
  --firewall-rule-group-id <id> \
  --firewall-domain-list-id rslvr-fdl-aws-managed-domains-malware \
  --priority 1 \
  --action BLOCK

aws route53resolver create-firewall-rule-group-association \
  --firewall-rule-group-id <id> \
  --vpc-id vpc-0abc123 \
  --priority 1
```

This will block malware domains in your VPC.
