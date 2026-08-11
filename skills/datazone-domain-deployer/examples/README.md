# End-to-End Example: Amazon DataZone Domain Deployment

A walkthrough showing how to use the `datazone-domain-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Amazon DataZone domain with an S3 data
source, cross-account IAM role chaining, glossary-driven governance,
and a request-approve subscription workflow. The deployment needs:

- Domain: `analytics-domain` (account 111111111111)
- Project: `customer-analytics`
- S3 data source: `my-customer-events` (account 222222222222)
- Cross-account IAM role: `DataZoneS3AccessRole` in source account
- Glossary: PII (steward approval), Public (auto-approve)
- Subscription workflow: request-approve model
- Blueprint: Default Data Lake
- Environment profile: production-data-lake
- KMS CMK: `alias/datazone-cmk`
- Region: `us-east-1`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-datazone-domain
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an Amazon DataZone domain called analytics-domain
      with an S3 data source my-customer-events in account
      222222222222. Create glossary terms PII and Public with
      subscription policies. Use CMK alias/datazone-cmk."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a datazone domain"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DATAZONE: analytics-domain (domain-aaa11122)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Domain: analytics-domain (domain-aaa11122) — AVAILABLE
  [✓] Domain execution role: arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution
  [✓] SSO/IAM Identity Center: configured (identity store: d-abc12345)
  [✓] Project: customer-analytics (project-bbb22233) — project owner: data-steward@corp
  [✓] Data source: customer-events-s3 (S3) — connection established
  [✓] Cross-account IAM role: arn:aws:iam::222222222222:role/DataZoneS3AccessRole — trust policy verified
  [✓] Assets: discovered and published (42 assets in catalog)
  [✓] Glossary: 15 terms configured — subscription policies attached (PII → steward approval, Public → auto-approve)
  [✓] Metadata enrichment: Lambda auto-classification configured (datazone-auto-classify)
  [✓] Subscription workflow: request-approve model — approver: data-steward@corp
  [✓] Blueprint: Default Data Lake — enabled
  [✓] Environment profile: production-data-lake → account 222222222222, region us-east-1
  [✓] Encryption: KMS CMK (alias/datazone-cmk)
  [✓] Tags: Environment=production, Domain=analytics
VERIFICATION_COMMANDS:
  aws datazone get-domain --domain-id domain-aaa11122
  aws datazone list-projects --domain-id domain-aaa11122
  aws datazone list-data-sources --domain-id domain-aaa11122
  aws datazone list-assets --domain-id domain-aaa11122
  aws datazone list-glossary-terms --domain-id domain-aaa11122
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the domain
DOMAIN_ID=$(aws datazone create-domain \
  --name analytics-domain \
  --description "Centralized data governance domain for analytics" \
  --domain-execution-role arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution \
  --kms-key-id alias/datazone-cmk \
  --region us-east-1 \
  --query 'id' --output text)

# Step 2: Wait for domain to become AVAILABLE
aws datazone get-domain --domain-id "$DOMAIN_ID" --query 'status' --region us-east-1
# Expected: AVAILABLE

# Step 3: Create the project
PROJECT_ID=$(aws datazone create-project \
  --domain-id "$DOMAIN_ID" \
  --name customer-analytics \
  --description "Customer analytics project" \
  --region us-east-1 \
  --query 'id' --output text)

# Step 4: In the SOURCE account (222222222222), create the IAM role
# (run this with source account credentials)
aws iam create-role \
  --role-name DataZoneS3AccessRole \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/service-role/AmazonDataZoneDomainExecution"},
      "Action": "sts:AssumeRole"
    }]
  }'

aws iam put-role-policy \
  --role-name DataZoneS3AccessRole \
  --policy-name DataZoneS3ReadAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:GetObject", "s3:ListBucket", "s3:GetBucketLocation"],
      "Resource": ["arn:aws:s3:::my-customer-events", "arn:aws:s3:::my-customer-events/*"]
    }]
  }'

# Step 5: Add the S3 data source in the project
aws datazone create-data-source \
  --domain-id "$DOMAIN_ID" \
  --project-id "$PROJECT_ID" \
  --name customer-events-s3 \
  --type S3 \
  --region us-east-1

# Step 6: Create glossary terms with subscription policies
aws datazone create-glossary-term \
  --domain-id "$DOMAIN_ID" --name "PII" --status ENABLED --region us-east-1

aws datazone create-glossary-term \
  --domain-id "$DOMAIN_ID" --name "Public" --status ENABLED --region us-east-1

# Step 7: Enable the Default Data Lake blueprint
aws datazone update-environment-blueprint \
  --domain-id "$DOMAIN_ID" \
  --blueprint-id default-data-lake \
  --enabled --region us-east-1

# Step 8: Create the environment profile
aws datazone create-environment-profile \
  --domain-id "$DOMAIN_ID" \
  --name production-data-lake \
  --blueprint-id default-data-lake \
  --environment-configuration '{
    "awsAccountId": "222222222222",
    "awsRegion": "us-east-1"
  }' \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify domain status
aws datazone get-domain --domain-id "$DOMAIN_ID" --query 'status'

# Verify project
aws datazone list-projects --domain-id "$DOMAIN_ID"

# Verify data source
aws datazone list-data-sources --domain-id "$DOMAIN_ID"

# Verify discovered assets
aws datazone list-assets --domain-id "$DOMAIN_ID"

# Verify glossary terms
aws datazone list-glossary-terms --domain-id "$DOMAIN_ID"

# Verify the cross-account IAM role trust policy
aws iam get-role \
  --role-name DataZoneS3AccessRole \
  --query 'Role.AssumeRolePolicyDocument'
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Cross-account IAM role | Not configured | Trust policy with full execution role ARN | Without the role, DataZone connects but all reads fail with Access Denied |
| Subscription model | Assumes auto-approval | Request-approve with glossary routing | Subscriptions require explicit approval; glossary terms route to the right approver |
| Glossary terms | Labels only | Policy engine with subscription policies | Glossary terms carry approval routing rules; not just tags |
| SSO | Assumes IAM users work | IAM Identity Center required | DataZone does NOT support IAM users; SSO is mandatory |
| Blueprint vs profile | Confused or skipped | Blueprint = WHAT, profile = WHERE | Both are needed: blueprint defines the template, profile maps to the deployment target |
| Domain status | Creates project immediately | Waits for AVAILABLE status | Domain creation is asynchronous; project creation fails if domain is not ready |
| Trust policy Principal | Account ID root | Full execution role ARN | Account root allows any role in the domain account to assume; full ARN restricts to DataZone only |

---

## Related artifacts

- **Skill definition:** `skills/datazone-domain-deployer/SKILL.md`
- **Cross-account and subscription guide:** `skills/datazone-domain-deployer/references/cross-account-and-subscriptions.md`
- **Blueprints and governance guide:** `skills/datazone-domain-deployer/references/blueprints-and-governance.md`
- **Slash command:** `commands/aws/deploy-datazone-domain.md`
- **Eval suite:** `skills/datazone-domain-deployer/evals/evals.json`
- **Legacy test cases:** `skills/datazone-domain-deployer/eval/test-cases.yaml`
