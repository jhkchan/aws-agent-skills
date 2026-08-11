# Eval: multi-region-active-passive

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — two endpoint groups, us-east-1 primary (dial 1.0), us-west-2 DR (dial 0.0), flow logs, failover

## Prompt

Create a Global Accelerator with two endpoint groups for
active-passive failover. Primary: us-east-1 with traffic dial
1.0, ALB endpoint
arn:aws:elasticloadbalancing:us-east-1:123456789012:loadbalancer/app/prod-alb-east/abc123.
DR: us-west-2 with traffic dial 0.0, ALB endpoint
arn:aws:elasticloadbalancing:us-west-2:123456789012:loadbalancer/app/prod-alb-west/def456.
Listener TCP port 443. Health check HTTPS /health port 443.
Enable flow logs to CloudWatch log group
/aws/globalaccelerator/prod. Tags: Environment=production,
Topology=active-passive.
