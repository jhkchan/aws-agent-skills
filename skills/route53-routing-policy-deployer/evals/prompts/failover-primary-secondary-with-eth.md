# Eval: failover-primary-secondary-with-eth

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — failover with ETH explicitly true on ALB alias

## Prompt

Provision DR failover routing in zone Z4DABCDEFGHIJK (example.com)
for "dr.example.com" type A. PRIMARY: alias to ALB
"my-alb-12345.us-east-1.elb.amazonaws.com" (canonical hosted zone
Z35SXDOTRQ7X7K), EvaluateTargetHealth true. SECONDARY: static IP
10.99.0.20 in us-west-2. PRIMARY must reference its own health
check on HTTPS /healthz. TTL 60s.
