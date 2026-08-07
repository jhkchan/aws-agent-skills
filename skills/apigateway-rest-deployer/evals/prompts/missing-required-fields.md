# Eval prompt: missing-required-fields

Design a deployment plan for an API. Emit the standard VERDICT block
(API_SPEC, VERDICT, ARCHITECTURE, CHECKLIST, FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Endpoint type: REGIONAL (us-east-1)
- Resources: /items [GET]
- Authorization: AWS_IAM

The user did NOT specify:

- API type (REST v1 or HTTP v2 — these have materially different feature
  sets and cost profiles)
- Integration type (AWS_PROXY to Lambda? HTTP_PROXY to ALB? VPC_LINK to
  NLB? MOCK? Direct AWS service call?)
- The backend that serves /items [GET]
- Whether usage plans / API keys are needed for per-consumer throttling
- Whether WAF should be associated
- Whether access logging is required
- Whether a custom domain is needed
- Stage throttling requirements

The user expects the skill to flag the missing prerequisites rather
than silently picking defaults. Without an integration type and backend,
the deployment plan is meaningless — the API would have a route to
nowhere.
