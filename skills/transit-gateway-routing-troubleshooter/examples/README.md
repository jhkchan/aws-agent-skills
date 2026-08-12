# Example usage: transit-gateway-routing-troubleshooter

A walkthrough showing the skill diagnosing a Transit Gateway routing
failure where a static route overrides a propagated route,
demonstrating the symptom-to-layer triage, the static-vs-propagated
priority rule, the evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and
the static-route-deletion remediation.

## Input (user prompt)

> Our payments service in VPC-A (10.10.0.0/16) cannot reach the
> orders service in VPC-B (10.20.0.0/16) through our transit gateway.
> Pings time out; the orders instance never sees the packets in its
> VPC flow logs. Both VPCs are attached to the TGW — we've been
> debugging this as a security group issue for an hour and can't find
> the block.

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

## Skill output

```text
TARGET: tgw-aaa (source: tgw-attach-vpc-a, dest: tgw-attach-vpc-b)
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: VPC-A's associated TGW route table tgw-rtb-default contains a
  static route for 10.20.0.0/16 pointing at tgw-attach-vpc-c (a legacy
  attachment from a prior migration), which overrides the propagated
  route from VPC-B's attachment. TGW route table priority: for equal
  prefix length, static beats propagated. VPC-A's outbound traffic
  for VPC-B's CIDR is forwarded to VPC-C, where it is dropped (VPC-C
  has no host at the target IP) (Step 3a).
LAYER: TGW_STATIC_ROUTE_PRIORITY
EVIDENCE:
  - Symptom: EC2 in VPC-A (10.10.0.0/16) cannot ping EC2 in VPC-B
    (10.20.0.0/16). ICMP "request timeout". The VPC-B instance never
    sees the packet in its VPC flow logs.
  - Probe: aws ec2 search-transit-gateway-routes on tgw-rtb-default
    with type=static returns:
      10.20.0.0/16 → tgw-attach-vpc-c (static, active)
  - Probe: aws ec2 search-transit-gateway-routes on tgw-rtb-default
    with type=propagated returns:
      10.20.0.0/16 → tgw-attach-vpc-b (propagated, active — but
      shadowed by the static route)
  - Passing: VPC-A's route table correctly has 10.20.0.0/16 → tgw-aaa;
    VPC-B's return route table has 10.10.0.0/16 → tgw-aaa; CIDRs do
    not overlap; no peering in play (both VPCs on the same TGW).
REMEDIATION:
  1. Delete the stale static route so the propagated route wins:
     aws ec2 delete-transit-gateway-route \
       --transit-gateway-route-table-id tgw-rtb-default \
       --destination-cidr-block 10.20.0.0/16
  2. Verify the propagated route becomes the active forwarding route:
     aws ec2 search-transit-gateway-routes \
       --transit-gateway-route-table-id tgw-rtb-default \
       --filters Name=state,Values=active
     The route for 10.20.0.0/16 should now show tgw-attach-vpc-b.
  3. Re-test the ping from VPC-A to VPC-B; should succeed within
     seconds of the route propagation.
CONFIRM: Before deleting the route, emit and await:
  "CONFIRM: About to delete static route 10.20.0.0/16 from
   tgw-rtb-default. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished a static-route override from a security group
   block.** A generic assistant says "check the security groups." The
   skill recognises that the VPC-B instance never sees the packet at
   all (no VPC flow log entry) — that pattern indicates the traffic
   never reaches VPC-B, ruling out a security group on VPC-B's
   instance.

2. **Identified the static-vs-propagated priority rule.** The skill
   searches specifically for static routes (`--filters Name=type,
   Values=static`) and finds the legacy `10.20.0.0/16 →
   tgw-attach-vpc-c` entry. A generic assistant searching only active
   routes sees both entries but does not know which one wins.

3. **Ruled out the return path.** The skill verifies VPC-B's route
   table has `10.10.0.0/16 → tgw-aaa`, ruling out a one-way-return
   blackhole. A generic assistant may not check the return path at
   all.

4. **Recommended the route-table-side fix, not a security-group fix.**
   The primary remediation is deleting the stale static route so the
   propagated route takes effect. The fix is at the TGW route table,
   not at the VPC security group.

## Slash-command invocation

```
/aws:troubleshoot-transit-gateway-routing
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why VPC-A cannot reach VPC-B through tgw-aaa"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: transit-gateway-routing-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the route propagation and connectivity:

```bash
# Confirm the static route is gone and the propagated route is active
aws ec2 search-transit-gateway-routes \
  --transit-gateway-route-table-id tgw-rtb-default \
  --filters Name=state,Values=active \
  --profile default --output json | \
  jq '.Routes[] | select(.DestinationCidrBlock=="10.20.0.0/16")'

# Confirm the ping succeeds from VPC-A to VPC-B (via SSM if available)
aws ssm send-command \
  --instance-ids <vpc-a-instance-id> \
  --document-name AWS-RunShellScript \
  --parameters 'commands=["ping -c 3 <vpc-b-instance-private-ip>"]' \
  --profile default --output json
```

Then monitor the TGW flow logs for the next 15-30 minutes to confirm
bidirectional traffic for the VPC-A ↔ VPC-B CIDR pair.
