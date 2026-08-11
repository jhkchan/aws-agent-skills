# Eval prompt: mixed-endpoint-types-blocked

Design a deployment plan for a Global Accelerator. Emit the standard
VERDICT block.

Requirements:

- Accelerator name: prod-ga-mixed
- IP source: Amazon pool
- Listener: TCP 443
- Endpoint group: region us-east-1, traffic dial 100
  Endpoints (both in the same group):
  - ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-alb/abc (state=active), weight 128
  - NLB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/net/prod-nlb/def (state=active), weight 128
- Health check: HTTPS / port 443

Existing-account context: the user wants to load-balance across the
ALB (serving the web frontend) and the NLB (serving a TCP backend) in
the same endpoint group, treating them as interchangeable targets.
The ALB and NLB are both in us-east-1 and both healthy.
