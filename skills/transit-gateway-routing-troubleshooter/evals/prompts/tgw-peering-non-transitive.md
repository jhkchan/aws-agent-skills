# Eval prompt: tgw-peering-non-transitive

Diagnose the Transit Gateway peering routing failure for the following
topology. Walk the symptom-driven diagnostic tree and emit the standard
diagnostic block (TARGET, VERDICT, REASON, LAYER, EVIDENCE,
REMEDIATION).

Symptom: EC2 in vpc-a (us-east-1, attached to tgw-a) cannot reach EC2
in vpc-c (us-west-2, attached to tgw-c). Ping times out. tgw-a has a
peering to tgw-b; tgw-b has a peering to tgw-c. Operators expect tgw-b
to forward traffic between tgw-a and tgw-c as an intermediate hop.

```text
TGW topology:
  - tgw-a (us-east-1): peering to tgw-b (available)
  - tgw-b (us-east-1): peering to tgw-a (available), peering to tgw-c (available)
  - tgw-c (us-west-2): peering to tgw-b (available)

Attachments:
  - tgw-a: vpc-a (10.10.0.0/16), peering-to-tgw-b
  - tgw-b: vpc-b (10.20.0.0/16), peering-to-tgw-a, peering-to-tgw-c
  - tgw-c: vpc-c (10.30.0.0/16), peering-to-tgw-b

tgw-a route table search for 10.30.0.0/16: no route
tgw-c route table search for 10.10.0.0/16: no route

VPC-A route table: 10.30.0.0/16 → tgw-a (forward path OK)
VPC-C route table: 10.10.0.0/16 → tgw-c (return path OK)
```

Transit Gateway peering attachments are non-transitive: tgw-b does NOT
forward traffic between its two peering attachments. Verify the
transitivity assumption and recommend the fix.
