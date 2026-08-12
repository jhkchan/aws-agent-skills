---
description: Provision an Amazon VPC Lattice service network with services, target groups (instance/IP/Lambda/ALB), listener rules (path/header/method routing), IAM auth policy at service level, health checks, cross-account access via RAM, custom domains, traffic splitting for canary, and access logs. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create vpc lattice service network"
  - "deploy vpc lattice service"
  - "vpc lattice target group"
  - "vpc lattice listener rule"
  - "vpc lattice auth policy"
  - "vpc lattice traffic splitting"
  - "vpc lattice canary"
  - "vpc lattice custom domain"
  - "vpc lattice cross-account"
  - "vpc lattice access logs"
  - "vpc lattice health check"
  - "vpc lattice service network vpc association"
  - "lattice service"
routes_to: vpclattice-service-deployer
---

# /aws:deploy-vpclattice-service

Activate the `vpclattice-service-deployer` skill and provision an
Amazon VPC Lattice service network with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Service network (top-level routing plane, account-level)
2. Target group (INSTANCE/IP/LAMBDA/ALB, health check determines routing)
3. Service (HTTP/gRPC, auto-assigned DNS name)
4. Listener rules (path-based, header-based, method-based routing)
5. IAM auth policy (at SERVICE level, NOT rule level — covers all paths)
6. Resource-based service policy (cross-account invocation)
7. Service network VPC association (required for DNS resolution)
8. Cross-account access (RAM share + service policy)
9. Custom domain mapping (ACM cert in us-east-1)
10. Traffic splitting (canary, weighted forwarding)
11. Access log delivery (CloudWatch / S3)
12. Pricing (per GB processed + per service-hour)

## When to use

- You need to create a VPC Lattice service network.
- You are provisioning a Lattice HTTP or gRPC service.
- You need target groups (instance, IP, Lambda, or ALB).
- You need listener rules (path, header, method routing).
- You need IAM auth at the service level.
- You need cross-account Lattice access via RAM.
- You need custom domain mapping for a Lattice service.
- You need traffic splitting for canary deployments.
- You need access log delivery to CloudWatch or S3.

## When NOT to use

- **VPC peering** — use the vpc-peering-deployer skill.
- **Transit Gateway** — use Transit Gateway skills for hub-and-spoke.
- **ALB / NLB** — use ALB/NLB-specific skills for load balancing.
- **API Gateway (HTTP API)** — different application-layer routing model.
- **Auditing existing Lattice services** — use Lattice audit skills.

## How to invoke

### Slash command

```
/aws:deploy-vpclattice-service
```

Then provide: service network name, auth type (AWS_IAM or NONE),
service name, target group type (INSTANCE/IP/LAMBDA/ALB), VPC ID,
health check path, listener rules (path/header/method), auth policy
decision, custom domain (if needed), traffic splitting weights,
access log destination, tags.

### Natural language

Any of these routes to the same skill:

- "create a vpc lattice service network"
- "deploy a lattice service with canary traffic splitting"
- "configure iam auth policy on my lattice service"
- "set up cross-account vpc lattice access"
- "map a custom domain to my lattice service"

### CLI routing

```bash
node cli/bin/cli.js route "create a vpc lattice service network"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create VPC Lattice
resources. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-vpclattice-service

     Create a VPC Lattice service network named prod-network with
     auth type AWS_IAM. HTTP service payments-svc. Target group
     tg-stable (INSTANCE, port 8080, VPC vpc-aaa11122). Path /api/*
     routes 20% canary / 80% stable. IAM auth at service level.
     CloudWatch access logs. us-east-1.

Skill:
  VPC_LATTICE: sni-aaa111 → svc-bbb222
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Service network: sni-aaa111 (auth type: AWS_IAM)
    [✓] Health check: path /health, interval 30s
    [✓] Auth policy: IAM auth at SERVICE level (covers ALL rules)
    [✓] Traffic splitting: canary 20% / stable 80%
    [✓] Access logs: CloudWatch
  VERIFICATION_COMMANDS:
    aws vpc-lattice get-service-network --service-network-identifier sni-aaa111
    aws vpc-lattice list-targets --target-group-identifier tgc-stable
```

## References

- Skill definition: `skills/vpclattice-service-deployer/SKILL.md`
- Auth policy and access guide: `skills/vpclattice-service-deployer/references/auth-policy-and-access.md`
- Listener rules and health guide: `skills/vpclattice-service-deployer/references/listener-rules-and-health.md`
- Eval suite: `skills/vpclattice-service-deployer/evals/evals.json`
