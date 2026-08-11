# Eval prompt: multi-region-alb-active-active

Design a deployment plan for a production Global Accelerator. Emit
the standard VERDICT block (ACCELERATOR_SPEC, VERDICT, ARCHITECTURE,
CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Accelerator name: prod-ga-multi-region
- IP source: Amazon pool (no BYOIP)
- IP version: IPv4
- Listener: TCP 443, client affinity NONE (stateless HTTPS)
- Endpoint group 1: region us-east-1, traffic dial 100
  Endpoint: ALB arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/app/prod-use1/abc (state=active), weight 128
- Endpoint group 2: region eu-west-1, traffic dial 100
  Endpoint: ALB arn:aws:elasticloadbalancing:eu-west-1:111111111111:loadbalancer/app/prod-euw1/def (state=active), weight 128
- Health check: HTTPS path / port 443 interval 30s threshold 3
- Flow logs: S3 bucket prod-ga-flowlogs (bucket policy grants
  s3:PutObject to flowlogs.globalaccelerator.amazonaws.com)
- Cross-account: no
- Custom routing: no

Existing-account context: two existing accelerators use Amazon-pool
IPs without issue. The two ALBs were validated as state=active via
describe-load-balancers. The S3 flow log bucket policy was updated
yesterday to grant s3:PutObject to the GA logging principal. IAM
principal holds globalaccelerator:CreateAccelerator, CreateListener,
CreateEndpointGroup, AddEndpoints.
