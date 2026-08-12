# Eval prompt: tgw-vpc-default-route-blackhole

Diagnose the Transit Gateway routing failure for the following topology.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: VPC-A's EC2 i-aaa (10.10.0.0/16) cannot ping VPC-B's EC2
i-bbb (10.20.0.0/16) through TGW. The forward path works (i-bbb sees
the ICMP echo request in tcpdump), but the reply never returns to
i-aaa.

```text
TGW: tgw-aaa
Attachment A: tgw-attach-vpc-a (VPC vpc-a, 10.10.0.0/16)
Attachment B: tgw-attach-vpc-b (VPC vpc-b, 10.20.0.0/16)

VPC-A route table:
  - 10.20.0.0/16 → tgw-aaa (forward path)
  - 0.0.0.0/0 → igw-aaa (internet)

VPC-B route table:
  - 10.20.0.0/16 → local
  - 0.0.0.0/0 → igw-bbb (internet; NO route for 10.10.0.0/16)

TGW route table tgw-rtb-default:
  - 10.10.0.0/16 → tgw-attach-vpc-a (propagated, active)
  - 10.20.0.0/16 → tgw-attach-vpc-b (propagated, active)
Both attachments associated with tgw-rtb-default.

i-bbb tcpdump shows incoming ICMP echo request from i-aaa, and
outgoing echo reply routed to the IGW (not the TGW).
```

Routing is bidirectional: a successful ping requires BOTH the forward
path (source → TGW → destination) AND the return path (destination →
TGW → source). Verify the return-path route table in VPC-B and
recommend the fix.
