# Example usage: multi-account-governance-automator

A walkthrough showing the skill designing a full greenfield 50-account
governance baseline with Control Tower, SCPs, delegated administration,
and IAM Identity Center. The skill emits an AUTOMATED verdict.

## Input (user prompt)

> Design a multi-account governance baseline for our greenfield AWS
> organization. We're targeting 50 accounts, PCI compliance, and want
> Control Tower as the landing surface. Include OUs, root-level SCPs,
> delegated admin in an audit account, CloudTrail org trail to log-archive,
> Identity Center with a break-glass path, and Resource Explorer.

## Skill output

```text
STRUCTURE:
  Org status: all-features
  OU depth: 3 (root -> BU -> environment)
  Foundational accounts: audit=111111111111, log-archive=222222222222
  Management account MFA: yes (virtual MFA, no access keys)
CONTROLS:
  - [PASS] Guardrail SCP "deny-leave-org" attached at root r-abc0
  - [PASS] SCP denies organizations:LeaveOrganization
  - [PASS] SCP denies root-account actions except iam:CreateVirtualMFADevice
  - [PASS] Region throttle SCP at Workloads-Prod OU (us-east-1, eu-west-1 only)
  - [PASS] Deny-list SCP at Sandbox OU (blocks QLDB, Macie2, AlexaForBusiness)
  - [PASS] SCP inheritance reviewed — Deny at child OU overrides root Allow
DELEGATION:
  - [PASS] GuardDuty delegated to audit account 111111111111
  - [PASS] Security Hub delegated to audit account 111111111111 (CIS + Foundational)
  - [PASS] Config aggregator OrgConfigAggregator in audit account (org source, AllRegions=true)
  - [PASS] CloudTrail org-trail delivering to log-archive S3 bucket org-trail-logs-2222
  - [PASS] Access Analyzer delegated to audit account
SHARING:
  - [PASS] IAM Identity Center with AWSAdministratorAccess (1h) + AWSReadOnlyAccess (4h)
  - [PASS] Break-glass path: EmergencyAdmin permission set, sealed envelope, tested 2026-07-15
  - [PASS] Resource Explorer aggregator index in audit account, view CrossAccountView
  - [PASS] RAM shares scoped to org (allow-external-principals=false on all 4 shares)
VERDICT: AUTOMATED
FINDINGS:
  - [INFO] All 50 member accounts enrolled in GuardDuty, Security Hub, Config aggregator
  - [INFO] Account Factory vending via Service Catalog product "ct-account-factory"
  - [WARN] Detective not enabled — enable if investigation graph is a requirement
  - [WARN] Macie not enabled — enable if PII detection in S3 is a requirement
REMEDIATION:
  1. Enable Detective: aws detective enable-organization-admin-account --admin-account-id 111111111111
  2. Enable Macie: aws macie2 enable-organization-admin-account --admin-account-id 111111111111
```

## What the skill caught that a generic assistant misses

1. **SCP inheritance is intersectional.** A generic assistant may say
   "Allow at root overrides Deny at child OU" — wrong. The skill
   documents that Deny always wins, and recommends attaching Deny-list
   SCPs at the workload OU level, not relying on root-level Allow.

2. **Management account is NOT governed by SCPs.** A generic assistant
   may suggest running GuardDuty admin from the management account. The
   skill delegates to the audit account — the management account should
   hold zero workload.

3. **Config aggregator must use OrganizationAggregationSource.** A
   generic assistant may use AccountAggregationSources (manual add per
   account). The skill uses the org source — auto-discovers new member
   accounts, no manual maintenance.

4. **CloudTrail org trail bucket policy uses aws:PrincipalOrgID.** A
   generic assistant may enumerate account IDs. The skill uses
   aws:PrincipalOrgID — new accounts auto-covered, no policy update
   needed.

5. **Break-glass path is mandatory.** A generic assistant may skip this.
   The skill requires an EmergencyAdmin permission set on the management
   account, sealed envelope, tested quarterly — Identity Center outages
   otherwise lock you out of the org.

6. **RAM shares default to allow-external-principals=false.** A generic
   assistant may leave the default or set it to true. The skill scopes
   to org members only — prevents unintended external principals from
   accepting shares.

## Slash-command invocation

```
/aws:automate-multi-account-governance
```

Or via the orchestrator:

```
/aws:pipeline
You: "stand up a 50-account org with audit + log-archive, PCI compliance"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the governance baseline, validate the posture:

```bash
# Verify Organizations is all-features
aws organizations describe-organization \
  --query 'Organization.FeatureSet' --profile default

# Verify root-level SCPs
aws organizations list-policies-for-target \
  --target-id r-abc0 --filter SERVICE_CONTROL_POLICY \
  --query 'Policies[*].Name' --profile default

# Verify GuardDuty delegated admin
aws guardduty list-organization-admin-accounts \
  --query 'AdminAccounts[*].AdminAccountId' --profile default

# Verify Config aggregator
aws configservice describe-configuration-aggregators \
  --query 'ConfigurationAggregators[*].Name' --profile default

# Verify CloudTrail org trail
aws cloudtrail describe-trails \
  --query 'trailList[?IsOrganizationTrail==`true`].Name' --profile default

# Verify Identity Center instance
aws sso-admin list-instances \
  --query 'Instances[*].InstanceArn' --profile default

# Verify Resource Explorer aggregator
aws resource-explorer-2 get-index \
  --query 'Index.Type' --profile default
# Must be "AGGREGATOR"
```
