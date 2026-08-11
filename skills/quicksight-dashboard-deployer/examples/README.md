# End-to-End Example: QuickSight Dashboard Deployment

A walkthrough showing how to use the `quicksight-dashboard-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Enterprise edition QuickSight dashboard backed
by Athena with SPICE ingestion, hourly refresh, and row-level security.
The dashboard needs:

- QuickSight account: Enterprise edition, us-east-1, account-id 123456789012
- Data source: Athena workgroup "primary"
- Dataset: "sales_metrics" (SPICE mode, hourly refresh)
- Analysis: 2 sheets (Overview, Regional Breakdown)
- Dashboard: "sales-dashboard"
- RLS: rules dataset mapping users to region values
- Tags: Environment=production, Domain=sales

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-quicksight-dashboard
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a QuickSight Enterprise dashboard backed by Athena
      with SPICE, hourly refresh, and row-level security by region."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a quicksight dashboard"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
QUICKSIGHT_DASHBOARD: sales-dashboard (version 1)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] QuickSight account: my-org-quicksight (edition: Enterprise, region: us-east-1)
  [✓] Data source: ds-athena-prod (type: Athena)
  [✓] VPC connection: Not required (Athena is AWS-native)
  [✓] Dataset: ds-sales-metrics (mode: SPICE)
  [✓] SPICE refresh schedule: HOURLY
  [✓] Analysis: sales-analysis (sheets: 2)
  [✓] Dashboard: sales-dashboard (version: 1, status: CREATED)
  [✓] Row-level security: ENABLED (dataset ds-sales-rls)
  [✓] Template: Not used
  [✓] Dashboard sharing: 3 users, roles: READER
  [✓] IAM service role: Default QuickSight role
  [✓] Parameters: Region, DateRange
  [✓] Tags: Environment=production, Domain=sales
VERIFICATION_COMMANDS:
  aws quicksight describe-dashboard --aws-account-id 123456789012 --dashboard-id sales-dashboard --region us-east-1
  aws quicksight describe-data-set --aws-account-id 123456789012 --data-set-id ds-sales-metrics --region us-east-1
  aws quicksight list-ingestions --aws-account-id 123456789012 --data-set-id ds-sales-metrics --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create Athena data source
aws quicksight create-data-source \
  --aws-account-id 123456789012 \
  --data-source-id ds-athena-prod \
  --name "Athena Production" \
  --type ATHENA \
  --data-source-parameters '{"AthenaParameters":{"WorkGroup":"primary"}}' \
  --region us-east-1

# Step 2: Create SPICE dataset with custom SQL
aws quicksight create-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --name "Sales Metrics" \
  --import-mode SPICE \
  --physical-table-map '{"sales-table":{"CustomSql":{"DataSourceArn":"arn:aws:quicksight:us-east-1:123456789012:datasource/ds-athena-prod","Name":"sales_query","SqlQuery":"SELECT order_id, customer_id, region, revenue, order_date FROM sales","Columns":[{"Name":"order_id","Type":"STRING"},{"Name":"customer_id","Type":"STRING"},{"Name":"region","Type":"STRING"},{"Name":"revenue","Type":"DECIMAL"},{"Name":"order_date","Type":"DATETIME"}]}}}' \
  --region us-east-1

# Step 3: Trigger initial SPICE ingestion
aws quicksight create-ingestion \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --ingestion-id "initial-$(date +%s)" \
  --region us-east-1

# Step 4: Set hourly refresh schedule
aws quicksight put-data-set-refresh-properties \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --refresh-properties '{"RefreshConfiguration":{"IncrementalRefresh":{"Frequency":{"Interval":"HOURLY","TimeOfTheDay":"00:00"}}}}' \
  --region us-east-1

# Step 5: Create RLS rules dataset
aws quicksight create-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-rls \
  --name "Sales RLS Rules" \
  --import-mode SPICE \
  --physical-table-map '{"rls-table":{"RelationalTable":{"DataSourceArn":"arn:aws:quicksight:us-east-1:123456789012:datasource/ds-athena-prod","Schema":"rls","Name":"sales_rls_rules","InputColumns":[{"Name":"UserName","Type":"STRING"},{"Name":"Region","Type":"STRING"}]}}}' \
  --region us-east-1

# Step 6: Enable RLS on main dataset
aws quicksight update-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --row-level-permission-data-set '{"Arn":"arn:aws:quicksight:us-east-1:123456789012:dataset/ds-sales-rls","PermissionPolicy":"GRANT_ACCESS","FormatVersion":"VERSION_1","Namespace":"default","Status":"ENABLED"}' \
  --region us-east-1

# Step 7: Create analysis and dashboard (in QuickSight console or API)
# Step 8: Register readers and share dashboard
aws quicksight register-user \
  --aws-account-id 123456789012 \
  --namespace default \
  --identity-type QUICKSIGHT \
  --email "reader@example.com" \
  --user-role READER \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Dashboard status
aws quicksight describe-dashboard \
  --aws-account-id 123456789012 \
  --dashboard-id sales-dashboard \
  --region us-east-1

# Dataset + SPICE ingestion status
aws quicksight describe-data-set \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --region us-east-1

aws quicksight list-ingestions \
  --aws-account-id 123456789012 \
  --data-set-id ds-sales-metrics \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Query mode | Defaults to Direct Query | SPICE for OLTP sources, Direct Query for analytical stores | Direct Query on RDS/Aurora overwhelms the source with concurrent viewers |
| Refresh schedule | Not configured | Hourly/daily SPICE refresh via put-data-set-refresh-properties | Without a schedule, SPICE data goes stale |
| Row-level security | Not configured | RLS rules dataset + ENABLED on main dataset | Without RLS, every reader sees all data |
| VPC connection | Attempts on Standard edition | Enterprise edition required; VPC connection + IAM role | Standard edition cannot reach private data stores |
| Template deployment | Manual rebuild per tenant | Template versioning + per-tenant dashboards from template | Single template update propagates to all tenants |

---

## Related artifacts

- **Skill definition:** `skills/quicksight-dashboard-deployer/SKILL.md`
- **SPICE and ingestion guide:** `skills/quicksight-dashboard-deployer/references/spice-and-ingestion.md`
- **Templates and RLS guide:** `skills/quicksight-dashboard-deployer/references/templates-and-rls.md`
- **Slash command:** `commands/aws/deploy-quicksight-dashboard.md`
- **Eval suite:** `skills/quicksight-dashboard-deployer/evals/evals.json`
- **Legacy test cases:** `skills/quicksight-dashboard-deployer/eval/test-cases.yaml`
