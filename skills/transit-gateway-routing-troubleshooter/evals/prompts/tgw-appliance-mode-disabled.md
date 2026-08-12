# Eval prompt: tgw-appliance-mode-disabled

Diagnose the Transit Gateway routing failure for the following topology.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: cross-VPC flows through the inspection VPC succeed when the
source EC2 is in us-east-1a (where the firewall ENI lives), but
intermittently fail when the source EC2 is in us-east-1b. The firewall
logs show "out-of-state drop" for the failing flows.

```text
TGW: tgw-aaa
Inspection VPC attachment: tgw-attach-inspection
  Options.ApplianceModeSupport: disable
  Subnet: subnet-inspection-1a (us-east-1a only)
Firewall: AWS Network Firewall in us-east-1a, stateful rules

VPC-A attachment: tgw-attach-vpc-a (10.10.0.0/16)
VPC-B attachment: tgw-attach-vpc-b (10.20.0.0/16)
Traffic flow: vpc-a → tgw-aaa → inspection-vpc → tgw-aaa → vpc-b

TGW route tables: all routes correct for both VPCs (verified).
No static routes override. CIDRs do not overlap.

Recent pattern (last 24h):
  - Source AZ us-east-1a → success (40 flows)
  - Source AZ us-east-1b → out-of-state drop (38 flows)
```

TGW appliance mode forces the return path for flows transiting an
inspection VPC back through the inspection VPC's AZ, regardless of the
original source AZ. Verify the appliance-mode configuration and
recommend the fix.
