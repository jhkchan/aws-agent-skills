---
description: Provision an AWS Organizations member account (via Organizations create-account or Control Tower Account Factory) with production defaults (root email, IAM role, SCP/tag policy, org trail, IAM Identity Center SSO, billing, baselines). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create aws account"
  - "provision aws account"
  - "organizations create-account"
  - "control tower account factory"
  - "account factory"
  - "vending machine account"
  - "organizationaccountaccessrole"
  - "cross-account admin role"
  - "consolidated billing account"
  - "sso permission set"
  - "iam identity center"
  - "scp assignment"
  - "tag policy"
  - "org trail"
  - "cloudtrail organization trail"
  - "account baseline"
  - "landing zone account"
  - "aws_organizations_account"
  - "aws_controltower_account"
  - "terraform organizations account"
  - "ram share account"
  - "alternate contact billing"
routes_to: organizations-account-deployer
---

# /aws:deploy-organizations-account

Activate the `organizations-account-deployer` skill and provision an
AWS Organizations member account (via `create-account` or Control
Tower Account Factory) with production-grade defaults.

## What it does

The skill walks a 10-step provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Creation path (Organizations create-account vs Control Tower Account Factory)
2. Account identity (root email, account name, IAM role name)
3. Cross-account admin role (OrganizationAccountAccessRole)
4. Billing + cost (consolidated billing, budgets, alternate contacts)
5. SCP + tag policy attachment (guardrails at correct scope)
6. CloudTrail org trail propagation
7. IAM Identity Center SSO (permission sets + account assignments)
8. Account baselines (Config aggregation, Config rules, RAM shares)
9. Terraform / IaC vending (aws_organizations_account, Account Factory as code)
10. Latest features (Account Factory custom baselines, AWS RAM)

## When to use

- You need to create a new AWS member account with production defaults.
- You are designing an account-vending / landing-zone workflow.
- You need to wire OrganizationAccountAccessRole cross-account access.
- You need to attach SCPs and tag policies to a new account (at the
  correct scope: root, OU, or account).
- You need to propagate a CloudTrail organization trail across the
  org.
- You need to assign IAM Identity Center SSO permission sets to a new
  account.
- You want to validate that an account design meets production
  baseline.
- You need copy-pasteable provisioning commands or Terraform templates.

## How to invoke

### Slash command

```
/aws:deploy-organizations-account
```

Then provide: account name, root email (distribution list), creation
path (Organizations create-account or Control Tower Account Factory),
OU placement, IAM role name, governance intent (SCP, tag policy),
billing posture, SSO permission set, audit posture (org trail), and
any optional features (Config aggregator, RAM share, budget,
alternate contacts).

### Natural language

Any of these routes to the same skill:

- "create a production AWS account via Control Tower Account Factory"
- "provision a member account with consolidated billing"
- "vending a landing zone account with an SCP and tag policy"
- "assign an SSO permission set to a new account"
- "wire OrganizationAccountAccessRole for a new member account"

### CLI routing

```bash
node cli/bin/cli.js route "create an aws account via organizations"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or
baseline an AWS member account. The output checklist feeds into
verification pipelines and governance skills (e.g.,
organizations-scp-auditor).

## Example

```
You: /aws:deploy-organizations-account

     Provision a production AWS account "prod-workload-use1" via
     Control Tower Account Factory. Root email
     aws+prod-workload@yourdomain.com. Place in OU ou-prod-abc so it
     inherits DenyUnapprovedRegions SCP and CostCenterRequired tag
     policy. Assign ProductionAdmins permission set to Eng-Prod
     group. Config aggregator in delegated admin 123456789012.
     Alternate contacts: finops@, security@, ops@yourdomain.com.
     Budget $5000/month at 80%. Share tgw-0abc123 via RAM.
     Management account: 123456789012.

Skill:
  ACCOUNT: prod-workload-use1
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Creation path: Control Tower Account Factory
    [✓] Root email: aws+prod-workload@yourdomain.com
    [✓] IAM role name: OrganizationAccountAccessRole
    [✓] Billing: Consolidated (payer: 123456789012)
    [✓] SCP attached: DenyUnapprovedRegions (OU ou-prod-abc)
    [✓] Tag policy attached: CostCenterRequired (OU ou-prod-abc)
    [✓] CloudTrail org trail: org-audit-trail (inherited)
    [✓] IAM Identity Center: ProductionAdmins assigned to group Eng-Prod
    [✓] Config aggregator: org-aggregator (delegated admin: 123456789012)
    [✓] Budget: prod-workload-budget ($5000/month, alert at 80%)
    [✓] RAM shares: org-tgw-share
    [✓] Baseline: Account Factory blueprint (VPC, guardrails, SSO, Config)
  VERIFICATION_COMMANDS:
    aws organizations describe-account --account-id <account-id>
    aws organizations list-policies-for-target --target-id <account-id>
    aws cloudtrail list-trails --query 'Trails[?IsOrganizationTrail==`true`]'
    aws sso-admin list-account-assignments --instance-arn <arn> --account-id <account-id>
```

## References

- Skill definition: `skills/organizations-account-deployer/SKILL.md`
- Creation paths guide: `skills/organizations-account-deployer/references/creation-paths-and-baselines.md`
- Provisioning CLI commands: `skills/organizations-account-deployer/references/provisioning-cli-commands.md`
- Eval suite: `skills/organizations-account-deployer/evals/evals.json`
