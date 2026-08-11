# End-to-End Example: Backup Vault Deployment

A walkthrough showing how to use the `backup-vault-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a compliance-mode AWS Backup vault with
cross-region DR copy, continuous backup for RDS/DynamoDB, and a
tag-based selection covering 45 production resources. The deployment
needs:

- Vault: production-backup-vault (us-east-1)
- KMS: alias/backup-encryption-key (customer-managed)
- Vault lock: COMPLIANCE mode, MinRetentionDays=90, MaxRetentionDays=365
- Backup plan: daily schedule, lifecycle DeleteAfterDays=180
- Cross-region copy: dr-backup-vault in us-west-2
- Continuous backup: RDS, DynamoDB (PITR)
- Selection: tag-based (Backup=daily), 45 resources
- Report plan: backup-compliance-reports S3 bucket

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-backup-vault
```

Then paste the vault requirements.

### Option B: Natural language

```
You: "Create a compliance-mode backup vault named
      production-backup-vault in us-east-1 with KMS key
      alias/backup-encryption-key. Lock with MinRetentionDays=90,
      MaxRetentionDays=365. Daily backup plan with cross-region
      copy to us-west-2. Continuous backup for RDS and DynamoDB.
      Tag-based selection."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create backup vault"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
BACKUP_VAULT: production-backup-vault (us-east-1) — KMS: alias/backup-encryption-key
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Vault name: production-backup-vault (unique)
  [✓] KMS key: arn:aws:kms:us-east-1:123456789012:key/abcd1234 (customer-managed, enabled)
  [✓] KMS key policy: backup.amazonaws.com service principal granted
  [✓] Tags: Environment=production, Compliance=PCI-DSS
  [✓] Vault lock: Compliance
  [✓] Lock retention: MinRetentionDays=90, MaxRetentionDays=365
  [✓] Lock grace period: ChangeableForDays=3 (verify before expiry)
  [✓] Backup plan: production-daily-backup (3 rules)
  [✓] Plan schedule: cron(0 5 ? * MON-SAT *)
  [✓] Lifecycle: DeleteAfterDays=180, MoveToColdAfterDays=60
  [✓] Lifecycle within lock window: PASS (90 ≤ 180 ≤ 365)
  [✓] Continuous backup (PITR): enabled (RecoveryPointType=CONTINUOUS for RDS, DynamoDB)
  [✓] Backup selection: tag-based (Backup=daily) — 45 resources matched
  [✓] Resource coverage: EC2=20, RDS=10, EFS=5, DynamoDB=10, S3=0
  [✓] Cross-region copy: destination vault dr-backup-vault in us-west-2 (ready)
  [✓] Cross-region KMS: destination key alias/dr-encryption-key (accessible)
  [✓] Cross-account: N/A (same-account cross-region)
  [✓] Vault access policy: delete denied from external accounts
  [✓] Report plan: production-backup-compliance-report → S3 backup-compliance-reports
  [✓] Audit Manager: integration enabled (PCI-DSS assessment active)
VERIFICATION_COMMANDS:
  aws backup describe-backup-vault --backup-vault-name production-backup-vault --region us-east-1
  aws backup list-backup-plans --region us-east-1
  aws backup list-backup-selections --backup-plan-id <plan-id> --region us-east-1
  aws backup list-protected-resources --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the vault with customer-managed KMS key
VAULT_NAME="production-backup-vault"
KMS_KEY_ARN=$(aws kms describe-key --key-id alias/backup-encryption-key \
  --query 'KeyMetadata.Arn' --output text)

aws backup create-backup-vault \
  --backup-vault-name "$VAULT_NAME" \
  --encryption-key-arn "$KMS_KEY_ARN" \
  --region us-east-1 \
  --tags Environment=production,Compliance=PCI-DSS

# Step 2: Apply compliance-mode vault lock
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name "$VAULT_NAME" \
  --region us-east-1 \
  --min-retention-days 90 \
  --max-retention-days 365 \
  --changeable-for-days 3 \
  --mode COMPLIANCE

# Step 3: Create the backup plan
cat > /tmp/backup-plan.json << 'EOF'
{
  "BackupPlanName": "production-daily-backup",
  "Rules": [
    {
      "RuleName": "daily-backup-with-dr",
      "TargetBackupVaultName": "production-backup-vault",
      "ScheduleExpression": "cron(0 5 ? * MON-SAT *)",
      "StartWindowMinutes": 480,
      "CompletionWindowMinutes": 10080,
      "Lifecycle": {
        "DeleteAfterDays": 180,
        "MoveToColdStorageAfterDays": 60
      },
      "EnableContinuousBackup": true,
      "CopyActions": [
        {
          "DestinationBackupVaultArn": "arn:aws:backup:us-west-2:123456789012:backup-vault:dr-backup-vault",
          "Lifecycle": { "DeleteAfterDays": 365, "MoveToColdStorageAfterDays": 90 }
        }
      ]
    }
  ]
}
EOF

PLAN_ID=$(aws backup create-backup-plan \
  --backup-plan file:///tmp/backup-plan.json \
  --region us-east-1 \
  --query 'BackupPlanId' --output text)

# Step 4: Create tag-based backup selection
aws backup create-backup-selection \
  --backup-plan-id "$PLAN_ID" \
  --region us-east-1 \
  --backup-selection '{
    "SelectionName": "production-tagged-resources",
    "IamRoleArn": "arn:aws:iam::123456789012:role/service-role/AWSBackupDefaultServiceRole",
    "Conditions": {
      "StringEquals": { "aws:ResourceTag/Backup": "daily" }
    }
  }'

# Step 5: Apply vault access policy (deny external delete)
aws backup put-backup-vault-access-policy \
  --backup-vault-name "$VAULT_NAME" \
  --region us-east-1 \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Deny",
      "NotPrincipal": { "AWS": "arn:aws:iam::123456789012:root" },
      "Action": "backup:DeleteRecoveryPoint",
      "Resource": "*",
      "Condition": {
        "StringNotEquals": { "aws:SourceAccount": "123456789012" }
      }
    }]
  }'

# Step 6: Create report plan
aws backup create-report-plan \
  --report-plan-name "production-backup-compliance-report" \
  --report-setting '{"ReportTemplate":"BACKUP_JOB_REPORT"}' \
  --report-delivery-config '{
    "S3BucketName": "backup-compliance-reports",
    "S3KeyPrefix": "reports/",
    "Formats": ["CSV","JSON"]
  }' \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Vault created with correct KMS key
aws backup describe-backup-vault \
  --backup-vault-name production-backup-vault --region us-east-1 \
  --query '{Name:BackupVaultName,Encryption:EncryptionKeyArn,Lock:LockedDate}'

# Vault lock is applied
aws backup describe-backup-vault \
  --backup-vault-name production-backup-vault --region us-east-1 \
  --query '{MinRetention:MinRetentionDays,MaxRetention:MaxRetentionDays}'

# Backup plan exists with correct rules
aws backup list-backup-plans --region us-east-1 \
  --query 'BackupPlansList[?BackupPlanName==`production-daily-backup`].{Id:BackupPlanId,Name:BackupPlanName}' \
  --output table

# Selection exists and matched resources
aws backup list-backup-selections \
  --backup-plan-id "$PLAN_ID" --region us-east-1 \
  --query 'BackupSelectionsList[*].{Name:SelectionName,Role:IamRoleArn}' \
  --output table

# Protected resources after first backup job
aws backup list-protected-resources --region us-east-1 \
  --query 'Results[*].{Type:ResourceType,ARN:ResourceArn}' \
  --output table | head -20
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| KMS key | Uses AWS-managed (aws/backup) | Customer-managed key | AWS-managed key cannot be customized for cross-account |
| Vault lock mode | Chooses governance "to be safe" | Compliance for PCI-DSS | Governance mode can be removed → compliance violation |
| Lifecycle vs lock | DeleteAfterDays=7 with MinRetention=90 | Cross-checks: PASS (90 ≤ 180 ≤ 365) | Job fails if lifecycle violates lock window |
| Cross-region copy | Adds copy rule, skips destination check | Verifies destination vault + KMS key | Copy fails silently without destination prerequisites |
| Continuous backup | SNAPSHOT only | CONTINUOUS for RDS/DynamoDB | Periodic backup does NOT enable PITR |
| Vault access policy | No policy or open delete | Deny delete from external accounts | Open delete = ransomware vector |
| Selection | Creates selection, no tag coverage check | 45 resources matched via tag | Inconsistent tags silently exclude resources |

---

## Related artifacts

- **Skill definition:** `skills/backup-vault-deployer/SKILL.md`
- **Vault lock and compliance guide:** `skills/backup-vault-deployer/references/vault-lock-and-compliance-guide.md`
- **Cross-region and backup plans guide:** `skills/backup-vault-deployer/references/cross-region-and-backup-plans.md`
- **Slash command:** `commands/aws/deploy-backup-vault.md`
- **Eval suite:** `skills/backup-vault-deployer/evals/evals.json`
- **Legacy test cases:** `skills/backup-vault-deployer/eval/test-cases.yaml`
