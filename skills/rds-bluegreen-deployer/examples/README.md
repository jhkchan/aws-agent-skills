# End-to-End Example: RDS Blue/Green Deployment

A walkthrough showing how to use the `rds-bluegreen-deployer` skill
from invocation through switchover and cleanup. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying a Blue/Green Deployment for an Aurora MySQL cluster
to perform a major version upgrade from MySQL 5.7 to 8.0 with zero
downtime. The deployment needs:

- Source DB (blue): prod-mysql-db (aurora-mysql 5.7.mysql_aurora.2.11.0)
- Target version (green): 8.0.mysql_aurora.3.04.0
- Parameter group for green: prod-mysql80-params
- Region: us-east-1
- Account: 123456789012
- Application has connection retry logic
- Switchover timeout: 300 seconds

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-rds-bluegreen
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an RDS Blue/Green Deployment for my Aurora MySQL
      cluster prod-mysql-db to upgrade from 5.7 to 8.0 in green.
      Use parameter group prod-mysql80-params. Region us-east-1."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create rds blue green deployment"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
BLUE_GREEN: prod-mysql-db → green-prod-mysql-db (bg-prod-upgrade-2026)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Source DB (blue): prod-mysql-db (aurora-mysql 5.7.mysql_aurora.2.11.0)
  [✓] Engine support: Supported (aurora-mysql)
  [✓] Blue status: AVAILABLE
  [✓] Blue/Green deployment: bg-prod-upgrade-2026 — AVAILABLE
  [✓] Green environment: green-prod-mysql-db (8.0.mysql_aurora.3.04.0)
  [✓] Major version upgrade: 5.7 → 8.0 (in green)
  [✓] Parameter group change: prod-mysql80-params (applied to green)
  [✓] Green validation: PASSED
  [✓] Replication (blue → green): ACTIVE, lag < 1s
  [✓] Switchover timeout: 300 seconds
  [✓] Application retry logic: Configured (connection pool with retry)
  [✓] Endpoint strategy: CNAME auto-follow (no app change needed)
  [✓] Tags: Environment=production, Upgrade=mysql57-to-80
VERIFICATION_COMMANDS:
  aws rds describe-blue-green-deployments --blue-green-deployment-identifier bg-prod-upgrade-2026 --region us-east-1
  aws rds describe-db-instances --db-instance-identifier green-prod-mysql-db --region us-east-1
```

---

## Step 3 — Create the Blue/Green Deployment

```bash
# Step 1: Create the Blue/Green Deployment
BG_ID=$(aws rds create-blue-green-deployment \
  --blue-green-deployment-name "bg-prod-upgrade-2026" \
  --source arn:aws:rds:us-east-1:123456789012:cluster:prod-mysql-db \
  --target-engine-version "8.0.mysql_aurora.3.04.0" \
  --target-db-cluster-parameter-group-name "prod-mysql80-cluster-params" \
  --target-db-parameter-group-name "prod-mysql80-params" \
  --region us-east-1 \
  --query 'BlueGreenDeploymentIdentifier' --output text)

echo "Blue/Green Deployment ID: $BG_ID"

# Step 2: Wait for green to be AVAILABLE (creation takes minutes to hours)
aws rds wait db-instance-available \
  --db-instance-identifier "green-prod-mysql-db" \
  --region us-east-1

# Step 3: Verify green engine version
aws rds describe-db-clusters \
  --db-cluster-identifier "green-prod-mysql-db" \
  --query 'DBClusters[0].{Engine:Engine,EngineVersion:EngineVersion,Status:Status}' \
  --region us-east-1 --output table
# Expected: EngineVersion = "8.0.mysql_aurora.3.04.0"
```

---

## Step 4 — Validate green environment

```bash
# Check Blue/Green status (should be AVAILABLE)
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].{Status:Status,Source:Source,Target:Target}' \
  --region us-east-1 --output table

# Verify green accepts connections
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "SELECT VERSION();"
# Expected: 8.0.xxx (Aurora MySQL)

# Run validation queries on green
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p \
  -e "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='mydb';"

# Compare query performance (EXPLAIN on green vs blue)
mysql -h green-prod-mysql-db.cluster-xxx.us-east-1.rds.amazonaws.com \
  -u admin -p mydb \
  -e "EXPLAIN SELECT * FROM orders WHERE customer_id = 12345 ORDER BY created_at DESC LIMIT 10;"
```

---

## Step 5 — Switchover (1-minute downtime)

```bash
# Initiate switchover
aws rds switchover-blue-green-deployment \
  --blue-green-deployment-identifier "$BG_ID" \
  --switchover-timeout 300 \
  --region us-east-1

# Wait for switchover to complete
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --query 'BlueGreenDeployments[0].Status' \
  --region us-east-1
# Expected: SWITCHOVER_COMPLETED

# Verify production endpoint now points to MySQL 8.0
aws rds describe-db-clusters \
  --db-cluster-identifier "prod-mysql-db" \
  --query 'DBClusters[0].EngineVersion' \
  --region us-east-1
# Expected: 8.0.mysql_aurora.3.04.0 (the target version)
```

---

## Step 6 — Delete green (former blue) to stop 2x billing

```bash
# Delete the Blue/Green Deployment and the former blue (now new green)
aws rds delete-blue-green-deployment \
  --blue-green-deployment-identifier "$BG_ID" \
  --delete-target \
  --region us-east-1

# Verify deletion
aws rds describe-blue-green-deployments \
  --blue-green-deployment-identifier "$BG_ID" \
  --region us-east-1 2>&1
# Expected: BlueGreenDeploymentNotFound
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Green validation | Skips validation, switches immediately | Thorough validation before switchover | Validation is the last checkpoint before production impact |
| Cost (2x billing) | Not mentioned | 2x cost window from creation to green deletion | Green is a full clone; delete promptly after switchover |
| DDL in blue | Runs DDL on production directly | Blue is frozen; DDL ONLY in green | DDL on blue breaks logical replication |
| Switchover downtime | Claims "zero downtime" | ~1 minute; apps need retry logic | Long-lived connections break; retry needed |
| Endpoint behavior | Says "update connection strings" | CNAME auto-follows; no app change needed | DNS swap is transparent to CNAME-based apps |
| Engine support | Assumes all engines supported | Only Aurora MySQL/PG, RDS MySQL/PG | SQL Server, Oracle, etc. do NOT support Blue/Green |
| Replication lag | Not checked before switchover | Verify lag near-zero before switching | High lag increases switchover downtime |

---

## Related artifacts

- **Skill definition:** `skills/rds-bluegreen-deployer/SKILL.md`
- **Switchover and DNS guide:** `skills/rds-bluegreen-deployer/references/switchover-and-dns.md`
- **Green validation and changes guide:** `skills/rds-bluegreen-deployer/references/green-validation-and-changes.md`
- **Slash command:** `commands/aws/deploy-rds-bluegreen.md`
- **Eval suite:** `skills/rds-bluegreen-deployer/evals/evals.json`
- **Legacy test cases:** `skills/rds-bluegreen-deployer/eval/test-cases.yaml`
