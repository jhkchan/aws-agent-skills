# End-to-End Example: Lake Formation Permissions Deployment

A walkthrough showing how to use the `lakeformation-permissions-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are deploying LF-tag based access control for the analytics team
on a production data lake. The deployment requires:

- Data lake admin registration (dedicated LFDataLakeAdmin role)
- LF-tag keys: environment, department, sensitivity
- LF-tag attachment to database analytics_db and table transactions
- LF-tag-based SELECT/DESCRIBE grant to AnalyticsTeamRole
- Column-level security for PII columns
- CloudTrail auditing

Deployment: `analytics-team-lf-tag-access`
Region: `us-east-1`
Account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-lakeformation-permissions
```

Then paste the deployment requirements.

### Option B: Natural language

```
You: "Deploy Lake Formation LF-tag based access control for the
      analytics team. Register data lake admin LFDataLakeAdmin.
      Create LF-tag keys: environment (production, staging, dev),
      department (finance, engineering, marketing), sensitivity
      (public, internal, restricted, pii). Attach LF-tags to
      database analytics_db: environment=production,
      department=finance. Attach LF-tags to table
      analytics_db.transactions: environment=production,
      department=finance, sensitivity=restricted. Grant LF-tag-based
      SELECT and DESCRIBE to AnalyticsTeamRole on TABLE resources
      matching environment=production AND department=finance.
      Account: 123456789012. Region: us-east-1."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy lake formation lf-tag permissions"
```

Output:

```
[Phase: Deploy | Skills routed: lakeformation-permissions-deployer]

Primary route: lakeformation-permissions-deployer (score: 18)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
PERMISSION_DEPLOYMENT: analytics-team-lf-tag-access
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Data lake admin — arn:aws:iam::123456789012:role/LFDataLakeAdmin (registered)
  [✓]      LF-tag keys — environment (production, staging, dev), department (finance, engineering, marketing), sensitivity (public, internal, restricted, pii)
  [✓]      LF-tag on database — analytics_db: environment=production, department=finance
  [✓]      LF-tag on table — analytics_db.transactions: environment=production, department=finance, sensitivity=restricted
  [✓]      Principal — arn:aws:iam::123456789012:role/AnalyticsTeamRole
  [✓]      LF-tag-based grant — SELECT, DESCRIBE on TABLE resources: environment=production AND department=finance
  [✓]      Tags — Environment=production, Governance=lake-formation
VERIFICATION_COMMANDS:
  aws lakeformation list-permissions --principal arn:aws:iam::123456789012:role/AnalyticsTeamRole
  aws lakeformation get-resource-lf-tags --resource '{"Database": {"Name": "analytics_db"}}'
  aws lakeformation get-resource-lf-tags --resource '{"Table": {"DatabaseName": "analytics_db", "Name": "transactions"}}'
  aws lakeformation list-lf-tags
```

---

## Step 3 — Deployment commands

The skill generates the CLI sequence (from
`references/cli-commands-and-iac.md`):

```bash
# Step 1: Register data lake admin
aws lakeformation put-data-lake-settings \
  --data-lake-settings '{
    "DataLakeAdmins": [
      {"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/LFDataLakeAdmin"}
    ]
  }'

# Step 2: Create LF-tag keys
aws lakeformation create-lf-tag --tag-key environment --tag-values production staging dev
aws lakeformation create-lf-tag --tag-key department --tag-values finance engineering marketing
aws lakeformation create-lf-tag --tag-key sensitivity --tag-values public internal restricted pii

# Step 3: Attach LF-tags to database
aws lakeformation add-lf-tags-to-resource \
  --resource '{"Database": {"Name": "analytics_db"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]'

# Step 4: Attach LF-tags to table
aws lakeformation add-lf-tags-to-resource \
  --resource '{"Table": {"DatabaseName": "analytics_db", "Name": "transactions"}}' \
  --lf-tags '[{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}, {"TagKey": "sensitivity", "TagValues": ["restricted"]}]'

# Step 5: Grant LF-tag-based permissions
aws lakeformation grant-permissions \
  --principal '{"DataLakePrincipalIdentifier": "arn:aws:iam::123456789012:role/AnalyticsTeamRole"}' \
  --permissions SELECT DESCRIBE \
  --resource '{"LFTagPolicy": {"ResourceType": "TABLE", "Expression": [{"TagKey": "environment", "TagValues": ["production"]}, {"TagKey": "department", "TagValues": ["finance"]}]}}'
```

---

## Step 4 — Post-deployment verification

```bash
# List permissions granted to the principal
aws lakeformation list-permissions --principal arn:aws:iam::123456789012:role/AnalyticsTeamRole

# Verify LF-tags on database
aws lakeformation get-resource-lf-tags --resource '{"Database": {"Name": "analytics_db"}}'

# Verify LF-tags on table
aws lakeformation get-resource-lf-tags --resource '{"Table": {"DatabaseName": "analytics_db", "Name": "transactions"}}'

# List all LF-tag keys
aws lakeformation list-lf-tags

# Verify data lake admin
aws lakeformation list-data-lake-settings --query 'DataLakeSettings.DataLakeAdmins'
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Data lake admin | Not verified | Registered and confirmed | Without an admin, all LF-tag and grant operations fail with AccessDeniedException. |
| LF-tags on resources | Skipped | Attached before grants | Without LF-tags on resources, tag-based grants match nothing — silent zero access. |
| Column-level security | Table-level SELECT (all columns) | Column grant excluding PII | Table-level SELECT grants access to ALL columns including PII. |
| Permission model | Named resource grants | LF-tag-based grants | LF-tag grants are dynamic — new tables auto-inherit access via tags. |
| Admin role scoping | `AdministratorAccess` | Dedicated `LFDataLakeAdmin` | Broad admin role is a privilege escalation vector. |
| Grant ordering | Grants before tags | Tags first, then grants | Tags-first ordering prevents silent zero-access failures. |
| Verification | Not included | list-permissions, get-resource-lf-tags | Without verification, silent permission failures go undetected. |

---

## Related artifacts

- **Skill definition:** `skills/lakeformation-permissions-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/lakeformation-permissions-deployer/references/cli-commands-and-iac.md`
- **LF-tags and column security guide:** `skills/lakeformation-permissions-deployer/references/lf-tags-and-column-security-guide.md`
- **Slash command:** `commands/aws/deploy-lakeformation-permissions.md`
- **Eval suite:** `skills/lakeformation-permissions-deployer/evals/evals.json`
- **Legacy test cases:** `skills/lakeformation-permissions-deployer/eval/test-cases.yaml`
