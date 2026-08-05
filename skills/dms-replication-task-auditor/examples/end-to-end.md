# End-to-end usage scenario: dms-replication-task-auditor

A walkthrough showing the skill auditing a DMS replication task that has a
plaintext source endpoint (NO_TLS), a public replication instance (CONFIG_GAP),
and disabled task logging (NO_LOGGING), demonstrating priority-based verdict
aggregation and the expert DMS knowledge that separates the skill from a
generic assistant.

## Input (user prompt)

> Review this DMS replication task before we start the production migration
> cutover. It replicates our production MySQL database to a PostgreSQL
> replica for the new application stack.

```
Task ARN: arn:aws:dms:us-east-1:111111111111:task:prod-mysql-to-pg-cdc
MigrationType: full-load-and-cdc
Status: running

Source endpoint (MySQL):
  EngineName: mysql
  ServerName: prod-mysql.internal.example.com
  Port: 3306
  SslMode: none
  KmsKeyId: (not set)

Target endpoint (PostgreSQL):
  EngineName: postgres
  ServerName: replica-pg.internal.example.com
  Port: 5432
  SslMode: verify-full
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/target-key

Replication instance:
  ReplicationInstanceClass: dms.t3.medium
  MultiAZ: false
  PubliclyAccessible: true
  KmsKeyId: arn:aws:kms:us-east-1:111111111111:key/instance-key

TaskSettings (JSON string):
  {"Logging":{"EnableLogging":false},"ValidationSettings":{"EnableValidation":false},"DeletionProtection":false}
```

## Skill output

```text
TASK: arn:aws:dms:us-east-1:111111111111:task:prod-mysql-to-pg-cdc
VERDICT: NO_TLS
REASON: Source endpoint (MySQL) has SslMode none — all replicated data flows
in plaintext between source and target, including credentials, PII, and
financial records (Step 1). Additionally, logging is disabled (NO_LOGGING)
and the replication instance is publicly accessible with no Multi-AZ —
multiple compounding failures.
FINDINGS:
  - [NO_TLS] Source endpoint SslMode is none — plaintext data in transit (Step 1)
  - [NO_TLS] Source endpoint missing KmsKeyId — endpoint config unencrypted (Step 4)
  - [NO_LOGGING] EnableLogging is false — task failures are invisible, CloudWatch
    metrics still show green (Step 2)
  - [CONFIG_GAP] Replication instance PubliclyAccessible is true — internet-reachable
    credential store (Step 3)
  - [CONFIG_GAP] MultiAZ is false on a full-load-and-cdc task — CDC position lost
    on instance failure (Step 3)
  - [CONFIG_GAP] ReplicationInstanceClass dms.t3.medium is burstable — CPU credits
    deplete under sustained CDC (Step 3)
  - [CONFIG_GAP] ValidationSettings.EnableValidation is false — no data-integrity check (Step 4)
  - [CONFIG_GAP] DeletionProtection is false — task can be deleted via CLI (Step 4)
  - [OK] Target endpoint SslMode is verify-full (Step 1)
REMEDIATION:
  1. NO_TLS — Stop the task, verify MySQL TLS support via test-connection, then
     modify the source endpoint:
     aws dms modify-endpoint --endpoint-arn <source-arn> --ssl-mode verify-full
     Add a KMS key:
     aws dms modify-endpoint --endpoint-arn <source-arn> --kms-key-id <key-arn>
  2. NO_LOGGING — Enable task logging with info level:
     aws dms modify-replication-task --replication-task-arn <arn> \
       --replication-task-settings '{"Logging":{"EnableLogging":true,"LogLevel":"info","LogComponents":[{"Id":"DATA_STRUCTURE","Severity":"LOGGER_SEVERITY_ONLY_INFO"},{"Id":"COMMON_AGENT","Severity":"LOGGER_SEVERITY_ONLY_INFO"}]}}'
     Verify the task IAM role has logs:CreateLogGroup/CreateLogStream/PutLogEvents.
  3. CONFIG_GAP — Make the instance private and enable Multi-AZ:
     aws dms modify-replication-instance --replication-instance-arn <arn> --publicly-accessible false --multi-az
  4. CONFIG_GAP — Enable validation and deletion protection:
     aws dms modify-replication-task --replication-task-arn <arn> --deletion-protection
  5. Upgrade the instance class from dms.t3.medium to dms.r5.large or larger
     for sustained CDC throughput.
```

## What the skill caught that a generic assistant misses

1. **Priority-based verdict aggregation.** A generic assistant lists "issues"
   without prioritization. The skill applies the strict priority order
   (NO_TLS > NO_LOGGING > CONFIG_GAP > OK) so the operator knows the
   single most critical dimension is plaintext data — even though there are
   seven total findings.

2. **The metrics-vs-logs trap.** A generic assistant says "enable logging."
   The skill explains that DMS CloudWatch metrics are always on regardless
   of EnableLogging — so the DMS console shows a green task while data is
   silently lost. This non-obvious behavior is the core insight that makes
   `EnableLogging: false` dangerous.

3. **Missing SslMode defaults to none.** If the endpoint had no SslMode
   field at all, a generic assistant might skip it ("not configured").
   The skill knows that missing SslMode is equivalent to `none` — plaintext
   — and flags it as NO_TLS.

4. **KmsKeyId ≠ transit encryption.** A generic assistant might see KMS on
   the target endpoint and say "encryption is configured." The skill
   distinguishes endpoint-config encryption (KmsKeyId) from data-in-transit
   encryption (SslMode) — they are independent dimensions.

5. **Burstable instance class on CDC.** The skill catches that
   `dms.t3.medium` is burstable and will deplete CPU credits under sustained
   CDC load — a performance finding that a security-focused assistant would
   miss but that causes silent CDC lag and data staleness.

## Slash-command invocation

```
/aws:audit-dms-replication-task
```

Or via the orchestrator:

```
/aws:pipeline
You: "audit this DMS replication task before production cutover"
```

## CLI routing

```bash
node cli/bin/cli.js route "audit this DMS replication task"
# [Phase: Audit | Skills routed: dms-replication-task-auditor]
```

## Live-account follow-up (optional, requires AWS CLI)

After remediating the findings, validate the task posture:

```bash
# Verify the source endpoint SslMode was updated
aws dms describe-endpoints --filters Name=endpoints-id,Values=<source-id> \
  --profile default --output json | jq '.Endpoints[].SslMode'

# Confirm logging is enabled
aws dms describe-replication-tasks --filters Name=replication-task-id,Values=<task-id> \
  --profile default --output json | jq '.ReplicationTasks[].ReplicationTaskSettings' | python3 -c "import sys,json; print(json.loads(sys.stdin.read()).get('Logging',{}).get('EnableLogging'))"

# Verify the instance is private and Multi-AZ
aws dms describe-replication-instances --filters Name=replication-instance-id,Values=<instance-id> \
  --profile default --output json | jq '.ReplicationInstances[] | {PubliclyAccessible,MultiAZ}'
```

Then monitor CloudWatch Logs for `ERROR` entries during the migration.
