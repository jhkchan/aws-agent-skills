# Eval: single-region-alb

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — single endpoint group, ALB endpoint, TCP listener 80/443, client IP preservation, health check HTTPS

## Prompt

Create a Global Accelerator in us-west-2 with two static anycast
IP addresses. Listener TCP ports 80 and 443. Endpoint group in
us-east-1 with traffic dial 1.0. Endpoint: ALB
arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/my-alb/50dc6c495c0c9188
with weight 128. Enable client IP preservation. Health check
HTTPS on /health port 443, interval 10 seconds, threshold 3.
Tags: Environment=production.
