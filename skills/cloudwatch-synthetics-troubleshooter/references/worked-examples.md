# Worked Examples (load on demand) — CloudWatch Synthetics Troubleshooter

Secondary worked examples moved verbatim from SKILL.md. Load on demand.

---

## Worked example — auth failure from secret rotation (moved from SKILL.md)

### Worked example — auth failure from secret rotation

```text
CANARY: api-health-canary in us-east-1
VERDICT: ROOT_CAUSE_FOUND
ROOT_CAUSE: AUTH_FAILURE — the canary reads an OAuth client secret from
  Secrets Manager. The secret was auto-rotated at 2026-08-09T03:00Z.
  The canary script caches the token in module scope across warm Lambda
  invocations, sending the old secret and producing 401 invalid_client.
FAILURE_TYPE: AUTH_FAILURE
EVIDENCE:
  - Run report: 401 Unauthorized — {"error": "invalid_client"}
  - CloudWatch SuccessPercent: dropped to 0% at 2026-08-09T03:01Z
  - Secrets Manager: LastRotatedDate 2026-08-09T03:00:12Z
  - Canary log: "Using cached token" on subsequent runs
ROOT_CAUSE_CATALOG: #3
REMEDIATION:
  1. Immediate: force a cold start:
      aws lambda update-function-configuration --function-name cwsyn-api-health-canary \
        --environment Variables={FORCE_REFRESH=true}
      aws synthetics start-canary --name api-health-canary
  2. Permanent: modify script to fetch secret on EVERY run:
      const secret = await secretsmanager.getSecretValue(
        {SecretId: process.env.CLIENT_SECRET_ID}).promise();
  3. Monitor SuccessPercent for 10 minutes; expect return to 100%.
```

## Worked example — insufficient context (moved from SKILL.md)

### Worked example — insufficient context

```text
CANARY: unknown
VERDICT: NEED_MORE_INFO
ROOT_CAUSE: UNKNOWN — cannot diagnose without the canary name
FAILURE_TYPE: UNKNOWN
EVIDENCE:
  - Run report: not available
ROOT_CAUSE_CATALOG: #0
MISSING:
  - Canary name + region
  - The run report error string
  - The canary type
  - The CloudWatch SuccessPercent / Duration pattern
```

