# Worked Examples (load on demand) — CloudWatch RUM Deployer

Secondary worked example moved verbatim from SKILL.md. The primary READY_TO_DEPLOY worked example remains in SKILL.md.


---

## Perfect example — PREREQUISITES_MISSING (moved from SKILL.md)

```text
RUM_APP: checkout-web
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓]      App monitor name — checkout-web-prod (created in us-east-1)
  [✓]      Domain (AllowedOrigins) — https://checkout.example.com
  [✓]      Sampling rate — current: 1.0   recommended: 1.0
  [✗]      Cookie domain — current: .com   recommended: .example.com (REJECT TLD; cookie leaks across all .com sites)
  [✓]      Telemetries — current: errors, performance, http   recommended: errors, performance, http
  [✗]      Guest role — MISSING: no IAM role with rum:PutRumEvents found (run `aws iam list-roles --query 'Roles[?contains(RoleName,`rum`)]'`)
  [INPUT NEEDED] Identity pool — operator must provide Cognito unauth pool ID, or skill must create one
  [✗]      X-Ray tracing — current: enableXRay=true   BLOCKED: server sampling rule FixedRate=0.0; raise to >=0.01 (aws xray update-sampling-rule)
  [✗]      Application Signals correlation — BLOCKED on X-Ray sampling rule above
  [✗]      XSS sanitization — JS_SNIPPET withheld: SRI hash missing until SDK version pinned
  [✗]      Custom metrics — BLOCKED: no put-metrics-destination configured
  [✗]      CloudWatch metrics emitted — none yet (deployment not live)
JS_SNIPPET: (withheld — resolve the 4 BLOCKED rows above, then re-invoke)
VERIFICATION_COMMANDS:
  aws iam list-roles --query 'Roles[?contains(RoleName,`rum`)]' --output text
  aws xray get-sampling-rules --region us-east-1
  aws cognito-identity list-identity-pools --max-results 10 --region us-east-1
  aws rum get-app-monitor --name checkout-web-prod --region us-east-1
```
