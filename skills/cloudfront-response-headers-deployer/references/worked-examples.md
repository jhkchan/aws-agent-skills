# Worked examples — CloudFront Response Headers Deployer

Secondary worked examples and output-format specs moved out of SKILL.md
for progressive disclosure. Load on demand.

## Output format (per operation) — full spec

Every operation MUST emit a single block using these literal labels, in this
order. Do NOT substitute markdown headings or camelCase variants —
assertion-based evals and downstream provisioning parse the literal labels
`DISTRIBUTION_ID:`, `VERDICT:`, `CHECKLIST:`, `GAP:`, `IAC_TEMPLATE:`,
`MANUAL_GAPS:`, `NOTES:`.

```text
DISTRIBUTION_ID: <id> | "(new — will be created)"
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [x] Target distribution: exists + Deployed state (or greenfield)
  [x] Target behavior: DefaultCacheBehavior | PathPattern <pattern>
  [x] Response headers policy:
        - Security headers: CSP <value>, HSTS <max-age + includeSubDomains + preload>, X-Frame-Options <DENY|SAMEORIGIN>, X-Content-Type-Options nosniff, Referrer-Policy <value>, Permissions-Policy <value>
        - CORS: origins <list|*>, methods <list>, headers <list>, credentials <true|false>, max-age <sec>
        - Custom headers: <name=value list>
        - Removal headers: <list> (NEVER Server or Via)
  [x] Policy origin: managed <ID + name> | custom
  [x] Override: true on every security header (else origin values win)
  [x] Attach plan: update-distribution with current ETag
GAP: <if PREREQUISITES_MISSING, the specific gap and remediation>
IAC_TEMPLATE: <inline CloudFormation / Terraform; "(held in draft)" if blocked>
MANUAL_GAPS:
  - GAP: <gap>
    REMEDIATION: <exact CLI / IaC snippet>
    REASON: <why this cannot be automated>
NOTES: <managed policy version, attach-vs-embed, invalidation guidance, deploy state>
```

### Worked example — PREREQUISITES_MISSING (wildcard CORS + credentials)

```text
DISTRIBUTION_ID: E1BCDEFGHIJ2EXAMPLE
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [x] Target distribution: E1BCDEFGHIJ2EXAMPLE exists in Deployed state
  [x] Target behavior: DefaultCacheBehavior
  [ ] Response headers policy: CORS config uses Access-Control-Allow-Origin: "*" with AllowCredentials: true (BROWSERS REJECT THIS COMBINATION)
  [x] Policy origin: custom
  [x] Override: true on every header
  [x] Attach plan: get-distribution-config → update-distribution with ETag
GAP: CORS policy combines wildcard origin "*" with AllowCredentials: true. CloudFront will serve the headers; the browser rejects the response and logs a CORS error in the console. The CloudFront API does not validate this combination — the browser does.
IAC_TEMPLATE: (held in draft — apply after closing the gap below)
MANUAL_GAPS:
  - GAP: CORS policy combines wildcard origin with credentials.
    REMEDIATION:
      Change AccessControlAllowOrigins from ["*"] to a specific origin list:
      aws cloudfront update-response-headers-policy --id <policy-id> \
        --response-headers-policy-config file://fixed-cors.json --if-match <etag>
      where fixed-cors.json sets AccessControlAllowOrigins.Items to ["https://app.example.com"].
    REASON: Browsers reject Access-Control-Allow-Origin: * with credentials. CloudFront API does not validate; the browser does.
NOTES:
  - Use specific origins for credentialed CORS, OR set AllowCredentials: false.
  - For dynamic origin reflection (echo the requesting Origin header), use Lambda@Edge or CloudFront Functions — response headers policies do not support reflection.
```
