# Diagnostic Commands (load on demand) — Cognito User Pool Deployer

Live-account pre-flight command listing (with pagination note), moved verbatim from SKILL.md. Run before classification.


---

## Live-account pre-flight (user pool metadata gate) (moved from SKILL.md)

**Pagination:** `list-user-pools` returns at most 20 pools per page (via
`--max-items`). Use `--starting-token` to drain.

**Live-account pre-flight (skip if offline plan audit):**
1. `aws cognito-idp list-user-pools --max-results 60` — confirm the pool
   name does not collide (for create) or matches (for update).
2. `aws cognito-idp describe-user-pool --user-pool-id <id>` — capture
   the full pool config for snapshot/diff.
3. `aws cognito-idp list-user-pool-clients --user-pool-id <id>` — check
   for client name conflicts.
4. `aws iam get-role --role-name <SnsCallerRoleName>` — for SMS MFA,
   verify the SNS caller role exists.
5. `aws lambda get-function --function-name <fn>` — for each Lambda
   trigger, verify the function exists and the pool principal can
   invoke it.
6. `aws acm describe-certificate --certificate-arn <arn>` — for custom
   domain, verify the cert is in us-east-1 and `ISSUED`.
7. `aws cognito-idp describe-user-pool-domain --domain <domain>` — for
   domain ops, confirm the domain is not already taken.
