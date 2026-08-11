# End-to-End Example: Organizations Account Deployment

A walkthrough showing how to use the `organizations-account-deployer`
skill from invocation through verification. Mirrors the
structured-eval pattern of shipping a concrete worked example per
skill.

---

## Scenario

You are provisioning a production AWS member account via Control
Tower Account Factory with a full baseline. The account needs:

- Creation path: Control Tower Account Factory
- Root email: `aws+prod-workload@yourdomain.com` (distribution list)
- IAM role name: `OrganizationAccountAccessRole`
- OU placement: `ou-prod-abc` (inherits SCP and tag policy)
- SCP: `DenyUnapprovedRegions` (via OU inheritance)
- Tag policy: `CostCenterRequired` (via OU inheritance)
- CloudTrail org trail: `org-audit-trail` (inherited)
- IAM Identity Center: `ProductionAdmins` permission set assigned to
  the `Eng-Prod` group
- Config aggregator: `org-aggregator` (delegated admin
  123456789012)
- Alternate contacts: Billing, Security, Operations
- Budget: $5000/month, alert at 80%
- RAM share: `org-tgw-share`

Account name: `prod-workload-use1`
Region: `us-east-1`
Management account: `123456789012`

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-organizations-account
```

Then paste the requirements.

### Option B: Natural language

```
You: "Provision a production AWS account 'prod-workload-use1' via
      Control Tower Account Factory. Root email
      aws+prod-workload@yourdomain.com. Place in OU ou-prod-abc so it
      inherits DenyUnapprovedRegions SCP and CostCenterRequired tag
      policy. Assign ProductionAdmins permission set to Eng-Prod
      group. Config aggregator in delegated admin 123456789012.
      Alternate contacts: finops@, security@, ops@yourdomain.com.
      Budget $5000/month at 80%. Share tgw-0abc123 via RAM.
      Management account: 123456789012."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a production aws account via control tower"
```

Output:

```
[Phase: Deploy | Skills routed: organizations-account-deployer]

Primary route: organizations-account-deployer (score: 22)
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
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
  [✓] Alternate contacts: Billing=finops@, Security=security@, Operations=ops@yourdomain.com
  [✓] Budget: prod-workload-budget ($5000/month, alert at 80%)
  [✓] RAM shares: org-tgw-share
  [✓] Baseline: Account Factory blueprint (VPC, guardrails, SSO, Config)
VERIFICATION_COMMANDS:
  aws organizations describe-account --account-id 111122223333
  aws organizations list-policies-for-target --target-id 111122223333
  aws cloudtrail list-trails --query 'Trails[?IsOrganizationTrail==`true`]'
  aws sso-admin list-account-assignments --instance-arn <arn> --account-id 111122223333
```

---

## Step 3 — Provisioning commands

The skill generates the copy-pasteable CLI sequence (from
`references/provisioning-cli-commands.md`):

```bash
# Step 1: Create the account via Control Tower Account Factory
aws controltower create-landing-zone-operation \
  --landing-zone-identifier <lz-id> \
  --operation-type PROVISION_ACCOUNT \
  --parameters file://account-factory-params.json

# (For Organizations create-account path:)
REQUEST_ID=$(aws organizations create-account \
  --email "aws+prod-workload@yourdomain.com" \
  --account-name "prod-workload-use1" \
  --role-name "OrganizationAccountAccessRole" \
  --iam-user-access-to-billing ALLOW \
  --query 'CreateAccountStatus.Id' --output text)

aws organizations describe-create-account-status \
  --create-account-request-id "$REQUEST_ID"

# Step 2: Move the account into the prod OU (inherits SCP and tag policy)
aws organizations move-account \
  --account-id 111122223333 \
  --source-parent-id <root-id> \
  --destination-parent-id ou-prod-abc

# Step 3: Assign the ProductionAdmins permission set
aws sso-admin create-account-assignment \
  --instance-arn arn:aws:sso:us-east-1:123456789012:instance/ssoins-0123 \
  --target-id 111122223333 \
  --target-type AWS_ACCOUNT \
  --permission-set-arn <permission-set-arn> \
  --principal-type GROUP \
  --principal-id <group-id>

# Step 4: Set alternate contacts and budget
aws account put-alternate-contact \
  --account-id 111122223333 \
  --alternate-contact-type BILLING \
  --email-address finops@yourdomain.com --name "FinOps Team" \
  --phone-number "+1-555-0100" --title "Finance Operations"

aws budgets create-budget --account-id 111122223333 \
  --budget file://budget.json \
  --notifications-with-subscribers file://notifications.json
```

---

## Step 4 — Post-deployment verification

```bash
# Account state and details
aws organizations describe-account --account-id 111122223333

# Effective SCPs and tag policies (via OU inheritance)
aws organizations list-policies-for-target --target-id 111122223333 \
  --filter SERVICE_CONTROL_POLICY
aws organizations list-policies-for-target --target-id 111122223333 \
  --filter TAG_POLICY

# Org trail
aws cloudtrail list-trails \
  --query 'Trails[?IsOrganizationTrail==`true`]'

# SSO assignments
aws sso-admin list-account-assignments \
  --instance-arn arn:aws:sso:...:instance/ssoins-0123 \
  --account-id 111122223333

# Alternate contacts
aws account get-alternate-contact --account-id 111122223333 \
  --alternate-contact-type BILLING
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Root email | Uses an individual's email | Distribution list | The root email is permanent identity — losing it locks password reset |
| IAM role name | Customized per account | Consistent across org | Mismatched names break cross-account automation silently |
| SCP attachment | Account-level | OU-level (inherited) | Account-level creates drift; OU-level inherits future updates |
| Org trail | Assumes new account is audited | Verifies org trail exists first | New account inherits only if the org trail already exists |
| SSO | Assumes new account is reachable | Permission set assignment required | New account is silent and inaccessible until assignment |
| Billing | "Consolidated = automatic" | Cost Explorer and budgets per account | Consolidated billing does not mean per-account visibility is automatic |
| Creation path | Always `create-account` | Account Factory for production | Bare account needs manual baseline retrofit; Account Factory bakes it in |

---

## Related artifacts

- **Skill definition:** `skills/organizations-account-deployer/SKILL.md`
- **Creation paths guide:** `skills/organizations-account-deployer/references/creation-paths-and-baselines.md`
- **Provisioning CLI commands:** `skills/organizations-account-deployer/references/provisioning-cli-commands.md`
- **Slash command:** `commands/aws/deploy-organizations-account.md`
- **Eval suite:** `skills/organizations-account-deployer/evals/evals.json`
- **Legacy test cases:** `skills/organizations-account-deployer/eval/test-cases.yaml`
