# Eval prompt: tgw-static-route-overrides-propagated

Diagnose the Transit Gateway routing failure for the following topology.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: EC2 instance i-aaa in VPC vpc-a (10.10.0.0/16) cannot ping EC2
instance i-bbb in VPC vpc-b (10.20.0.0/16) through transit gateway
tgw-aaa. The ping returns "request timeout". i-bbb never sees the packet
in its VPC flow logs. Both VPCs are attached to the TGW.

```text
TGW: tgw-aaa
Route table: tgw-rtb-default (associated with vpc-a's attachment)
Attachment A: tgw-attach-vpc-a (VPC vpc-a, 10.10.0.0/16)
Attachment B: tgw-attach-vpc-b (VPC vpc-b, 10.20.0.0/16)
Attachment C: tgw-attach-vpc-c (VPC vpc-c, 10.30.0.0/16, legacy)

VPC-A route table: 10.20.0.0/16 → tgw-aaa
VPC-B route table: 10.10.0.0/16 → tgw-aaa (return path OK)

TGW route table tgw-rtb-default contents:
  - 10.20.0.0/16 → tgw-attach-vpc-c (type: static, state: active)
  - 10.20.0.0/16 → tgw-attach-vpc-b (type: propagated, state: active)
  - 10.30.0.0/16 → tgw-attach-vpc-c (type: propagated, state: active)
  - 10.10.0.0/16 → tgw-attach-vpc-a (type: propagated, state: active)
```

TGW route table priority: for equal prefix length, static routes beat
propagated routes. Verify the static-vs-propagated interplay and identify
why traffic for 10.20.0.0/16 is being misrouted.
