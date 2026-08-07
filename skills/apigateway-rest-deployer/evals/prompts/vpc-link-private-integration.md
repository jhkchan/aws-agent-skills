# Eval prompt: vpc-link-private-integration

Design a deployment plan for a REST API with private backend integration
via VPC Link. Emit the standard VERDICT block (API_SPEC, VERDICT,
ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- API type: REST (v1)
- Endpoint type: REGIONAL (us-east-1)
- Resources and methods:
  - /orders [GET (list), POST (create)]
  - /orders/{id} [GET (read)]
- Integration: HTTP_PROXY via VPC Link
- VPC Link target: NLB
  `arn:aws:elasticloadbalancing:us-east-1:111111111111:loadbalancer/net/prod-nlb/abc123def456`
- NLB listener: TCP 443 (TLS termination at ECS service behind NLB;
  NLB is TCP pass-through)
- NLB target groups: span us-east-1a, us-east-1b, us-east-1c (ECS tasks
  on Fargate in private subnets)
- Authorization: AWS_IAM (sigv4 — service-to-service access)
- Usage plan: not required (internal B2B; IAM auth gates access)
- Stage throttling: 5000 rps / 2000 burst
- WAF: REGIONAL scope in us-east-1, CommonRuleSet +
  KnownBadInputsRuleSet + rate-based (5000 req/5min per IP)
- Access logging: JSON to CloudWatch with $context.requestId, status,
  authorizerError, sourceIp, responseLatency
- Custom domain: internal-api.example.com with base path `v1`
- ACM cert: arn:aws:acm:us-east-1:111111111111:certificate/internal-cert
  (REGIONAL, covers internal-api.example.com)

Existing-account context: the NLB exists and is ACTIVE. The ECS service
behind the NLB is healthy. The NLB security group allows inbound 443
from the VPC Link's source ENIs (will be configured after VPC Link
creation returns the ENI IDs).
