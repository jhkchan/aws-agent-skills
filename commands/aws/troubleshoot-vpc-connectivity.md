---
description: Diagnose AWS VPC network connectivity issues through an OSI-layered diagnostic tree (routing, security groups, NACLs, DNS, VPC endpoint policy, peering, TGW, PrivateLink) — emits ROOT_CAUSE_FOUND with the specific layer or ESCALATE.
nl_triggers:
  - "VPC connection timeout"
  - "cannot reach EC2 instance"
  - "EC2 port unreachable"
  - "Lambda VPC timeout"
  - "ECS task cannot reach"
  - "security group blocking traffic"
  - "NACL dropping packets"
  - "route table missing"
  - "VPC peering not working"
  - "Transit Gateway routing"
  - "TGW routes not propagating"
  - "VPC endpoint policy blocked"
  - "DNS not resolving in VPC"
  - "Route 53 private hosted zone"
  - "cross-VPC connectivity"
  - "PrivateLink endpoint service"
  - "Reachability Analyzer"
  - "VPC Flow Logs analysis"
  - "overlapping CIDR peering"
  - "troubleshoot VPC connectivity"
  - "diagnose network connectivity"
routes_to: vpc-connectivity-troubleshooter
---

# /aws:troubleshoot-vpc-connectivity

Activate the `vpc-connectivity-troubleshooter` skill and diagnose a VPC
network connectivity issue through the OSI-layered diagnostic tree.

## What it does

Reads a symptom description (error message, observed behaviour, source
and destination context) then walks the OSI-aligned diagnostic tree to
a root cause with positive evidence:

1. **Pre-flight** — source/destination context (`describe-instances`,
   `describe-subnets`, `describe-vpcs`), AWS Health (regional
   incidents, AZ-wide degradation). Short-circuits on AWS-side events.
2. **Symptom entry** — map the error to one of: timeout, DNS failure,
   endpoint-policy 403, peering asymmetry, TGW propagation gap,
   PrivateLink acceptance / SG / NLB issue, application-layer auth.
3. **OSI-aligned probes** — for timeouts, walk OSI order:
   - DNS resolution → route table (source subnet + dest subnet) →
     overlapping-CIDR check → SG inbound (dest) → SG outbound (source) →
     NACL both directions both subnets → cross-VPC plumbing → final
     `nc -vz`.
   - For DNS: VPC `enableDnsSupport` / `enableDnsHostnames` →
     `list-hosted-zones-by-vpc` for PHZ association → Resolver
     endpoints and rules.
   - For HTTP 403 from AWS service: `describe-vpc-endpoints` (Policy,
     State) → bypass the endpoint to verify.
   - For VPC peering: status (`active` / `pending-acceptance` /
     `failed`) → route table both sides (pcx route) → overlapping CIDR
     → SG references (peering route must exist for cross-VPC SG ref) →
     DNS resolution flag.
   - For Transit Gateway: attachment state → TGW route table
     association vs propagation → VPC route tables both sides.
   - For PrivateLink: endpoint state → endpoint SG → endpoint service
     configuration → NLB target health → PrivateDnsEnabled.
4. **Verdict** — ROOT_CAUSE_FOUND (with failing probe that matches the
   symptom), NEED_MORE_INFO (a probe requires operator input), or
   ESCALATE (AWS-side incident; surface AWS Health event ARN).

Emits a deterministic diagnostic block per target pair:

```text
TARGET: <source → destination pair>
VERDICT: ROOT_CAUSE_FOUND | NEED_MORE_INFO | ESCALATE
REASON: <1-2 sentences naming the failed layer and the failing probe>
LAYER: <ROUTE_TABLE_MISSING | ROUTE_TABLE_WRONG_TARGET |
        ROUTE_OVERLAPPING_CIDR | SG_INBOUND | SG_OUTBOUND |
        SG_REFERENCE_CROSS_VPC | NACL_STATELESS | DNS_RESOLUTION |
        DNS_PHZ_ASSOCIATION | ENDPOINT_POLICY | PEERING_INACTIVE |
        PEERING_DNS_RESOLUTION | PEERING_SG_REFERENCE |
        TGW_ROUTE_PROPAGATION | TGW_ASSOCIATION_MISSING |
        PRIVATELINK_ENDPOINT_SERVICE | PRIVATELINK_SG | APP_AUTH |
        UNKNOWN>
EVIDENCE:
  - <observed symptom — error string or behaviour>
  - <failing probe — command and its output that confirms the cause>
  - <passing probes — layers ruled out>
REMEDIATION:
  1. <specific action with CLI command>
  2. <verification command after the fix>
```

## When to invoke

Paste a symptom description and ask any of:

- "EC2 instance cannot reach another EC2 instance — connection times
  out"
- "Lambda function in VPC cannot reach the internet"
- "VPC peering Active but traffic times out"
- "TGW attachments Active but traffic times out"
- "VPC endpoint returning AccessDenied for an IAM-allowed action"
- "Route 53 private hosted zone not resolving in a peered VPC"
- "PrivateLink endpoint accepted but service unreachable"
- "overlapping CIDRs between peered VPCs"

A bare source + destination + any connectivity verb ("cannot reach",
"port blocked", "DNS failure") also routes here via the orchestrator.

## Inputs

- Symptom description: error string, observed behaviour, intermittent
  vs persistent pattern.
- Source context: EC2 instance / Lambda / ECS task / on-prem host.
  Subnet, security group, region, AZ.
- Destination context: EC2 instance / RDS / Lambda / external host.
  Subnet, security group, port, protocol.
- For cross-VPC: peering connection ID / TGW ID / PrivateLink endpoint
  ID. The skill uses `describe-route-tables`,
  `describe-security-groups`, `describe-network-acls`,
  `describe-vpc-endpoints`, `describe-vpc-peering-connections`,
  `describe-transit-gateway-attachments`,
  `describe-transit-gateway-route-tables`, Reachability Analyzer
  (`create-network-insights-path` /
  `describe-network-insights-analyses`), Route 53 Resolver
  (`list-resolver-endpoints`, `list-resolver-rules`),
  `list-hosted-zones-by-vpc`, and `describe-vpcs`.

## Outputs

- One diagnostic block per target pair.
- Layer-specific LAYER value from the enumerated set.
- Evidence section with the failing probe AND passing probes (layers
  ruled out) — never a verdict without positive evidence.
- Specific remediation: route table addition, SG/NACL rule addition,
  VPC DNS flag fix, PHZ association, endpoint policy edit, peering
  acceptance, TGW propagation enable, or AWS Support escalation.

## Related

- `/aws:pipeline` to enter the full CloudOps pipeline (this skill is
  the Phase 2 Troubleshoot specialist for VPC connectivity).
- `/aws:audit-ec2-security-groups` for security-group exposure audits
  on the same source / destination.
- `/aws:troubleshoot-rds-connectivity` for RDS-specific auth and TLS
  issues once VPC reachability is confirmed.
- `/aws:troubleshoot-lambda-invocation` for Lambda-specific invocation
  failures (OOM, timeout, container image) once VPC reachability is
  confirmed.
- `/aws:troubleshoot-iam-permission` for AccessDenied from IAM, SCP,
  or permissions boundary (separate from VPC endpoint policy).
