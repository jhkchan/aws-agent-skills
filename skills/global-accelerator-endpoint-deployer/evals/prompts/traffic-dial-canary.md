# Eval: traffic-dial-canary

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — canary with traffic dial 0.9 us-east-1 and 0.1 eu-west-1, NLB endpoints

## Prompt

Create a Global Accelerator with a traffic dial canary
configuration. Endpoint group 1: us-east-1 with traffic dial
0.9, NLB endpoint
arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/net/prod-nlb/aaa111.
Endpoint group 2: eu-west-1 with traffic dial 0.1, NLB endpoint
arn:aws:elasticloadbalancing:eu-west-1:123456789012:loadbalancer/net/prod-nlb-eu/bbb222.
Listener TCP port 443. Health check TCP port 443, interval 10.
Tags: Environment=staging, Strategy=canary.
