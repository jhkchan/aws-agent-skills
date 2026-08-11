# Eval prompt: verify-cutover-completed

Verify the CLB-to-ALB migration is complete (24 hours after 100% shift)
and emit the standard VERDICT block (post-verification form).

Operation: verify-cutover
CLB name: prod-web-clb (still provisioned for rollback)
ALB name: prod-web-alb
Region: us-east-1

```json
{
  "Route53 weights": {"ALB": 100, "CLB": 0},
  "set 24 hours ago": true,
  "describe-target-health": "3/3 targets State: healthy",
  "CloudWatch last 60 min": {
    "HTTPCode_Target_5XX_Count": 0,
    "CLB baseline 5xx": "0-2/min",
    "TargetResponseTime p99": "85ms",
    "CLB baseline p99": "90ms"
  },
  "ALB access logs": "target_status_code 2xx for 100% of /api/* requests",
  "client-reported errors": "none"
}
```
