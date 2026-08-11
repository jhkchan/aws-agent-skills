# Eval prompt: byoip-cidr-not-provisioned

Design a deployment plan for a Global Accelerator. Emit the standard
VERDICT block.

Requirements:

- Accelerator name: prod-ga-byoip
- IP source: BYOIP 203.0.113.0/24
- Listener: TCP 443
- Endpoint group: region us-east-1, traffic dial 100
  Endpoint: ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-use1/abc (state=active), weight 128
- Health check: HTTPS / port 443 interval 30s

Existing-account context: `aws ec2 describe-byoip-cidrs` returns the
CIDR 203.0.113.0/24 in state `PENDING_PROVISIONING`. The ROA was
published with ARIN two weeks ago, but Route 53 provisioning has not
completed — the signed message was submitted yesterday and AWS is
still validating it. The user expects to advertise this CIDR through
Global Accelerator today as part of a launch.
