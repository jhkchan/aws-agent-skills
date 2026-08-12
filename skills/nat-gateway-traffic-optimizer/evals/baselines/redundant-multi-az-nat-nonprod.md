# Baseline (no-skill) response: redundant-multi-az-nat-nonprod

This file captures what a generic assistant produces WITHOUT the
nat-gateway-traffic-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, cross-AZ cost modelling,
EIP release step, CONFIRM gate, route table backup).

---

Your staging VPC has 3 NAT Gateways but only processes 200 GB per
month. Since this is staging and doesn't need high availability, you
could consolidate to a single NAT Gateway to save on the hourly
charges.

Each NAT Gateway costs about $33/month just in hourly charges, so
removing 2 of them would save around $66/month. You'd have some cross-
AZ data transfer costs but those would be minimal at 200 GB.

To consolidate:

```
aws ec2 replace-route --route-table-id rtb-0bbb --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-0keep
aws ec2 replace-route --route-table-id rtb-0ccc --destination-cidr-block 0.0.0.0/0 --nat-gateway-id nat-0keep
aws ec2 delete-nat-gateway --nat-gateway-id nat-0removeB
aws ec2 delete-nat-gateway --nat-gateway-id nat-0removeC
```

Make sure to test connectivity from all AZs after making the change.
