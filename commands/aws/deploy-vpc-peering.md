---
description: Provision an Amazon VPC peering connection with production-grade defaults (requester/accepter model, same-account vs cross-account, same-region vs inter-region, route tables on BOTH sides, DNS resolution, security group cross-VPC references, IPv6 support). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create vpc peering"
  - "deploy vpc peering"
  - "vpc peering connection"
  - "cross-account vpc peering"
  - "inter-region vpc peering"
  - "vpc peering route table"
  - "vpc peering dns resolution"
  - "vpc peering security group"
  - "accept vpc peering"
  - "vpc peering ipv6"
  - "connect two vpcs"
  - "peer vpc"
  - "vpc peering"
routes_to: vpc-peering-deployer
---

# /aws:deploy-vpc-peering

Activate the `vpc-peering-deployer` skill and provision an Amazon VPC
peering connection with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Requester/accepter model (create and accept)
2. Same-account vs cross-account (acceptance automation)
3. Same-region vs inter-region (--peer-region)
4. Create and accept the peering connection
5. Route table updates (BOTH sides required)
6. DNS resolution (AllowDnsResolutionFromPeeredVpc — both sides)
7. Security group cross-VPC references (same account+region only)
8. Limitations (no transitive routing, no edge-to-edge)
9. IPv6 support (independent from IPv4 routes)
10. Recent features (IPv6 maturity, inter-region performance)

## When to use

- You need to create a VPC peering connection between two VPCs.
- You are setting up cross-account VPC peering.
- You are setting up inter-region VPC peering.
- You need DNS resolution across peered VPCs.
- You need security group cross-VPC references.
- You need IPv6 routing across a peering connection.
- You need to understand peering limitations (transitive routing).

## When NOT to use

- **AWS Transit Gateway** — use Transit Gateway skills for hub-and-spoke
  or transitive routing topologies.
- **VPC endpoints (PrivateLink)** — different connectivity model.
- **VPN / Direct Connect** — use VPN/DX-specific skills.
- **Auditing existing peering connections** — use VPC audit skills.

## How to invoke

### Slash command

```
/aws:deploy-vpc-peering
```

Then provide: requester VPC ID, accepter VPC ID, accepter account ID
(if cross-account), peer region (if inter-region), route table IDs
(both sides), DNS resolution decision, security group IDs, IPv6
requirements, tags.

### Natural language

Any of these routes to the same skill:

- "create a VPC peering connection between vpc-aaa and vpc-bbb"
- "set up cross-account VPC peering"
- "enable DNS resolution across my peered VPCs"
- "create an inter-region VPC peering connection"
- "configure VPC peering with IPv6 routing"

### CLI routing

```bash
node cli/bin/cli.js route "create a vpc peering connection"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create VPC
peering connections. The output checklist feeds into verification
pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-vpc-peering

     Create a VPC peering connection between vpc-aaa11122
     (10.0.0.0/16) and vpc-bbb22233 (10.1.0.0/16) in us-east-1.
     Same account 123456789012. Enable DNS resolution.
     Route tables rtb-app111 and rtb-data222.

Skill:
  VPC_PEERING: vpc-aaa11122 ↔ vpc-bbb22233
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Peering connection: ACTIVE
    [✓] Route table (requester): rtb-app111 → 10.1.0.0/16
    [✓] Route table (accepter): rtb-data222 → 10.0.0.0/16
    [✓] DNS resolution: AllowDnsResolutionFromPeeredVpc (both sides)
  VERIFICATION_COMMANDS:
    aws ec2 describe-vpc-peering-connections --vpc-peering-connection-ids <pcx-id> --region us-east-1
    aws ec2 describe-route-tables --route-table-ids rtb-app111 --region us-east-1
```

## References

- Skill definition: `skills/vpc-peering-deployer/SKILL.md`
- Routing and DNS guide: `skills/vpc-peering-deployer/references/routing-and-dns.md`
- Cross-account and security guide: `skills/vpc-peering-deployer/references/cross-account-and-security.md`
- Eval suite: `skills/vpc-peering-deployer/evals/evals.json`
