# Eval prompt: cross-account-endpoint-shared

Design a deployment plan for a cross-account Global Accelerator. Emit
the standard VERDICT block.

Requirements:

- Accelerator name: prod-ga-cross-account (in network account 111111111111)
- IP source: Amazon pool
- Listener: TCP 443, client affinity NONE
- Endpoint group: region us-east-1, traffic dial 100
  Endpoint: ALB arn:aws:elasticloadbalancing:us-east-1:222222222222:loadbalancer/app/prod-alb-workload/abc
    (state=active, in workload account 222222222222), weight 128
- RAM resource share
  arn:aws:ram:us-east-1:222222222222:resource-share/prod-alb-share/xyz
  is ACTIVE in both accounts (the network account 111111111111 has
  accepted the invitation, verified via get-resource-share-invitations)
- Health check: HTTPS / port 443 interval 30s threshold 3
- Flow logs: S3 bucket prod-ga-flowlogs in account 111111111111
  (bucket policy grants s3:PutObject to flowlogs.globalaccelerator.amazonaws.com)

Existing-account context: the network team owns the accelerator and
flow log bucket; the workload team owns the ALB and target groups in
account 222222222222. The RAM share was created last week and accepted
by the network account yesterday.
