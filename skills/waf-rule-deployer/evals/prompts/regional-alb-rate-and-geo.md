# Eval: regional-alb-rate-and-geo

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — Regional scope us-west-2, rate-based rule 100/5min per IP on /login, geo-match block RU/KP

## Prompt

Create a Regional Web ACL named api-protection-acl protecting
ALB arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/api-alb/1234567890
in us-west-2. Add a rate-based rule blocking IPs exceeding
100 requests per 5 minutes on /login (priority 100, action
BLOCK). Add a geo-match block for countries RU and KP at
priority 40. Default action ALLOW. Tags: Environment=production,
Service=api.
