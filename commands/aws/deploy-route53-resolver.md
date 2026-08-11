---
description: Provision Route 53 Resolver endpoints, forwarding rules, DNS Firewall policies, and query logging configurations with secure networking defaults. Emits a READY_TO_DEPLOY checklist with verification commands and blocks single-AZ endpoints and missing query-log resource policies.
nl_triggers:
  - "create resolver endpoint"
  - "provision resolver inbound endpoint"
  - "provision resolver outbound endpoint"
  - "deploy route 53 resolver"
  - "conditional forwarding rule"
  - "forwarding rule association"
  - "dns firewall"
  - "firewall domain list"
  - "firewall rule group"
  - "managed domain list"
  - "custom domain list"
  - "block dns domains"
  - "resolver query logging"
  - "dns query logs cloudwatch"
  - "dns query logs s3"
  - "hybrid dns setup"
  - "on-prem dns forwarding"
  - "route53resolver create-resolver-endpoint"
  - "route53resolver create-resolver-rule"
  - "route53resolver create-firewall-rule"
  - "resolver inbound endpoint"
  - "resolver outbound endpoint"
routes_to: route53-resolver-deployer
---

# /aws:deploy-route53-resolver

Activate the `route53-resolver-deployer` skill and provision Route 53
Resolver endpoints, forwarding rules, DNS Firewall policies, and query
logging configurations with secure networking defaults.

## What it does

The skill walks a pre-check gate and emits a READY_TO_DEPLOY checklist:

1. Endpoint name uniqueness (no collision with existing endpoints)
2. Subnet count and AZ diversity (minimum 2 subnets in 2 distinct AZs)
3. Security group ingress/egress (UDP/TCP 53 on the correct CIDRs)
4. VPC DNS settings (enableDnsSupport + enableDnsHostnames both true)
5. Forwarding rule domain (valid DNS suffix with trailing dot)
6. Forwarding target IPs (reachable from outbound endpoint subnets)
7. Rule association VPC (exists in the same account/region)
8. DNS Firewall rule group priority (no collisions on the target VPC)
9. Firewall domain list content (valid domain syntax, wildcard support)
10. Firewall action consistency (BLOCK requires BlockResponse)
11. Query log destination ARN (CloudWatch/S3/Kinesis exists and writable)
12. Query log resource policy (route53resolver principal has write access)
13. IAM permissions (route53resolver:CreateResolverEndpoint etc.)

## When to use

- You need to create a Resolver inbound endpoint (on-prem to Route 53).
- You need to create a Resolver outbound endpoint (VPC to on-prem DNS).
- You are configuring conditional forwarding rules with VPC associations.
- You want to deploy DNS Firewall with managed or custom domain lists.
- You need Resolver query logging to CloudWatch, S3, or Kinesis Firehose.
- You are setting up hybrid DNS between on-prem and AWS.

## How to invoke

### Slash command

```
/aws:deploy-route53-resolver
```

Then provide: endpoint name, region, direction (INBOUND/OUTBOUND), VPC,
subnets (>= 2 in distinct AZs), security group IDs, and (for outbound)
forwarding rule domain + target IPs.

### Natural language

Any of these routes to the same skill:

- "create a Resolver inbound endpoint for hybrid DNS"
- "set up conditional forwarding to on-prem DNS"
- "deploy DNS Firewall with the managed malware list"
- "enable Resolver query logging to CloudWatch"
- "create an outbound Resolver endpoint"

### CLI routing

```bash
node cli/bin/cli.js route "create a route53 resolver endpoint"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or extend
Resolver endpoints, forwarding rules, DNS Firewall, or query logging.
The output checklist feeds into verification pipelines and the
`route53-record-auditor` skill for post-deploy DNS auditing.

## Example

```
You: /aws:deploy-route53-resolver

     Create an outbound Resolver endpoint "prod-outbound" in us-east-1
     for VPC vpc-0abc123 with subnets subnet-aaa and subnet-bbb. Forward
     corp.example.local. to on-prem DNS 10.99.1.5 and 10.99.2.5.
     Account: 111111111111.

Skill:
  RESOLVER: prod-outbound
  VERDICT: READY_TO_DEPLOY
  TARGET: prod-outbound
  PRE_CHECKS:
    [PASS] Endpoint name unique
    [PASS] 2 subnets in 2 distinct AZs
    [PASS] Security group egress to 10.99.1.5, 10.99.2.5 on port 53
    [PASS] VPC enableDnsSupport: true
  ENDPOINT_TYPE: OUTBOUND
  FORWARDING_RULES: 1 (corp.example.local.)
  QUERY_LOGS: NONE
```

## References

- Skill definition: `skills/route53-resolver-deployer/SKILL.md`
- Endpoints & forwarding rules: `skills/route53-resolver-deployer/references/endpoints-and-forwarding-rules.md`
- DNS Firewall & query logging: `skills/route53-resolver-deployer/references/dns-firewall-and-query-logging.md`
- Eval suite: `skills/route53-resolver-deployer/evals/evals.json`
