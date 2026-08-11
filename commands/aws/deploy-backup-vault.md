---
description: Provision an AWS Backup vault with production-grade defaults (customer-managed KMS encryption, compliance or governance vault lock with WORM retention, backup plan with lifecycle and cross-region copy, continuous vs periodic backup for PITR, tag-based or resource-ARN selection, vault access policy, backup report plans). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create backup vault"
  - "deploy backup vault"
  - "vault lock compliance mode"
  - "backup plan deploy"
  - "backup policy"
  - "cross-region backup copy"
  - "continuous backup pitr"
  - "backup vault access policy"
  - "backup report plan"
  - "aws backup org policy"
  - "backup vault kms"
  - "worm backup vault"
  - "backup vault"
routes_to: backup-vault-deployer
---

# /aws:deploy-backup-vault

Activate the `backup-vault-deployer` skill and provision an AWS
Backup vault with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Vault creation (customer-managed KMS key, tags)
2. Vault lock mode selection (governance vs compliance — WORM)
3. Vault lock retention window (MinRetentionDays, MaxRetentionDays, ChangeableForDays)
4. Backup plans (rules with lifecycle, schedule, cold storage)
5. Cross-region and cross-account copy (destination vault + KMS prerequisites)
6. Backup selections (tag-based, resource-ARN, conditions)
7. Continuous vs periodic backups (PITR for EC2/RDS/DynamoDB/EFS)
8. Resource-type coverage (EC2/RDS/EFS/DynamoDB/S3/FSx)
9. Vault access policy (cross-account, ransomware resistance)
10. Backup report plans (compliance reporting)
11. Audit Manager integration
12. Recent features (Logically Air-Gapped Backups, Restore Testing)

## When to use

- You need to create a backup vault with KMS encryption.
- You need to apply a vault lock (governance or compliance mode).
- You are deploying a backup plan with lifecycle and cross-region copy.
- You need continuous backups for PITR.
- You need a vault access policy for cross-account backup.
- You need backup report plans for compliance.
- You need an org-level backup policy.

## When NOT to use

- **Operating existing backup vaults** (restore, manage lifecycles) — use
  backup-vault-operator.
- **Restoring from backups** — use restore-specific skills.
- **Auditing existing backup plans** — use backup-plan-auditor.
- **Cross-region backup operations** — use backup-cross-region-operator.

## How to invoke

### Slash command

```
/aws:deploy-backup-vault
```

Then provide: vault name, KMS key ARN/alias, vault lock mode
(governance/compliance), retention window (Min/Max days), backup
plan name, schedule, lifecycle (Delete/Cold storage days), cross-
region copy destination, resource selection method, continuous
backup requirement, tags.

### Natural language

Any of these routes to the same skill:

- "create a compliance-mode backup vault"
- "lock my backup vault for PCI-DSS compliance"
- "deploy a backup plan with cross-region DR copy"
- "set up continuous backups for RDS PITR"
- "create a backup vault with WORM lock"

### CLI routing

```bash
node cli/bin/cli.js route "create backup vault"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create backup
vaults or deploy backup plans. The output checklist feeds into
verification pipelines and downstream backup audit skills.

## Example

```
You: /aws:deploy-backup-vault

     Create a compliance-mode backup vault named
     production-backup-vault in us-east-1 with KMS key
     alias/backup-encryption-key. Lock with MinRetentionDays=90,
     MaxRetentionDays=365. Daily plan with cross-region copy
     to us-west-2. Continuous backup for RDS.

Skill:
  BACKUP_VAULT: production-backup-vault (us-east-1)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Vault lock: Compliance
    [✓] Lock retention: MinRetentionDays=90, MaxRetentionDays=365
    [✓] Lifecycle within lock window: PASS
    [✓] Cross-region copy: destination vault ready
    [✓] Continuous backup: enabled
  VERIFICATION_COMMANDS:
    aws backup describe-backup-vault --backup-vault-name production-backup-vault --region us-east-1
```

## References

- Skill definition: `skills/backup-vault-deployer/SKILL.md`
- Vault lock and compliance guide: `skills/backup-vault-deployer/references/vault-lock-and-compliance-guide.md`
- Cross-region and backup plans guide: `skills/backup-vault-deployer/references/cross-region-and-backup-plans.md`
- Eval suite: `skills/backup-vault-deployer/evals/evals.json`
