# End-to-End Example: RDS DB Parameter Group Provisioning

A walkthrough showing how to use the `rds-parameter-group-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a PostgreSQL 15 DB parameter group for the payments
service. The group requires:

- Family: `postgres15`
- `max_connections=200` (static, requires reboot)
- `shared_buffers={DBInstanceClassMemory/4}` (static, requires reboot)
- `work_mem=8MB` (dynamic, immediate)
- `wal_buffers=16MB` (dynamic, immediate)
- `checkpoint_completion_target=0.9` (dynamic, immediate)
- `effective_cache_size={DBInstanceClassMemory*3/4}` (dynamic, immediate)
- `random_page_cost=1.1` (dynamic, immediate)
- `log_min_duration_statement=1000` (dynamic, immediate)
- Association: DB instance `payments-db-pg15`
- Tags: Environment=production, Application=payments

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-rds-parameter-group
```

Then paste the parameter group requirements.

### Option B: Natural language

```
You: "Provision a PostgreSQL 15 parameter group for the payments DB.
      Name: payments-pg15-params. Set max_connections=200,
      shared_buffers={DBInstanceClassMemory/4}, work_mem=8MB,
      wal_buffers=16MB, checkpoint_completion_target=0.9,
      effective_cache_size={DBInstanceClassMemory*3/4},
      random_page_cost=1.1, log_min_duration_statement=1000.
      Associate with payments-db-pg15."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy rds parameter group"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
GROUP: payments-pg15-params
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Family — postgres15
  [✓]      Type — DBParameterGroup
  [✓]      max_connections — 200 (static, PENDING REBOOT required)
  [✓]      shared_buffers — {DBInstanceClassMemory/4} (static, PENDING REBOOT required)
  [✓]      work_mem — 8MB (dynamic, immediate)
  [✓]      wal_buffers — 16MB (dynamic, immediate)
  [✓]      checkpoint_completion_target — 0.9 (dynamic, immediate)
  [✓]      effective_cache_size — {DBInstanceClassMemory*3/4} (dynamic, immediate)
  [✓]      random_page_cost — 1.1 (dynamic, immediate)
  [✓]      log_min_duration_statement — 1000 (dynamic, immediate)
  [✓]      Association — DB instance payments-db-pg15
  [✓]      Reboot required — YES (static params: max_connections, shared_buffers)
  [✓]      Tags — Environment=production, Application=payments
VERIFICATION_COMMANDS:
  aws rds describe-db-parameters --db-parameter-group-name payments-pg15-params
  aws rds describe-db-instances --db-instance-identifier payments-db-pg15
  aws rds describe-pending-maintenance-actions --db-instance-identifier payments-db-pg15
```

---

## Step 3 — Provisioning commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Create the parameter group
aws rds create-db-parameter-group \
  --db-parameter-group-name payments-pg15-params \
  --db-parameter-group-family postgres15 \
  --description "PostgreSQL 15 parameters for payments service" \
  --tags '[{"Key":"Environment","TagValue":"production"},{"Key":"Application","TagValue":"payments"}]'

# Step 2: Modify parameters (note ApplyMethod per parameter)
aws rds modify-db-parameter-group \
  --db-parameter-group-name payments-pg15-params \
  --parameters '[
    {"ParameterName":"max_connections","ParameterValue":"200","ApplyMethod":"pending-reboot"},
    {"ParameterName":"shared_buffers","ParameterValue":"{DBInstanceClassMemory/4}","ApplyMethod":"pending-reboot"},
    {"ParameterName":"work_mem","ParameterValue":"8MB","ApplyMethod":"immediate"},
    {"ParameterName":"wal_buffers","ParameterValue":"16MB","ApplyMethod":"immediate"},
    {"ParameterName":"checkpoint_completion_target","ParameterValue":"0.9","ApplyMethod":"immediate"},
    {"ParameterName":"effective_cache_size","ParameterValue":"{DBInstanceClassMemory*3/4}","ApplyMethod":"immediate"},
    {"ParameterName":"random_page_cost","ParameterValue":"1.1","ApplyMethod":"immediate"},
    {"ParameterName":"log_min_duration_statement","ParameterValue":"1000","ApplyMethod":"immediate"}
  ]'

# Step 3: Associate with the DB instance
aws rds modify-db-instance \
  --db-instance-identifier payments-db-pg15 \
  --db-parameter-group-name payments-pg15-params \
  --apply-immediately

# Step 4: Reboot for static parameters (max_connections, shared_buffers)
aws rds reboot-db-instance \
  --db-instance-identifier payments-db-pg15
```

---

## Step 4 — Post-provisioning verification

```bash
# Verify parameter group settings
aws rds describe-db-parameters \
  --db-parameter-group-name payments-pg15-params \
  --query 'Parameters[?Source!=`engine-default`].{Name:ParameterName,Value:ParameterValue,ApplyType:ApplyType}' \
  --output table

# Verify DB instance association
aws rds describe-db-instances \
  --db-instance-identifier payments-db-pg15 \
  --query 'DBInstances[].DBParameterGroups'

# Check pending maintenance (static params awaiting reboot)
aws rds describe-pending-maintenance-actions \
  --db-instance-identifier payments-db-pg15
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Static vs dynamic | ApplyMethod=immediate on all params | pending-reboot for static, immediate for dynamic | Setting immediate on a static param silently becomes pending-reboot — RDS does not error, the param just doesn't apply until reboot |
| Reboot flag | Not mentioned | "Reboot required — YES" with specific params listed | Without the flag, the operator does not know to schedule a reboot window. Static params are silently no-ops until reboot |
| Formula syntax | Absolute values (6GB) | {DBInstanceClassMemory/4} formula | Formula adapts to instance class changes. Absolute values break when the instance is scaled up or down |
| Family match | Guessed family | Verified against engine version via describe-db-engine-versions | A postgres15 parameter group cannot attach to a postgres14 instance — the family is immutable |
| Association | Often forgotten | Explicit ModifyDBInstance step | Creating the parameter group alone has no effect. It must be associated with a DB instance |
| random_page_cost | Default 4.0 (spinning disk) | 1.1 (SSD/EBS) | Modern RDS uses SSD storage. Default 4.0 causes the planner to avoid index scans |
| log_min_duration_statement | Disabled (-1) | 1000ms (1 second) | Without slow query logging, performance issues are invisible. 1s catches problematic queries without log noise |

---

## Related artifacts

- **Skill definition:** `skills/rds-parameter-group-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/rds-parameter-group-deployer/references/deployment-cli-commands.md`
- **Database tuning guide:** `skills/rds-parameter-group-deployer/references/database-tuning-guide.md`
- **Slash command:** `commands/aws/deploy-rds-parameter-group.md`
- **Eval suite:** `skills/rds-parameter-group-deployer/evals/evals.json`
- **Legacy test cases:** `skills/rds-parameter-group-deployer/eval/test-cases.yaml`
