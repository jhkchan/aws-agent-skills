# Worked examples — transit-gateway-routing-troubleshooter

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

### Worked example — Appliance mode disabled

```text
TARGET: tgw-aaa (inspection-vpc-attachment: tgw-attach-inspection)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The inspection VPC's attachment has ApplianceModeSupport=disable.
  Flows from us-east-1a (where the firewall ENI lives) succeed; flows
  from us-east-1b fail because the return traffic exits the TGW in
  us-east-1b, bypassing the firewall, which drops the flow as
  out-of-state (Step 5).
LAYER: TGW_APPLIANCE_MODE
EVIDENCE:
  - Symptom: cross-VPC flows succeed when the source is in
    us-east-1a; intermittently fail when the source is in
    us-east-1b. Firewall logs show "out-of-state drop".
  - Probe: aws ec2 describe-transit-gateway-attachments on
    tgw-attach-inspection returns Options.ApplianceModeSupport=disable.
  - Passing: TGW route tables contain correct routes for both VPCs;
    no static routes override; CIDRs do not overlap.
REMEDIATION:
  1. Enable appliance mode:
     aws ec2 modify-transit-gateway-attachment \
       --transit-gateway-attachment-id tgw-attach-inspection \
       --options ApplianceModeSupport=enable
  2. Verify flows from us-east-1b now succeed.
CONFIRM: Before modifying the attachment, emit and await:
  "CONFIRM: About to enable ApplianceModeSupport on
   tgw-attach-inspection. Proceed? (yes/no)"
```
