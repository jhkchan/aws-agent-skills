# Eval prompt: clb-to-alb-migration-savings

Optimise the following Elastic Load Balancer for cost. Walk all
optimization dimensions and emit the standard optimization block
(TARGET, VERDICT, REASON, RECOMMENDATION, ESTIMATED_SAVINGS,
ACTION_STEPS).

## Scenario

A Classic Load Balancer (CLB) has been serving HTTP/HTTPS traffic for
3 years. The team wants to evaluate migration to an ALB for cost and
feature benefits.

## Known facts

- CLB name: `legacy-web-clb`
- Region: us-east-1, VPC: vpc-prod
- Created: 3 years ago
- Listeners: HTTP:80 and HTTPS:443
- Backend instances: 4 x m5.large (EC2, running nginx)
- Traffic: ~5M requests/day, ~2 TB/month processed
- Cost Explorer: $34.25/month
  ($18.25 base + $16.00 for 2 TB at $0.008/GB)
- The application currently handles path-based routing in nginx
  (not at the load balancer level)
- SSL termination: CLB uses a single ACM certificate (no SNI support)
- No ALBs or NLBs exist in the account yet
- The team wants path-based routing at the load balancer layer and
  SNI for multiple domains

## Symptom

The team wants to reduce the CLB cost and gain ALB features (path
routing, SNI, better metrics, LCU-based pricing).
