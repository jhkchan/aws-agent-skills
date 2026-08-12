# Baseline (no-skill) response: missing-s3-gateway-endpoint

This file captures what a generic assistant produces WITHOUT the
nat-gateway-traffic-optimizer skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, Gateway Endpoint FREE
citation, dollar savings math, CONFIRM gate, route table verification).

---

Your VPC has two NAT Gateways processing 800 GB per month, with 300 GB
of that being S3 traffic. You're paying about $102/month for NAT.

Since a lot of your traffic is going to S3, you should create an S3
VPC Gateway Endpoint. This will route S3 traffic directly without going
through the NAT Gateway, saving you the data processing charges for
that traffic.

You can create the endpoint with:

```
aws ec2 create-vpc-endpoint --vpc-id vpc-missing-s3-gateway-endpoint \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids rtb-0aaa rtb-0bbb \
  --vpc-endpoint-type Gateway
```

This should save you about $13/month from the S3 traffic not going
through NAT. The endpoint itself is free, so it's a no-brainer.
