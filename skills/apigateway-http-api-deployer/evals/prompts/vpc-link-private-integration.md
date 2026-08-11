# Eval prompt: vpc-link-private-integration

Design a deployment plan for an HTTP API with a private backend
integration via VPC link. Emit the standard VERDICT block.

Requirements:

- API type: HTTP (v2)
- Endpoint type: REGIONAL (us-east-1)
- Routes and authorization:
  - GET /internal/health [NONE]
  - GET /internal/orders [AWS_IAM]
  - POST /internal/orders [AWS_IAM]
- Integration: HTTP_PROXY via VPC link to internal NLB
  `prod-internal-nlb` with HTTPS listener on 443
- NLB DNS: `prod-internal-nlb-abc123.elb.us-east-1.amazonaws.com`
- VPC link: subnets `subnet-aaa`, `subnet-bbb` (two AZs), security
  group `sg-egress-nlb` allowing egress 443 to the NLB
- Authorization: AWS_IAM (service-to-service, sigv4)
- Access logging: JSON to CloudWatch
  `/aws/apigateway/prod-internal-http`
- WAF: REGIONAL with CommonRuleSet + KnownBadInputsRuleSet
- Auto-deploy: true on `$default` stage

Existing-account context: the NLB exists with target groups in two
AZs pointing to an ECS service. The VPC link has NOT been created yet
— the operator expects the skill to emit `create-vpc-link` as part of
the deploy commands. Caller services in the same account will sign
requests with sigv4 using IAM roles already configured.
