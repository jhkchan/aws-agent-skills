# Eval prompt: cutover-weighted-phase-1-ready

Plan the weighted DNS cutover Phase 1 (5% ALB / 95% CLB) and emit the
standard VERDICT block.

Operation: cutover-dns
CLB name: prod-web-clb
ALB name: prod-web-alb
Region: us-east-1
Hosted zone: Z111 (app.example.com currently aliases CLB)

```json
{
  "ALB": {
    "State": "active",
    "DNSName": "dualstack.prod-web-alb-456.us-east-1.elb.amazonaws.com"
  },
  "CLB": {
    "DNSName": "dualstack.prod-web-clb-123.us-east-1.elb.amazonaws.com"
  },
  "describe-target-health": "3/3 targets State: healthy in tg-web-8080",
  "Canary": "curl https://prod-web-alb-456.../healthz returns 200",
  "CloudWatch baseline": {"RequestCount": 5000, "5xx": 0},
  "Phase": "1 (canary) — target 5% ALB / 95% CLB"
}
```
