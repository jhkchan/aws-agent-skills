# End-to-end usage scenario: elbv2-load-balancer-auditor

A walkthrough showing the skill auditing a production ALB that has a TLS 1.0
listener policy (INSECURE_LISTENER) and disabled access logs (NO_ACCESS_LOGS),
demonstrating verdict aggregation, the protocol-downgrade reasoning, and the
per-verdict CLI remediation workflow.

## Input (user prompt)

> Review this ALB before our PCI-DSS compliance audit next week. It fronts
> our payment API.

```text
Load balancer ARN: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/prod-payments-alb/pay123abc
Type: application
Scheme: internet-facing
State: active
Security groups: sg-0pay1111
Access logs: disabled
Deletion protection: enabled
Cross-zone load balancing: enabled (always on for ALB)

Listeners:
  - Protocol: HTTPS, Port: 443
    SslPolicy: ELBSecurityPolicy-2016-08
    DefaultAction: forward to tg-payments-api
  - Protocol: HTTP, Port: 80
    DefaultAction: redirect to HTTPS://#{host}:443/#{path}?#{query} (HTTP_301)

Security group sg-0pay1111 inbound rules:
  - TCP 443 from 0.0.0.0/0
  - TCP 80 from 0.0.0.0/0

Target groups:
  - tg-payments-api: 4 registered targets (all healthy)
```

## Skill output

```text
LB: arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/prod-payments-alb/pay123abc
VERDICT: INSECURE_LISTENER
REASON: HTTPS listener on port 443 uses ELBSecurityPolicy-2016-08 which
includes TLS 1.0 and TLS 1.1 — both deprecated by PCI-DSS 3.2.1+ (Step 1).
Access logs are also disabled (Step 3).
FINDINGS:
  - [CRITICAL] HTTPS:443 SslPolicy ELBSecurityPolicy-2016-08 includes TLS
    1.0/1.1 — the AWS default policy is insecure by modern standards; clients
    can be forced into a protocol downgrade (Step 1)
  - [HIGH] Access logs disabled — no per-request forensic trail for PCI-DSS
    requirement 10 (audit trails) or incident response (Step 3)
  - [OK] HTTP:80 listener redirects to HTTPS — standard secure pattern (Step 1)
  - [OK] Security group allows 0.0.0.0/0 only on ports 80/443 — expected for
    internet-facing ALB (Step 2)
  - [OK] Target group tg-payments-api has 4 healthy targets — LB is serving
    traffic (Step 4)
  - [OK] Deletion protection enabled (Step 5)
REMEDIATION:
  1. CRITICAL — Update the HTTPS listener SslPolicy:
     aws elbv2 modify-listener \
       --listener-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/prod-payments-alb/pay123abc/abc456 \
       --ssl-policy ELBSecurityPolicy-TLS13-1-2-2021-06 --profile default
  2. HIGH — Enable access logs (requires S3 bucket with correct policy):
     aws elbv2 modify-load-balancer-attributes \
       --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/prod-payments-alb/pay123abc \
       --attributes Key=access_logs.s3.enabled,Value=true \
       Key=access_logs.s3.bucket,Value=alb-logs-pci \
       Key=access_logs.s3.prefix,Value=payments \
       --profile default
  3. After changes, verify target health remains healthy:
     aws elbv2 describe-target-health \
       --target-group-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:target-group/tg-payments-api/xyz789 \
       --profile default
```

## What the skill caught that a generic assistant misses

1. **ELBSecurityPolicy-2016-08 is the AWS default and is insecure.** A
   generic assistant sees "TLS policy" and may not recognize that the default
   policy includes TLS 1.0/1.1. The skill identifies it by name and maps it
   directly to a PCI-DSS violation (requirement 4.1: strong cryptography,
   TLS 1.2+ required).

2. **The HTTP redirect listener is NOT flagged.** The HTTP:80 listener with a
   redirect action is the standard secure ALB pattern. A naive auditor flags
   "cleartext HTTP." The skill recognizes the redirect action and marks it OK.

3. **Verdict aggregation with per-finding breakdown.** The verdict is
   INSECURE_LISTENER (worst finding), but the FINDINGS list shows both the
   CRITICAL TLS finding and the HIGH access-logs finding. The operator can
   triage each independently — fix the TLS policy first (blocks PCI
   compliance), then enable logs.

4. **The access-logs finding has a compliance citation.** The skill maps
   "no access logs" to PCI-DSS requirement 10 (audit trails), not just "you
   should enable logs." This gives the operator the exact control mapping
   needed for the compliance audit.

## Slash-command invocation

```
/aws:audit-elbv2-load-balancer
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this ALB before our PCI-DSS review"
```

The orchestrator emits
`[Phase: Audit | Skills routed: elbv2-load-balancer-auditor]` and hands off
to this skill for the VERDICT.

## CLI routing

```bash
node cli/bin/cli.js route "audit this load balancer"
# [Phase: Audit | Skills routed: elbv2-load-balancer-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the TLS policy and enabling access logs, validate:

```bash
# Verify the new SslPolicy is applied
aws elbv2 describe-listeners \
  --listener-arns arn:aws:elasticloadbalancing:us-east-1:111111111111:listener/app/prod-payments-alb/pay123abc/abc456 \
  --query 'Listeners[0].SslPolicy' --profile default

# Confirm access logs are enabled
aws elbv2 describe-load-balancer-attributes \
  --load-balancer-arn arn:aws:elasticloadbalancing:us-east-1:111111111111:load-balancer/app/prod-payments-alb/pay123abc \
  --profile default | jq '.Attributes[] | select(.Key | startswith("access_logs"))'

# Verify S3 bucket policy grants ELB write access
aws s3api get-bucket-policy --bucket alb-logs-pci --profile default | jq '.'

# Check that log objects are appearing (after 5-10 minutes)
aws s3 ls s3://alb-logs-pci/payments/AWSLogs/111111111111/elasticloadbalancing/us-east-1/ \
  --recursive --profile default | tail -5
```

Then run an external TLS scan (ssllabs.com or testssl.sh) to confirm no
client can negotiate TLS 1.0 or 1.1 against the updated listener.
