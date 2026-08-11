# Eval prompt: single-region-nlb-client-ip-preserve

Design a deployment plan for a Global Accelerator. Emit the standard
VERDICT block.

Requirements:

- Accelerator name: prod-ga-nlb-preserve-ip
- IP source: Amazon pool
- IP version: IPv4
- Listener: TCP 443, client affinity NONE
- Endpoint group: region us-east-1, traffic dial 100
  Endpoint: NLB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/net/prod-nlb/abc
    (state=active), weight 256, PreserveClientIpEnabled: true
- Origin security group: already updated to allow client CIDRs
  (0.0.0.0/0 for now, will be tightened later)
- Health check: TCP port 443 interval 10s threshold 3
- Flow logs: CloudWatch Logs group
  /aws/globalaccelerator/prod-ga-nlb-preserve-ip (service-linked
  role AWSServiceRoleForGlobalAccelerator has logs:CreateLogStream
  and logs:PutLogEvents on the group ARN)

Existing-account context: the workload is a gaming backend that
reads the L4 source IP for IP-based rate limiting. The NLB target
group has been validated as healthy. The CloudWatch log group was
created last week and the service-linked role policy was verified
via iam:get-role.
