# Worked Examples — ALB 5xx Troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## NEED_MORE_INFO re-prompt (malformed input)

```text
TARGET: <lb-arn or unknown>
VERDICT: NEED_MORE_INFO
REASON: Input is missing required context — at minimum the 5xx error
  code (500/502/503/504/561), the load balancer ARN, and the target
  group ARN. Cannot drive a diagnostic tree without the error-code layer.
LAYER: UNKNOWN
EVIDENCE:
  - Missing: <list specific missing fields>
REMEDIATION: Re-prompt the operator for: (1) the exact 5xx error code
  from the client or ALB access log, (2) the load balancer ARN or name,
  (3) the target group ARN, and (4) for live diagnosis, the time window
  of the failure.
```

## Worked example — 502 from target SG not allowing ALB SG

```text
TARGET: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/app/prod-api/ghi / target-group/tg-api/jkl
VERDICT: ROOT_CAUSE_FOUND
REASON: The target security group sg-target-api has no inbound rule
  allowing the ALB security group sg-alb-prod on port 443 — the ALB
  cannot establish a connection to the targets (Step 2b).
LAYER: TARGET_SG_BLOCKED
EVIDENCE:
  - Symptom: clients receive 502 BadGateway. ALB access logs show
    error_reason: Target.ConnectionFailed for all requests.
  - Probe: aws elbv2 describe-target-health shows all targets State:
    healthy (health check is on a different port that IS allowed by
    the SG — port 80, while the target group serves on 443).
  - Probe: aws ec2 describe-security-groups --group-ids sg-target-api
    returns inbound rules allowing tcp/80 from sg-alb-prod but NO rule
    for tcp/443.
  - Probe: aws elbv2 describe-target-groups returns Port: 443 for
    tg-api (the target group forwards on 443, not 80).
  - Passing: health check passes on port 80 (traffic from sg-alb-prod
    on port 80 is allowed); targets are healthy; ALB idle timeout is
    60s; listener rule correctly points to tg-api.
REMEDIATION:
  1. Add an inbound rule to sg-target-api allowing the ALB SG on port
     443:
     aws ec2 authorize-security-group-ingress --group-id sg-target-api
       --protocol tcp --port 443 --source-security-group-id sg-alb-prod
       --profile <p>
  2. Verify: curl from the ALB subnet to the target on 443 succeeds;
     clients no longer see 502.
CONFIRM: Before authorizing the SG ingress, emit and await:
  "CONFIRM: About to authorize-security-group-ingress on sg-target-api
   for sg-alb-prod on tcp/443. Proceed? (yes/no)"
```

## Worked example — 504 from target exceeding idle timeout

```text
TARGET: arn:aws:elasticloadbalancing:us-east-1:111:load-balancer/app/prod-reports/mno / target-group/tg-reports/pqr
VERDICT: ROOT_CAUSE_FOUND
REASON: The report-generation endpoint takes 75-90 seconds to respond,
  exceeding the ALB idle timeout of 60 seconds. The ALB returns 504 at
  60s while the target continues processing (Step 4).
LAYER: TARGET_TIMEOUT
EVIDENCE:
  - Symptom: clients receive 504 GatewayTimeout on POST /reports/generate
    after exactly 60 seconds.
  - Probe: aws elbv2 describe-load-balancer-attributes returns
    idle_timeout.timeout_seconds: 60.
  - Probe: ALB access logs show target_processing_time: 60.0 and
    error_reason: Target.Timeout for the failing requests.
  - Probe: CloudWatch TargetResponseTime metric shows Maximum 60.0s
    (capped — the ALB closes at 60s even though the target continues).
  - Probe: ssh <bastion> "time curl -X POST
    http://<target-ip>:8080/reports/generate -d '@test.json'"
    returns the response in 82 seconds (the target is slow but succeeds
    when given time).
  - Passing: targets are healthy; target SG allows ALB SG on 8080;
    listener rule correctly points to tg-reports.
REMEDIATION:
  1. Raise the ALB idle timeout to 120s (verify the target can finish
     within 120s):
     aws elbv2 modify-load-balancer-attributes --load-balancer-arn <arn>
       --attributes Key=idle_timeout.timeout_seconds,Value=120
       --profile <p>
  2. Alternatively, migrate the report-generation endpoint to an async
     pattern (POST returns 202 with a job ID; client polls for status).
     This is preferred for endpoints that take > 60s.
  3. Verify: POST /reports/generate returns 200 within 120s.
CONFIRM: Before modifying the ALB attributes, emit and await:
  "CONFIRM: About to modify-load-balancer-attributes on <arn>
   (idle_timeout 60 → 120). Proceed? (yes/no)"
```
