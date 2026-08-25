# Error Handling (load on demand) — CloudWatch Synthetics Troubleshooter

Error-handling and remediation detail moved verbatim from SKILL.md. Load on demand.

---

## Remediation guidance by failure type (moved from SKILL.md)

### TIMEOUT
1. Identify the slow step from the canary log (last logged action).
2. Check target endpoint response time independently.
3. If target is slow, escalate to the application team.
4. If script waits for a missing element, update selectors.
5. If VPC networking is constrained, check NAT gateway and route tables.

### AUTH_FAILURE
1. Check Secrets Manager `LastRotatedDate` vs failure start time.
2. Verify canary role can read the secret (`simulate-principal-policy`).
3. Check script for token caching across runs.
4. Verify the test account is not locked or expired.

### VISUAL_MONITORING_MISMATCH
1. Correlate failure start time with UI deployments.
2. Download screenshot and baseline; compare visually.
3. If legitimate UI change, update the baseline.
4. If dynamic content, add ignore regions or increase tolerance.
5. If real break, escalate to the application team.

### RUNTIME_EXCEPTION
1. Identify exception type and line number from the canary log.
2. Correlate with target-side deployments.
3. If DOM changed, update selectors and redeploy.
4. If unhandled promise, add error handling.
5. If post-runtime-upgrade, pin version or fix script.

### TARGET_ENDPOINT_DOWN
1. Verify target unreachable from a different vantage point.
2. Check Route 53, ALB, CloudFront, AWS Health Dashboard.
3. Escalate to application team with canary evidence.

