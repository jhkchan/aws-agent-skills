# End-to-end usage scenario: clb-to-alb-migration-operator

A walkthrough showing the skill planning a CLB-to-ALB migration for an
HTTP/HTTPS Classic Load Balancer with an ACM cert, then a BLOCKED case
where the CLB has a TCP listener that ALB cannot handle.

## Input (user prompt)

> Migrate `prod-web-clb` (Classic, internet-facing, HTTP:80 -> HTTPS:443
> with ACM cert) to a new ALB `prod-web-alb`. The CLB has sticky
> sessions (lb cookie, 3600s) and connection draining (300s). Plan the
> migration with weighted DNS cutover.

```json
{
  "Operation": "plan-migration",
  "CLB": "prod-web-clb",
  "PlannedALB": "prod-web-alb",
  "Region": "us-east-1",
  "LoadBalancer": {
    "Scheme": "internet-facing",
    "Subnets": ["subnet-aaa", "subnet-bbb"],
    "Listeners": [
      {"Protocol": "HTTP", "Port": 80, "InstancePort": 8080},
      {"Protocol": "HTTPS", "Port": 443, "InstancePort": 8080, "Cert": "arn:aws:acm:us-east-1:111111111111:certificate/abc"}
    ],
    "Policies": [{"LBCookieStickinessPolicy": {"timeout": 3600}}],
    "ConnectionDraining": {"enabled": true, "timeout": 300}
  }
}
```

## Skill output

```text
OPERATION: plan-migration
VERDICT: READY
TARGET: prod-web-clb -> prod-web-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] CLB exists, Scheme: internet-facing
  - [PASS] Two subnets in us-east-1a, us-east-1b
  - [PASS] Listeners: HTTP:80 (redirect to HTTPS), HTTPS:443 (cert
    arn:aws:acm:us-east-1:111111111111:certificate/abc, ISSUED)
  - [PASS] No TCP/SSL passthrough listeners (no NLB needed)
  - [PASS] LBCookieStickinessPolicy timeout=3600 -> ALB
    stickiness.type=lb_cookie, duration_seconds=3600
  - [PASS] No ProxyProtocolPolicyType detected
  - [PASS] ConnectionDraining timeout=300 -> deregistration_delay.
    timeout_seconds=300
  - [PASS] Target SG sg-target-web allows sg-alb-prod on tcp/8080
STEPS:
  1. CONFIRM: About to plan the ALB migration of prod-web-clb -> prod-
     web-alb in account 111111111111 region us-east-1. Plan only — no
     resources created. Proceed? (yes/no)
  2. (Plan output): ALB prod-web-alb, target group tg-web-8080,
     listener HTTPS:443 with cert abc, default action forward tg-web-
     8080, plus rule path /api/* -> tg-api-8080. Cutover: weighted
     5/25/50/100 over 4 hours. Rollback: flip Route 53 weights to
     100/0.
POST_VERIFY:
  - (pending execution)
NOTES:
  - Feature gains: path-based routing (/api/* to dedicated TG), WAF
    attachment, OIDC via Cognito if added later.
  - No feature loss: CLB had no Proxy Protocol, no TCP listeners.
  - Rollback window: keep CLB alive 72 hours post-cutover.
```

## Contrast — BLOCKED case (TCP listener)

If the operator tried to migrate a CLB with a `TCP:4242` listener for
a custom binary protocol, the pre-check gate would fire:

```text
OPERATION: plan-migration
VERDICT: BLOCKED
TARGET: prod-game-clb -> prod-game-alb (account 111111111111, region
        us-east-1)
PRE_CHECKS:
  - [PASS] CLB exists, Scheme: internet-facing
  - [PASS] Two subnets in different AZs
  - [FAIL] ListenerDescriptions[1].Protocol: TCP on port 4242 — ALB
    is HTTP/HTTPS only. TCP listeners must migrate to NLB (which
    supports TCP/SSL passthrough). Silently dropping this listener
    would orphan the game protocol traffic.
STEPS: (none — listener incompatible with ALB)
POST_VERIFY: (none)
NOTES:
  - Root cause: ALB supports HTTP and HTTPS only. A CLB TCP listener
    (custom binary protocol, SSL passthrough) cannot move to ALB.
  - Fix: (a) migrate the TCP:4242 listener to an NLB, OR (b) if the
    protocol is actually HTTP behind a TCP wrapper, terminate at the
    ALB and create an HTTPS listener. Inspect the backend protocol.
```

## What the skill caught that a generic assistant misses

1. **TCP listener detection.** A generic assistant creates the ALB and
   silently drops the TCP listener. The skill detects the TCP protocol
   and BLOCKS, routing to NLB planning.

2. **Proxy Protocol awareness.** A generic assistant cuts over DNS
   without checking for ProxyProtocolPolicyType. The skill checks the
   CLB policy list AND the backend listener config before cutover.

3. **Sticky session semantics.** A generic assistant says "sticky
   sessions carry over." The skill maps LBCookieStickinessPolicy to
   the ALB target group attribute and flags the cookie-lifetime
   semantics difference.

4. **Deregistration delay matching.** A generic assistant omits this.
   The skill reads the CLB ConnectionDraining timeout and sets the
   target group deregistration_delay to match.

5. **IAM vs ACM certificate awareness.** A generic assistant reuses the
   IAM cert ARN directly. The skill detects IAM-uploaded certs and
   recommends re-issuing via ACM for free managed renewal.

6. **Weighted cutover phases.** A generic assistant says "update DNS."
   The skill specifies 5/25/50/100 phases with validation gates and a
   one-line rollback (weight flip).

7. **Rollback window.** A generic assistant says "delete the CLB after
   cutover." The skill mandates keeping the CLB for 24-72 hours as the
   rollback target.

## Slash-command invocation

```
/aws:operate-clb-to-alb-migration
```

Or via the orchestrator:

```
/aws:pipeline
You: "migrate prod-web-clb to ALB"
```

The orchestrator emits
`[Phase: Operate | Skills routed: clb-to-alb-migration-operator]` and
hands off to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "migrate CLB prod-web-clb to ALB"
# [Phase: Operate | Skills routed: clb-to-alb-migration-operator]
```

## Live-account follow-up (optional, requires AWS CLI)

After the plan is READY:

```bash
# Create the ALB
aws elbv2 create-load-balancer --name prod-web-alb \
  --subnets subnet-aaa subnet-bbb \
  --security-groups sg-alb-prod \
  --scheme internet-facing --type application \
  --profile default

# Create the target group
aws elbv2 create-target-group --name tg-web-8080 \
  --protocol HTTP --port 8080 --vpc-id vpc-abc123 \
  --health-check-path /healthz --matcher HttpCode 200 \
  --profile default

# Set stickiness + deregistration delay
aws elbv2 modify-target-group-attributes \
  --target-group-arn <tg-arn> \
  --attributes \
    Key=stickiness.enabled,Value=true \
    Key=stickiness.type,Value=lb_cookie \
    Key=stickiness.duration_seconds,Value=3600 \
    Key=deregistration_delay.timeout_seconds,Value=300 \
  --profile default

# Create the HTTPS listener
aws elbv2 create-listener --load-balancer-arn <alb-arn> \
  --protocol HTTPS --port 443 \
  --certificates CertificateArn=arn:aws:acm:us-east-1:111111111111:certificate/abc \
  --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 \
  --default-actions Type=forward,TargetGroupArn=<tg-arn> \
  --profile default

# Register the same instances the CLB used
aws elbv2 register-targets --target-group-arn <tg-arn> \
  --targets i-aaa i-bbb i-ccc --profile default

# Verify target health
aws elbv2 describe-target-health --target-group-arn <tg-arn> \
  --profile default
```
