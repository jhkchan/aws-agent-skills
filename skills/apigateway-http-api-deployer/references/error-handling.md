# Error handling - API Gateway HTTP API Deployer

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

**Ordering principle:** authorization first (active exposure if wrong),
then routes and greedy catch-alls (exposure surface), then CORS
(browser UX), then observability (logging), then optimization (WAF,
custom domain, throttle).

- **JWT issuer unreachable or malformed:** resolve the issuer URL via
  `curl <issuer>/.well-known/openid-configuration`; if Cognito, ensure
  trailing slash; verify audience matches the app client id (Cognito)
  or the `aud` claim (third-party OIDC); re-issue `create-authorizer`.
- **VPC link to ALB:** create an NLB that targets the ALB (or the
  ALB's targets directly); verify target groups span multiple AZs;
  create the VPC link; update the HTTP_PROXY integration with
  `connection-type: VPC_LINK` and `connection-id`.
- **HTTP API chosen but REST features required:** confirm whether usage
  plans, mapping templates, resource policies, EDGE, or Lambda
  authorizers are genuinely required. If yes, switch to REST API (no
  in-place conversion — re-create the API). If no, proceed with HTTP
  API and document the trade-off (e.g., per-consumer throttling via
  WAF instead of usage plans).
