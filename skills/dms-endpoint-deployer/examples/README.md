# End-to-End Example: DMS Endpoint Deployment

A walkthrough showing how to use the `dms-endpoint-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a PostgreSQL source endpoint with CDC enabled,
Secrets Manager for credentials, and verify-full SSL. The migration
needs:

- Source: PostgreSQL at prod-db.cluster-abc123.us-east-1.rds.amazonaws.com
- Port: 5432
- Database: analytics
- Region: us-east-1
- CDC: pglogical plugin, slot dms_replication_slot
- Credentials: Secrets Manager (secret dms-pg-prod)
- SSL: verify-full with certificate prod-ca-cert
- KMS: customer-managed key
- Replication instance: rep-instance-prod
- Tags: Environment=production, MigrationType=cdc

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-dms-endpoint
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a DMS PostgreSQL source endpoint with CDC, Secrets
      Manager credentials, and verify-full SSL."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a dms endpoint"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
DMS_ENDPOINT: pg-source-prod (postgres, source)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Endpoint type: source
  [✓] Engine: postgres (port: 5432, database: analytics)
  [✓] Server: prod-db.cluster-abc123.us-east-1.rds.amazonaws.com
  [✓] Credentials: Secrets Manager (dms-pg-prod)
  [✓] SSL mode: verify-full (certificate: prod-ca-cert)
  [✓] Extra connection attributes: PluginName=pglogical;slotName=dms_replication_slot
  [✓] KMS key: arn:aws:kms:us-east-1:123456789012:key/abc123
  [✓] CDC prerequisites: MET (wal_level=logical, max_replication_slots=5)
  [✓] Replication instance: rep-instance-prod (engine version: 3.5.2, status: available)
  [✓] Engine version compatibility: PASS (PostgreSQL 16 supported by DMS 3.5.x)
  [✓] Connection test: PASS
  [✓] Tags: Environment=production, MigrationType=cdc
VERIFICATION_COMMANDS:
  aws dms describe-endpoints --filters Name=endpoint-id,Values=pg-source-prod --region us-east-1
  aws dms test-connection --replication-instance-arn arn:aws:dms:us-east-1:123456789012:rep:rep-instance-prod --endpoint-arn arn:aws:dms:us-east-1:123456789012:endpoint:pg-source-prod --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Import the CA certificate (if not already imported)
aws dms import-certificate \
  --certificate-identifier "prod-ca-cert" \
  --certificate-pem "fileb://prod-ca.pem" \
  --region us-east-1

# Step 2: Create the PostgreSQL source endpoint
aws dms create-endpoint \
  --endpoint-identifier "pg-source-prod" \
  --endpoint-type source \
  --engine-name postgres \
  --secrets-manager-access-role-arn "arn:aws:iam::123456789012:role/dms-vpc-role" \
  --secrets-manager-secret-id "arn:aws:secretsmanager:us-east-1:123456789012:secret:dms-pg-prod-abc123" \
  --database-name analytics \
  --ssl-mode verify-full \
  --certificate-arn "arn:aws:dms:us-east-1:123456789012:cert:prod-ca-cert" \
  --extra-connection-attributes "PluginName=pglogical;slotName=dms_replication_slot" \
  --kms-key-id "arn:aws:kms:us-east-1:123456789012:key/abc123" \
  --tags Key=Environment,Value=production Key=MigrationType,Value=cdc \
  --region us-east-1

# Step 3: Test the connection
aws dms test-connection \
  --replication-instance-arn "arn:aws:dms:us-east-1:123456789012:rep:rep-instance-prod" \
  --endpoint-arn "arn:aws:dms:us-east-1:123456789012:endpoint:pg-source-prod" \
  --region us-east-1

# Step 4: Verify connection test result
aws dms describe-connections \
  --filters Name=endpoint-arn,Values=arn:aws:dms:us-east-1:123456789012:endpoint:pg-source-prod \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Verify endpoint configuration
aws dms describe-endpoints \
  --filters Name=endpoint-id,Values=pg-source-prod \
  --region us-east-1

# Verify connection status (should be successful)
aws dms describe-connections \
  --filters Name=endpoint-arn,Values=arn:aws:dms:us-east-1:123456789012:endpoint:pg-source-prod \
  --region us-east-1

# Verify source CDC prerequisites (on the PostgreSQL source):
#   SHOW wal_level;          -- must return 'logical'
#   SHOW max_replication_slots;  -- must be >= 1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| CDC prerequisites | Not checked | wal_level=logical, replication slots verified | CDC tasks fail without source DB configuration |
| Credentials | Inline password | Secrets Manager with rotation awareness | Inline passwords leak in state files |
| SSL mode | require (no verification) | verify-full with imported certificate | require allows man-in-the-middle |
| Extra connection attributes | Not specified | PluginName=pglogical;slotName=... | Without pglogical, PostgreSQL CDC fails |
| Engine version | Not checked | Compatibility verified (PG 16 + DMS 3.5.x) | Version mismatch causes silent failures |
| Certificate | Not imported | CA cert imported before endpoint creation | verify-full fails without imported cert |

---

## Related artifacts

- **Skill definition:** `skills/dms-endpoint-deployer/SKILL.md`
- **CDC prerequisites guide:** `skills/dms-endpoint-deployer/references/cdc-prerequisites.md`
- **Connection tuning guide:** `skills/dms-endpoint-deployer/references/connection-tuning.md`
- **Slash command:** `commands/aws/deploy-dms-endpoint.md`
- **Eval suite:** `skills/dms-endpoint-deployer/evals/evals.json`
- **Legacy test cases:** `skills/dms-endpoint-deployer/eval/test-cases.yaml`
