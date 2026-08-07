# Eval prompt: missing-acm-domain-cert

Design a deployment plan for a REST API. Emit the standard VERDICT block
(API_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- API type: REST (v1)
- Endpoint type: REGIONAL (us-east-1)
- Resources and methods:
  - /health [GET] — returns 200 OK for load balancer health checks
- Integration: AWS_PROXY to Lambda function `health-check-handler`
- Authorization: NONE (public health check endpoint — intentionally open)
- Usage plan: not required (public endpoint)
- Stage throttling: 100 rps / 50 burst (low-volume health check)
- Access logging: JSON to CloudWatch with $context.requestId, status,
  sourceIp
- Custom domain: api.example.com with base path mapping `v1`

The user did NOT specify the ACM certificate ARN for the custom domain
api.example.com. They expect the skill to flag this as a missing
prerequisite rather than silently proceeding without TLS configuration.

Note: an ACM certificate is REQUIRED for a custom domain mapping. The
skill must not silently fall back to the default
`*.execute-api.<region>.amazonaws.com` endpoint when a custom domain was
explicitly requested.
