---
description: Provision Route 53 routing policies (simple, weighted, latency, failover, geolocation, geoproximity, multivalue, IP-based), alias records to AWS services, health checks, traffic policies, and Application Recovery Controller primitives. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create route 53 record"
  - "route 53 routing policy"
  - "weighted routing"
  - "latency routing"
  - "failover routing"
  - "geolocation routing"
  - "geoproximity routing"
  - "multivalue answer routing"
  - "ip based routing"
  - "cidr routing"
  - "alias record to alb"
  - "alias record to cloudfront"
  - "alias record to api gateway"
  - "alias record to s3 website"
  - "alias record to vpc endpoint"
  - "route 53 health check"
  - "route 53 traffic policy"
  - "application recovery controller"
  - "routing control"
  - "readiness check"
routes_to: route53-routing-policy-deployer
---

# /aws:deploy-route53-routing-policy

Activate the `route53-routing-policy-deployer` skill and provision
Route 53 routing policies and their dependent primitives.

## What it does

The skill walks an 8-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Confirm hosted zone + name + record type
2. Choose routing policy (simple, weighted, latency, failover, geolocation, geoproximity, multivalue, IP-based, alias)
3. Resolve target value(s) / alias targets
4. Configure health checks (per target where required)
5. Build the change-batch POST (atomic)
6. Optional: traffic policy / ARC routing control
7. Apply TTL appropriate to the policy
8. Verify via `test-dns-answer` + `get-health-check-status`

## When to use

- You need a DNS routing policy for multi-region, canary, geolocation, or DR failover.
- You want an alias record to an AWS service (ALB, CloudFront, API Gateway, S3 website, VPC interface endpoint).
- You are configuring a health check (endpoint, string matching, calculated, inverted).
- You are versioning a traffic policy or setting up Application Recovery Controller.
- You want to generate CloudFormation / Terraform for any of the above.

## How to invoke

### Slash command

```
/aws:deploy-route53-routing-policy
```

Then provide: hosted zone ID, record name, record type, routing policy,
and target value(s) or alias target. Add health check IDs and TTL.

### Natural language

Any of these routes to the same skill:

- "create a weighted routing policy"
- "set up failover DNS for DR"
- "alias this domain to my ALB"
- "build a geolocation routing set"
- "configure an ARC routing control"

### CLI routing

```bash
node cli/bin/cli.js route "create route 53 routing policy"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or update
a Route 53 routing policy. The output checklist feeds into verification
pipelines and operate skills (route53-failover-operator for emergency
failover execution, route53-record-auditor for post-deploy audit).

## Example

```
You: /aws:deploy-route53-routing-policy

     Provision weighted routing for api.example.com in zone
     Z2DABCDEFGHIJK. Primary 10.0.0.10 weight 90, canary 10.0.0.20
     weight 10. Health checks on HTTPS /healthz for both, atomic
     change-batch, TTL 60.

Skill:
  RECORD_SET: api.example.com A (routing policy: weighted)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Hosted zone confirmed: Z2DABCDEFGHIJK (example.com)
    [✓] Routing policy: weighted
    [✓] Target(s): primary 10.0.0.10 (w=90, hc-aaa), canary 10.0.0.20 (w=10, hc-bbb)
    [✓] Health check(s): hc-aaa (Healthy), hc-bbb (Healthy)
    [✓] Change-batch atomic: CREATE 2 records (single POST)
    [OPTIONAL] Optional feature: none
    [✓] TTL applied: 60s (rationale: fast canary re-normalization)
  VERIFICATION_COMMANDS:
    aws route53 test-dns-answer --hosted-zone-id Z2DABCDEFGHIJK --record-name api.example.com. --record-type A
    aws route53 get-health-check-status --health-check-id hc-aaa
    aws route53 get-health-check-status --health-check-id hc-bbb
    ...
```

## References

- Skill definition: `skills/route53-routing-policy-deployer/SKILL.md`
- Change-batch templates: `skills/route53-routing-policy-deployer/references/routing-policy-change-batches.md`
- Health check & ARC procedures: `skills/route53-routing-policy-deployer/references/health-check-and-arc-procedures.md`
- Eval suite: `skills/route53-routing-policy-deployer/evals/evals.json`
