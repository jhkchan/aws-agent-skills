# Eval: weighted-canary-traffic-split

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — weighted forwarding to canary TG (20%) and stable TG (80%), weights are relative not percentage, health checks on both target groups

## Prompt

Configure traffic splitting on Lattice service payments-svc
(svc-bbb222) listener lstn-ccc333. Create canary target group
tg-canary (INSTANCE, port 8080, VPC vpc-aaa11122, health path
/health). Rule for /api/* path: route 20% to tg-canary and 80%
to tg-stable (tgc-stable). us-east-1.
