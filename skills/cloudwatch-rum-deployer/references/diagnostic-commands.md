# Diagnostic Commands (load on demand) — CloudWatch RUM Deployer

Telemetry-flow verification commands and pre-flight safety checks moved verbatim from SKILL.md. Load on demand after deployment or before enablement CLIs.


---

## Step 9 — Verify telemetry is flowing (checks + silent-drop causes) (moved from SKILL.md)

Within 1-5 minutes of the first user visiting the page, telemetry
should appear:

```bash
aws cloudwatch list-metrics --namespace AWS/RUM \
  --dimensions Name=ApplicationName,Value=checkout-web-prod

aws logs describe-log-streams \
  --log-group-name /aws/rum/checkout-web-prod \
  --limit 1 --order-by LastEventTime --descending

aws xray get-trace-summaries \
  --start-time $(date -u +%s --date='10 min ago') \
  --end-time $(date -u +%s) \
  --filter-expression 'service.id = "checkout-web-prod"'
```

If metrics do not appear within 15 minutes, the cause is almost
always:
- Domain not in `AllowedOrigins` (silent drop).
- Guest role lacks `rum:PutRumEvents` on the app monitor ARN.
- Browser ad blocker suppressing the RUM CDN script.

---

## Pre-flight safety checks (run before any enablement CLI) (moved from SKILL.md)

- **Confirm RUM is available in the Region:** `aws rum
  list-app-monitors --region <r>` (no error = available).
- **Confirm the guest role:** `aws iam list-attached-role-policies
  --role-name <guest-role>` (must include a policy with
  `rum:PutRumEvents` on the planned app monitor ARN).
- **Confirm X-Ray sampling default exists (if X-Ray enabled):**
  `aws xray get-sampling-rules` (must list a `Default` rule with
  `FixedRate > 0`).
- **Confirm Application Signals is enabled on the server (if
  client correlation desired):** `aws application-signals
  list-services` (server workload appears).
- **Confirm the domain allow-list:** every origin (scheme + host
  + port) the web app is served from must be in `AllowedOrigins`.
- **Confirm the cookie domain** matches the deployment's parent
  domain or the exact host.
