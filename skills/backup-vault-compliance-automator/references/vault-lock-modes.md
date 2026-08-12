# Vault Lock Modes Reference

Supplementary reference for the Backup Vault Compliance Automator
skill. Use when selecting between governance and compliance mode,
configuring lock parameters, or auditing an existing Vault Lock
deployment.

## Mode comparison

| Dimension | Governance Mode | Compliance Mode |
|---|---|---|
| Immutability | Soft — privileged override possible | Hard — no override, not even root |
| Lock removal | `CancelLegalHold` by privileged principal | IMPOSSIBLE after cool-off period expires |
| Retention shortening | Can be overridden by privileged principal | Cannot be shortened — only extended |
| Recovery point deletion | Can be overridden with `CancelLegalHold` | Cannot be deleted until retention expires |
| Regulatory compliance | Does NOT meet SEC 17a-4, CFTC 1.31, FINRA 4511 | Meets SEC 17a-4, CFTC 1.31, FINRA 4511, HIPAA |
| Operational risk | Low — mistakes can be corrected | HIGH — mistakes are permanent |
| Cool-off period | Configurable (min 3 days) | Configurable (min 3 days) |
| Post-cool-off reversibility | Lock can still be removed by privileged principal | Lock is PERMANENT — no reversal |

## API parameters

### put-backup-vault-lock-configuration

```bash
aws backup put-backup-vault-lock-configuration \
  --backup-vault-name <vault> \
  --changeable-for-days <3-365> \
  --min-retention-days <1-36500> \
  --max-retention-days <1-36500> \
  [--mode COMPLIANCE] \
  --region <region>
```

| Parameter | Required | Description |
|---|---|---|
| `--backup-vault-name` | Yes | Target vault |
| `--changeable-for-days` | Yes | Cool-off period (min 3 days). During this period the lock can be removed. After expiry, compliance mode is permanent. |
| `--min-retention-days` | Yes | Minimum retention enforced by the lock. Recovery points cannot be deleted before this period expires. |
| `--max-retention-days` | No | Maximum retention enforced by the lock. Prevents excessively long retention. Added in 2024. |
| `--mode` | No | `COMPLIANCE` for hard lock. Omit for governance mode (default). |

### delete-backup-vault-lock-configuration (governance only)

```bash
# Only works during cool-off OR if lock is in governance mode
aws backup delete-backup-vault-lock-configuration \
  --backup-vault-name <vault> \
  --region <region>
```

This call FAILS after the cool-off period in compliance mode.

## Cool-off period management

The cool-off period (`ChangeableForDays`) is the critical safety window:

| Phase | State | Actions possible |
|---|---|---|
| Pre-lock | No lock | Full vault mutability |
| Cool-off (days 1 to N) | `LOCKED` but changeable | Modify lock params, remove lock |
| Post-cool-off (compliance) | `LOCKED` permanently | NOTHING — lock is irreversible |
| Post-cool-off (governance) | `LOCKED` with override | Privileged principal can `CancelLegalHold` |

### Cool-off verification commands

```bash
# Check vault lock state and dates
aws backup describe-backup-vault \
  --backup-vault-name <vault> \
  --query '[LockState,MinRetentionDays,MaxRetentionDays,VaultLockDate,CreationDate]' \
  --output json \
  --region us-east-1

# Verify lock is permanent (should FAIL in compliance mode post-cool-off)
aws backup delete-backup-vault-lock-configuration \
  --backup-vault-name <vault> \
  --region us-east-1
# Expected error: "ResourceNotFoundException" or "InvalidRequestException"
```

## Retention parameter selection

| Compliance standard | Min retention | Max retention | Mode |
|---|---|---|---|
| SEC 17a-4 (broker-dealer) | 1825 (5 years) | 2557 (7 years) | COMPLIANCE |
| CFTC 1.31 (derivatives) | 1825 (5 years) | 2557 (7 years) | COMPLIANCE |
| FINRA 4511 (securities) | 2192 (6 years) | 2557 (7 years) | COMPLIANCE |
| HIPAA (healthcare) | 2192 (6 years) | 2557 (7 years) | COMPLIANCE |
| SOX (public companies) | 2557 (7 years) | 3653 (10 years) | COMPLIANCE |
| IRS (tax records) | 2557 (7 years) | 2557 (7 years) | COMPLIANCE |
| Internal policy (standard) | 30 | 365 | GOVERNANCE |
| Internal policy (strict) | 90 | 1096 | GOVERNANCE |

## Common Vault Lock mistakes

| Mistake | Consequence | Prevention |
|---|---|---|
| Deploying compliance mode without testing governance first | Permanent misconfiguration | Always test parameters in governance mode first |
| Setting MinRetention too high | Over-retention, excessive storage cost | Match exactly to regulatory minimum |
| Setting MinRetention too low | Non-compliance — data expires before regulatory minimum | Verify regulatory requirement before deploying |
| Omitting MaxRetention | No upper bound — backups retained indefinitely | Set MaxRetention to regulatory maximum |
| Forgetting cool-off expiry date | Surprise permanent lock | Document lock date; set calendar reminder |
| Using governance mode when compliance is required | Audit failure — immutability not guaranteed | Verify regulatory requirements before mode selection |
| Attempting to delete vault with locked recovery points | API failure | Let recovery points expire naturally |

## Cost impact of Vault Lock

| Retention period | Storage cost (warm) | Storage cost (cold) | Notes |
|---|---|---|---|
| 90 days | $0.05/GB-month | $0.0125/GB-month | Standard production |
| 365 days | $0.05/GB-month | $0.0125/GB-month | Annual compliance |
| 1827 days (5 years) | $0.05/GB-month | $0.0125/GB-month | SEC/HIPAA |
| 2557 days (7 years) | $0.05/GB-month | $0.0125/GB-month | SEC/FINRA/IRS |

**Cost optimization:** Move recovery points to cold storage tier
within the backup plan to reduce long-term retention costs by 75%.

```bash
# Backup plan with cold storage transition
aws backup create-backup-plan \
  --backup-plan '{
    "BackupPlanName": "compliance-plan",
    "Rules": [{
      "RuleName": "daily-compliance",
      "TargetBackupVaultName": "compliance-vault",
      "ScheduleExpression": "cron(0 5 ? * MON-FRI *)",
      "StartWindowMinutes": 480,
      "CompletionWindowMinutes": 10080,
      "Lifecycle": {
        "MoveToColdStorageAfterDays": 30,
        "DeleteAfterDays": 2557
      }
    }]
  }'
```

With cold storage transition at 30 days, a 1 TB backup retained for
7 years costs approximately:
- Warm (30 days): 1000 GB * $0.05 = $50/month for 1 month = $50
- Cold (2527 days): 1000 GB * $0.0125 = $12.50/month for 84 months = $1,050
- Total 7-year cost: ~$1,100 (vs $4,200 without cold storage)
