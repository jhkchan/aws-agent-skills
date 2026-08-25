# Advanced Patterns — Secrets Manager Rotation Operator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Mindset

**One-line takeaway:** `RotationEnabled: true` is a claim, not proof. The
credential is only rotating if `LastRotatedDate` advances on schedule and
no version is stranded in AWSPENDING. Driven by three Secrets Manager
realities:

- **Rotation is a four-link chain.** Config points to a Lambda; the Lambda
  runs with an execution role; the role needs KMS + network + service
  permissions; the target resource must accept the new credential. A single
  broken link makes the entire chain fail silently — the secret appears
  "managed" on dashboards while the credential is static in production.
- **A stuck AWSPENDING version is a live incident, not a transient state.**
  If `setSecret` completed before the failure, the target already has the
  new password but the secret's `AWSCURRENT` stage still points to the old
  version. Applications read the old password, the database rejects them —
  authentication failures cascade across the workload.
- **Cross-account rotation Lambdas require a resource-based policy grant.**
  Secrets Manager invokes the Lambda as the `secretsmanager.amazonaws.com`
  service principal. The Lambda's resource-based policy must explicitly
  allow that principal to `lambda:InvokeFunction`, and (for cross-account)
  the secret's resource-based policy must allow the Lambda's account to
  `secretsmanager:GetSecretValue` / `PutSecretValue`.

## Step 0: Expert knowledge — non-obvious Secrets Manager behaviors

These behaviors are easy to misjudge without operational rotation
experience. Each changes a plan if ignored:

- **The rotation cycle is four Lambda steps, not one.** Secrets Manager
  invokes the rotation Lambda four times per rotation: `createSecret`
  (generate a new value, store it as `AWSPENDING`), `setSecret` (apply the
  `AWSPENDING` credential to the target service), `testSecret` (log in
  with the new credential to verify), and `finishSecret` (move
  `AWSCURRENT` to the new version). A failure at any step leaves a
  different footprint — see the failure-mode table in Step 1.

- **`AWSCURRENT` moves atomically in `finishSecret`, not before.** Until
  `finishSecret` succeeds, applications read the OLD credential even if
  `setSecret` already changed the database password. This is why a stuck
  `AWSPENDING` causes authentication storms: the DB has the new password,
  the secret still serves the old one.

- **`RotationRules.ScheduleExpression` overrides `AutomaticallyAfterDays`.**
  When both are set, the cron expression wins. When auditing freshness or
  planning a schedule change, always check `ScheduleExpression` first;
  computing the interval off `AutomaticallyAfterDays` alone produces wrong
  STALE classifications.

- **Lambda timeout default (3s) is too short for database rotation.** The
  `setSecret` step must open a TCP connection, authenticate with the
  `AWSCURRENT` credential, and run `ALTER USER` / `ALTER ROLE SET
  PASSWORD` — on a slow or busy DB this takes 5-15 seconds. Set timeout to
  minimum 30 seconds; 60 seconds for Aurora clusters with many instances.

- **The Lambda's VPC subnets must route to the DB.** A common
  misconfiguration is attaching the Lambda to private subnets with a NAT
  gateway — the DB's security group only accepts connections from the
  app's SG, so the Lambda's ENI is denied. Either attach the Lambda to the
  same subnets as the application, or add an ingress rule on the DB SG for
  the Lambda's security group on the DB port.

- **Cross-account rotation requires BOTH the Lambda resource-based policy
  AND the secret resource-based policy.** Secrets Manager invokes the
  Lambda in the Lambda's account; the Lambda then calls `GetSecretValue`
  on the secret in the secret-owning account. The Lambda's resource policy
  must allow `secretsmanager.amazonaws.com` (or the secret's account) to
  invoke it; the secret's resource policy must allow the Lambda's role ARN
  to `secretsmanager:GetSecretValue`, `PutSecretValue`,
  `UpdateSecretVersionStage`.

- **RDS managed secrets (created by RDS) use `AWS::RDS::DBInstance`
  templates.** When `OwningService: rds`, the secret is bound to an RDS
  instance. Use the AWS-managed rotation template for the engine (MySQL,
  PostgreSQL, etc.); a custom Lambda will conflict with RDS's secret-
  binding lifecycle.

- **Master vs. rotating-user rotation.** RDS MySQL/PostgreSQL templates
  support two modes: "single user" (rotates the master credential by
  connecting as the master and running `ALTER USER ... PASSWORD`),
  "multi user" (creates a new user and appends it to the secret, avoiding
  the master-only single-writer limitation). Choose multi-user if
  applications tolerate a username change; otherwise single-user.

- **`HostedRotationLambda` (2024+) is AWS-managed.** When the rotation
  Lambda's ARN matches the hosted pattern (or the secret was created via
  the console's "rotate using AWS-managed Lambda" option), skip the
  execution-role checks — AWS owns the function and its permissions. The
  failure surface narrows to: scheduling, target reachability, and
  credential match.

- **Reserved concurrency = 0 is a stealth kill switch.** The Lambda
  appears `Active` in every status check, but every invocation is
  throttled. CloudWatch shows a `Throttles` metric spike, not an error
  log. Always check `get-function-concurrency` separately.

- **`kms:Decrypt` is required even for `GetSecretValue`.** The Lambda
  calls `GetSecretValue` to read `AWSCURRENT` before `setSecret`. If the
  key policy denies the Lambda role, the API call succeeds (the ARN is
  readable) but the ciphertext is undecryptable — the error surfaces as
  `DecryptionFailureException` in the Lambda logs, not in the Secrets
  Manager API response.

- **Manual `ALTER USER` outside rotation breaks the next rotation.** If a
  human changes the DB password directly, the Lambda's `setSecret` step
  authenticates with the `AWSCURRENT` credential and fails — the stored
  password no longer matches. The fix is to update the secret value to
  match the manual password, then trigger a rotation to re-sync.

- **Replica secrets are read-only.** Secrets Manager returns
  `InvalidParameterException` when you try to enable rotation on a
  replica. Rotation runs against the primary in the primary region; the
  rotated value syncs to replicas in 1-5 seconds.

- **ScheduleExpression uses EventBridge cron/rate syntax.** `"rate(30 days)"`
  or `"cron(0 9 ? * MON *)"` (every Monday 09:00). The `?` in the day-of-
  month field is required when day-of-week is specified. Cron expressions
  use UTC.

- **ForceOverwriteReplicaSecret is for regional-failover DR only.** When
  the primary region is down, you can promote a replica and force-overwrite
  it. This breaks the normal primary/replica sync and requires manual
  reconciliation when the primary returns. Treat as a DR procedure, not a
  routine rotation.

- **`SecretsManagerRotation` managed policy is over-broad.** It grants
  `secretsmanager:*` on `*` — the Lambda can read or modify any secret in
  the account. For least-privilege, scope a custom policy to the specific
  secret ARN with the `-??????` suffix (Secrets Manager auto-appends a
  random 6-char string).

## Recent AWS features (2024-2026)

- **HostedRotationLambda (2024-2025):** Secrets Manager can create and
  manage the rotation Lambda for you (no customer-owned function). The
  rotation Lambda ARN points to an AWS-managed function; the execution
  role and permissions are maintained by AWS. When the ARN matches the
  hosted pattern, skip the execution-role pre-checks — the failure
  surface narrows to scheduling, target reachability, and credential
  match.

- **Cross-region secret replication GA (2024):** Secrets can be replicated
  across regions for DR. The primary holds the rotation config; replicas
  are read-only and inherit rotated values in 1-5 seconds. Use
  `ForceOverwriteReplicaSecret` only during regional-failover DR.

- **Partial wildcard for resource-based policies (2024-2025):** Secrets
  Manager now supports partial wildcard matching in resource-based
  policy `Resource` elements (e.g.,
  `arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/*`). This
  simplifies cross-account access grants for fleets of related secrets.
  Verify the wildcard does not inadvertently grant access to unrelated
  secrets in the same prefix.

- **ScheduleExpression (2023-2024) GA:** Cron-style rotation schedules
  (`"rate(7 days)"`, `"cron(0 9 ? * MON *)"`). When present, overrides
  `AutomaticallyAfterDays`. Use cron for day-of-week or time-of-day
  requirements; use `AutomaticallyAfterDays` for simple intervals.

- **Rotation templates for additional engines (2024-2025):** New managed
  rotation Lambda templates for Amazon MQ, DocumentDB, Neptune, and
  Redshift. Verify the template matches the engine before deploying.

- **Rotation strategy: multi-user for RDS (2024):** The RDS templates
  support single-user (rotates the master) and multi-user (creates a new
  rotating user, avoiding single-writer limitations). Choose multi-user
  for workloads that tolerate username changes.

- **Secrets Manager VPC endpoint policy (2024):** For Lambda-in-VPC
  rotation, a VPC endpoint for Secrets Manager avoids NAT gateway charges
  and improves security. Verify the endpoint policy allows the Lambda
  role to call the required Secrets Manager APIs.

- **CloudTrail data event logging for Secrets Manager (2025):**
  CloudTrail now supports data-event logging for `GetSecretValue` and
  `PutSecretValue`. Enable for compliance audits — management events
  alone do not capture credential reads/writes.

