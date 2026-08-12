# Policy Types and Delegation — Organizations Policy Deployer

Deep reference on the non-SCP Organizations policy types — Tag
Policies, Backup Policies, and AI Services Opt-Out Policies — and
on Organizations Delegated Administrator administration. Loaded
on demand by the skill — kept out of the main SKILL.md body so
the deployment procedure stays scannable.

## Policy types overview

Organizations supports four policy types. Each must be enabled
at the root before it can be created or attached.

| Policy type | Constant | Purpose | Default behavior |
|---|---|---|---|
| Service Control Policy | `SERVICE_CONTROL_POLICY` | Permission boundary (Allow/Deny filter on AWS API calls) | Blocking |
| Tag Policy | `TAG_POLICIES` | Standardize tag keys, values, capitalization | Audit-only (non-blocking) unless `enforced_for` lists resource types |
| Backup Policy | `BACKUP_POLICY` | Apply AWS Backup plans org-wide based on tags | Active backup plans |
| AI Services Opt-Out Policy | `AISERVICES_OPT_OUT_POLICY` | Prevent AWS from using account content to train/improve AI services | Opt-out (no content use) |

### Enable a policy type

```bash
aws organizations enable-policy-type \
  --root-id r-xxxx \
  --policy-type TAG_POLICIES

# Verify enablement
aws organizations list-roots \
  --query 'Roots[0].PolicyTypes[?Type==`TAG_POLICIES`].Status' \
  --output text
# Expected: ENABLED
```

## Tag Policies

### Anatomy of a tag policy

A tag policy JSON has a `tags` object. Each key is a tag key
standardized across the org. Each tag key specifies:

- `TagKey.Value` — the canonical tag key (case-sensitive when
  `CaseSensitive: true`)
- `TagKey.CaseSensitive` — whether the tag key is case-sensitive
- `AllowedValues` — the list of permitted values (optional)
- `EnforcedFor` — the list of resource types where non-compliant
  tagging FAILS the API call (optional; without it, the policy
  is audit-only)

```json
{
  "tags": {
    "Environment": {
      "TagKey": { "Value": "Environment" },
      "EnforcedFor": ["ec2:instance", "s3:bucket", "rds:db"],
      "AllowedValues": ["dev", "staging", "production"]
    },
    "Owner": {
      "TagKey": { "Value": "Owner", "CaseSensitive": true }
    },
    "CostCenter": {
      "TagKey": { "Value": "CostCenter" },
      "AllowedValues": ["cc-1001", "cc-1002", "cc-1003"]
    }
  }
}
```

### Audit-only vs enforced

Without `EnforcedFor`, a tag policy is AUDIT-ONLY. Non-compliant
tags are recorded in the tag-policy compliance report but the
tagging API call (`CreateTags`, `UntagResources`) succeeds. With
`EnforcedFor` listing a resource type, non-compliant tagging on
that resource type FAILS.

```bash
# Generate the compliance report (audit-only mode)
aws organizations describe-effective-policy \
  --policy-type TAG_POLICIES \
  --target-id 111122223311
```

### Inheritance for tag policies

Tag policies inherit like SCPs — the effective tag policy at an
account is the UNION of tag policies along the chain (NOT
intersection like SCPs). A child OU can ADD tags but cannot
remove or weaken parent tag policies.

### Common tag-policy pitfalls

1. **Forgetting that `EnforcedFor` is required for blocking.**
   A policy without `EnforcedFor` is audit-only — operators may
   think tags are enforced but non-compliant tags still apply.

2. **Case-sensitivity surprises.** `Environment` and
   `environment` are different tag keys when `CaseSensitive:
   true`. Use `CaseSensitive: false` (or omit) for case-
   insensitive enforcement.

3. **`AllowedValues` is a closed list.** Any value not in the
   list fails when `EnforcedFor` covers the resource type. Add
   values before rollout, or scope `EnforcedFor` conservatively.

## Backup Policies

### Anatomy of a backup policy

A backup policy JSON defines one or more backup plans, each with
a schedule, a backup vault (per region), and a tag-based
resource selection. The policy is structured in three levels:
`plans`, `rules` (per-region schedule), and `selections` (tag-
based resource targeting).

```json
{
  "plans": {
    "default-backup-plan": {
      "rules": {
        "default-rule": {
          "rule_backup_vault_name": "Default",
          "schedule_expression": "cron(0 5 ? * * *)",
          "start_backup_window_minutes": 480,
          "complete_backup_window_minutes": 10080,
          "lifecycle": {
            "delete_after_days": 30
          },
          "target_backup_vaults": [
            { "backup_vault_arn": "arn:aws:backup:us-east-1:111122223311:backup-vault:Default" }
          ],
          "copy_actions": []
        }
      },
      "regions": ["us-east-1", "us-west-2"]
    }
  },
  "selections": {
    "tags": {
      "backup-plan-default": {
        "iam_role_arn": "arn:aws:iam::111122223311:role/AWSBackupDefaultServiceRole",
        "tag_key": "BackupPlan",
        "tag_value": "default"
      }
    }
  }
}
```

### Tag-based selection

A backup policy applies the SAME plan to every matching resource
in every account under the target root/OU. Tag-based selection
(`StringEquals` on `aws:ResourceTag/<key>`) is the canonical
selector. Resources tagged `BackupPlan=default` are picked up
automatically.

### Common backup-policy pitfalls

1. **Missing backup vault per region.** Each region needs its
   own backup vault ARN. A policy targeting multiple regions
   without per-region vaults fails to apply in the missing
   regions.

2. **Wrong IAM role.** The `iam_role_arn` must exist in EACH
   member account and trust `backup.amazonaws.com`. AWS Backup
   cannot assume a role that does not exist or is mis-configured.

3. **Lifecycle deletes too aggressively.** A short
   `delete_after_days` removes backups before compliance windows
   expire. Align lifecycle with regulatory retention
   requirements.

4. **Cross-account backup vault requires separate setup.** The
   backup-policy `target_backup_vaults` ARN can point to a vault
   in the management account, but the vault must have a backup
   vault policy allowing member-account access.

## AI Services Opt-Out Policies

### Anatomy of an AI services opt-out policy

The policy has a `services` object. The `default` key applies
the opt-out to every AI service, present and future. Each
service can be opted out individually by listing its principal
key.

```json
{
  "services": {
    "default": {
      "opt_out_policy": {
        "@odata.type": "#AWS.OptOutPolicy#ServicesOptOutPolicyDefault",
        "opt_out_enabled_at_level": "account"
      }
    },
    "amazon_polly": {
      "opt_out_policy": {
        "@odata.type": "#AWS.OptOutPolicy#ServicesOptOutPolicy",
        "opt_out_enabled_at_level": "account"
      }
    }
  }
}
```

### All-or-nothing per service

AI services opt-out is organization-wide and all-or-nothing per
service. Once attached at root, it applies to EVERY account.
There is no per-account opt-in override.

### Verification

```bash
# View effective AI services opt-out policy at an account
aws organizations describe-effective-policy \
  --policy-type AISERVICES_OPT_OUT_POLICY \
  --target-id 111122223311
```

### Common AI services opt-out pitfalls

1. **Thinking a child OU can override.** It cannot. Once
   attached at root, the opt-out applies org-wide. There is no
   opt-in at a child.

2. **Forgetting the `default` key.** Without `default`, new AI
   services added by AWS are NOT opted-out automatically. Use
   `default.opt_out_enabled_at_level: account` for future-
   proofing.

3. **Confusing opt-out with IAM.** Opt-out prevents AWS from
   USING account content for training/improvement; it does NOT
   disable the service. The service remains callable via IAM.

## Organizations Delegated Administrator

### What delegation does

`RegisterDelegatedAdministrator` grants a member account read/
list administration for a SPECIFIC AWS service principal (e.g.,
`access-analyzer.amazonaws.com`). The delegated admin can then
manage that service's resources across the org without requiring
IAM roles in each member account.

```bash
aws organizations register-delegated-administrator \
  --account-id 111122223311 \
  --service-principal access-analyzer.amazonaws.com

aws organizations list-delegated-administrators \
  --service-principal access-analyzer.amazonaws.com

aws organizations deregister-delegated-administrator \
  --account-id 111122223311 \
  --service-principal access-analyzer.amazonaws.com
```

### What delegation does NOT do

Delegation is **service-scoped and read/list-only**. The
delegated administrator:

- CANNOT create, attach, detach, or delete SCPs, tag policies,
  backup policies, or AI services opt-out policies. (Policy
  writes always require the management account.)
- CANNOT invite accounts to the org, remove accounts, or move
  accounts between OUs.
- CANNOT create or delete OUs.
- CANNOT enable or disable policy types.

The delegation is per-service — registering the account for
Access Analyzer does not delegate Backup, GuardDuty, or any
other service.

### Common delegable service principals

- `access-analyzer.amazonaws.com` (IAM Access Analyzer)
- `auditmanager.amazonaws.com` (AWS Audit Manager)
- `backup.amazonaws.com` (AWS Backup)
- `config.amazonaws.com` (AWS Config)
- `firewallmanager.amazonaws.com` (AWS Firewall Manager)
- `guardduty.amazonaws.com` (Amazon GuardDuty)
- `resource-explorer-2.amazonaws.com` (AWS Resource Explorer)
- `securityhub.amazonaws.com` (AWS Security Hub)
- `ssm.amazonaws.com` (AWS Systems Manager QuickSetup)
- `storagegateway.amazonaws.com` (AWS Storage Gateway)

### Verification after delegation

```bash
# Confirm the account is registered
aws organizations list-delegated-administrators \
  --query 'DelegatedAdministrators[?Id==`111122223311`].{Account:Id,Service:ServicePrincipal}' \
  --output table

# From the delegated admin account, verify cross-account access
aws accessanalyzer list-analyzers   # should see org-wide analyzers
```

### Common delegation pitfalls

1. **Expecting delegation to grant SCP write.** It does not.
   Policy writes always require the management account. A
   delegated admin cannot create or attach SCPs.

2. **Forgetting to register per service.** Delegating Access
   Analyzer does not delegate GuardDuty. Each service requires
   its own `register-delegated-administrator` call.

3. **Confusing delegation with IAM roles.** Delegation uses
   AWS-managed service-linked roles. Do NOT create custom IAM
   roles in member accounts for the delegated admin — the
   service-linked role is what the delegated admin uses.

4. **Leaving stale delegations after account closure.** When a
   delegated admin account is closed, deregister FIRST. Stale
   delegations block re-registration of a new account for the
   same service principal.

## Terraform examples

### Tag policy with enforced_for

```hcl
resource "aws_organizations_policy" "tag_policy" {
  name = "mandatory-tag-policy"
  type = "TAG_POLICIES"
  description = "Enforce Environment and Owner tags"

  content = jsonencode({
    tags = {
      Environment = {
        TagKey        = { Value = "Environment" }
        EnforcedFor   = ["ec2:instance", "s3:bucket"]
        AllowedValues = ["dev", "staging", "production"]
      }
      Owner = {
        TagKey = { Value = "Owner", CaseSensitive = true }
      }
    }
  })
}

resource "aws_organizations_policy_attachment" "tag_policy_root" {
  policy_id = aws_organizations_policy.tag_policy.id
  target_id = "r-xxxx"
}
```

### Backup policy

```hcl
resource "aws_organizations_policy" "backup_policy" {
  name = "org-backup-plan"
  type = "BACKUP_POLICY"
  description = "Default org-wide backup plan for tagged resources"

  content = jsonencode({
    plans = {
      "default-backup-plan" = {
        rules = {
          "default-rule" = {
            rule_backup_vault_name    = "Default"
            schedule_expression       = "cron(0 5 ? * * *)"
            start_backup_window_minutes   = 480
            complete_backup_window_minutes = 10080
            lifecycle = { delete_after_days = 30 }
            target_backup_vaults = [
              { backup_vault_arn = "arn:aws:backup:us-east-1:111122223311:backup-vault:Default" }
            ]
          }
        }
        regions = ["us-east-1"]
      }
    }
    selections = {
      tags = {
        "backup-plan-default" = {
          iam_role_arn = "arn:aws:iam::111122223311:role/AWSBackupDefaultServiceRole"
          tag_key      = "BackupPlan"
          tag_value    = "default"
        }
      }
    }
  })
}

resource "aws_organizations_policy_attachment" "backup_policy_root" {
  policy_id = aws_organizations_policy.backup_policy.id
  target_id = "r-xxxx"
}
```

### AI services opt-out policy

```hcl
resource "aws_organizations_policy" "ai_opt_out" {
  name = "opt-out-all-ai-services"
  type = "AISERVICES_OPT_OUT_POLICY"
  description = "Opt out of all AI services content use"

  content = jsonencode({
    services = {
      default = {
        opt_out_policy = {
          "@odata.type"            = "#AWS.OptOutPolicy#ServicesOptOutPolicyDefault"
          "opt_out_enabled_at_level" = "account"
        }
      }
    }
  })
}

resource "aws_organizations_policy_attachment" "ai_opt_out_root" {
  policy_id = aws_organizations_policy.ai_opt_out.id
  target_id = "r-xxxx"
}
```

### Delegated administrator

```hcl
resource "aws_organizations_delegated_administrator" "access_analyzer" {
  account_id        = "111122223311"
  service_principal = "access-analyzer.amazonaws.com"
}
```
