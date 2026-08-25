# Worked Examples (load on demand) — App Runner Autoscaling Optimizer

Secondary worked examples moved verbatim from SKILL.md (the primary concurrency-tuning example stays in SKILL.md). Loaded on demand.

---

## Worked example — pause/resume for non-prod (FURTHER_OPTIMIZATION_AVAILABLE) (moved from SKILL.md)

```text
TARGET: dev-staging-service (region: us-east-1)
VERDICT: FURTHER_OPTIMIZATION_AVAILABLE
REASON: Service runs 24/7 in a dev environment. Pausing outside business
        hours (7pm-7am weekdays + all weekend) saves 75% of compute.
RECOMMENDATION:
  - Pause service at 7pm and resume at 7am weekdays via EventBridge
  - Pause for entire weekend (Friday 7pm to Monday 7am)
  - Use MinSize 0 during business hours for scale-to-zero on idle
ESTIMATED_SAVINGS: $540/month (75% of current compute spend)
MIGRATION_STEPS:
  1. Create EventBridge rule for pause (cron(0 19 ? * MON-FRI *)):
     aws events put-rule --name apprunner-pause-dev \
       --schedule-expression "cron(0 19 ? * MON-FRI *)"
     aws events put-targets --rule apprunner-pause-dev \
       --targets '{"Id":"1","Arn":"<pause-lambda-arn>"}'
  2. Create EventBridge rule for resume (cron(0 7 ? * MON-FRI *)):
     aws events put-rule --name apprunner-resume-dev \
       --schedule-expression "cron(0 7 ? * MON-FRI *)"
     aws events put-targets --rule apprunner-resume-dev \
       --targets '{"Id":"1","Arn":"<resume-lambda-arn>"}'
  3. Set MinSize to 0 during business hours:
     aws apprunner create-auto-scaling-configuration \
       --auto-scaling-configuration-name dev-asg-min0 \
       --min-size 0 --max-size 5 --concurrency 50
CURRENT_MONTHLY_COST: $720/month
PROJECTED_MONTHLY_COST: $180/month
TRAFFIC_PATTERN: intermittent (only used during business hours)
RISK: LOW
NOTES:
  - Pausing the service removes the endpoint. Developers must wait for
    resume (~30-60s) before accessing the service.
  - Consider a Slack bot or CLI alias for manual pause/resume on demand.
```

---

## Worked example — already optimal (OPTIMIZED) (moved from SKILL.md)

```text
TARGET: prod-web-service (region: us-east-1)
VERDICT: OPTIMIZED
REASON: All optimization dimensions are within target. Concurrency 80
        matches observed peak (72 per instance). MinSize 1 matches
        steady-state. CPU 45%, memory 38%. No VPC egress. Health check
        interval 10s is appropriate.
RECOMMENDATION: (none — service is optimized)
ESTIMATED_SAVINGS: $0/month
CURRENT_MONTHLY_COST: $850/month
PROJECTED_MONTHLY_COST: $850/month
TRAFFIC_PATTERN: static (consistent 24/7)
RISK: N/A
NOTES:
  - Re-evaluate quarterly or when traffic pattern changes.
  - Monitor for CPU > 70% sustained — would indicate concurrency is
    too high or instance type needs upgrading.
  - Consider cost-per-request benchmarking against ECS/Fargate if
    monthly cost exceeds $2,000.
```
