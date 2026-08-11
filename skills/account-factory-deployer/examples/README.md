# End-to-End Example: Control Tower Account Factory Deployment

A walkthrough showing how to use the `account-factory-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are vending a new production data platform account via Control
Tower Account Factory with SSO, Guardrails, custom baseline, and
alternate contacts. The deployment needs:

- Account name: data-platform-prod
- Root email: aws+prod-data-platform@company.com
- Target OU: Custom (DataPlatform) (ou-bbb-ccc)
- SSO: DataEngineerAccess assigned to DataPlatformTeam group
- Custom baseline: CustomBaseline-VPC (VPC with subnets)
- Alternate contacts: Billing, Security, Operations
- Management account: 123456789012, Region: us-east-1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-account-factory
```

Then paste the requirements.

### Option B: Natural language

```
You: "Vend a new data-platform-prod account via Account Factory
      into the DataPlatform OU. Assign DataEngineerAccess to
      the DataPlatformTeam group. Set up custom VPC baseline
      and alternate contacts."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "vending a new account via account factory"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
ACCOUNT_FACTORY: data-platform-prod (123456789012) in OU DataPlatform (ou-bbb-ccc)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Account email: aws+prod-data-platform@company.com — UNIQUE
  [✓] Account name: data-platform-prod — UNIQUE
  [✓] Target OU: Custom (DataPlatform) (ou-bbb-ccc) — REGISTERED
  [✓] Service Catalog product: prod-aaa111 — AVAILABLE
  [✓] Account provisioned: 123456789012 — ACTIVE
  [✓] Guardrails (SCP): 8 preventive controls inherited from OU
  [✓] Guardrails (Detective): 12 Config rules deployed
  [✓] Baseline StackSets: AWSControlTowerLogging — DEPLOYED, AWSControlTowerSecurity — DEPLOYED
  [✓] SSO: Identity Center instance arn:aws:sso:::instance/ssoins-12345
  [✓] Permission sets: DataEngineerAccess assigned to DataPlatformTeam
  [✓] SSO provisioning: DataEngineerAccess provisioned — SUCCEEDED
  [✓] Alternate contacts: BILLING ✓, SECURITY ✓, OPERATIONS ✓
  [✓] Custom baseline: CustomBaseline-VPC — DEPLOYED
  [✓] Compliance status: compliant
  [✓] Tags: Environment=production, OU=DataPlatform, Owner=PlatformTeam
VERIFICATION_COMMANDS:
  aws organizations describe-account --account-id 123456789012
  aws organizations list-policies-for-target --target-id 123456789012 --filter SERVICE_CONTROL_POLICY
  aws cloudformation list-stack-instances --stack-set-name AWSControlTowerLogging
  aws sso-admin list-account-assignments --instance-arn arn:aws:sso:::instance/ssoins-12345 --account-id 123456789012
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Get the Account Factory Service Catalog product
PRODUCT_ID=$(aws servicecatalog search-products \
  --filters FullTextSearch="AWS Control Tower Account Factory Factory" \
  --query 'ProductViewSummaries[0].ProductId' --output text)

ARTIFACT_ID=$(aws servicecatalog describe-product \
  --id "$PRODUCT_ID" \
  --query 'ProvisioningArtifacts[0].Id' --output text)

# Step 2: Provision the account via Service Catalog
aws servicecatalog provision-product \
  --product-id "$PRODUCT_ID" \
  --provisioning-artifact-id "$ARTIFACT_ID" \
  --provisioned-product-name "data-platform-prod" \
  --provisioning-parameters '[
    {"Key":"AccountEmail","Value":"aws+prod-data-platform@company.com"},
    {"Key":"AccountName","Value":"data-platform-prod"},
    {"Key":"ManagedOrganizationalUnit","Value":"Custom (DataPlatform)"},
    {"Key":"SSOUserEmail","Value":"platform-lead@company.com"},
    {"Key":"SSOUserFirstName","Value":"Platform"},
    {"Key":"SSOUserLastName","Value":"Lead"}
  ]'

# Step 3: Wait for provisioning to complete (5-30 min)
aws servicecatalog describe-provisioned-product \
  --name "data-platform-prod" \
  --query 'ProvisionedProductDetail.Status' --output text
# Expected: AVAILABLE

# Step 4: Verify Guardrail inheritance (SCPs)
ACCOUNT_ID="123456789012"
aws organizations list-policies-for-target \
  --target-id "$ACCOUNT_ID" \
  --filter SERVICE_CONTROL_POLICY \
  --output table

# Step 5: Verify baseline StackSets
aws cloudformation list-stack-instances \
  --stack-set-name "AWSControlTowerLogging" \
  --query "Summaries[?Account=='$ACCOUNT_ID'].Status" \
  --output table

# Step 6: Set alternate contacts
aws account put-alternate-contact \
  --account-id "$ACCOUNT_ID" \
  --alternate-contact-type "BILLING" \
  --email-address "billing@company.com" \
  --name "Finance Team" \
  --phone-number "+1-555-0100" \
  --title "Accounts Payable"

aws account put-alternate-contact \
  --account-id "$ACCOUNT_ID" \
  --alternate-contact-type "SECURITY" \
  --email-address "security@company.com" \
  --name "Security Operations" \
  --phone-number "+1-555-0200" \
  --title "SOC"

aws account put-alternate-contact \
  --account-id "$ACCOUNT_ID" \
  --alternate-contact-type "OPERATIONS" \
  --email-address "ops@company.com" \
  --name "DevOps Team" \
  --phone-number "+1-555-0300" \
  --title "Platform Engineering"

# Step 7: Assign SSO permission set to group
aws sso-admin create-account-assignment \
  --instance-arn "arn:aws:sso:::instance/ssoins-12345" \
  --target-id "$ACCOUNT_ID" \
  --target-type "AWS_ACCOUNT" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --principal-type "GROUP" \
  --principal-id "$GROUP_ID"

# Step 8: Provision the permission set to the account (CRITICAL)
aws sso-admin provision-permission-set \
  --instance-arn "arn:aws:sso:::instance/ssoins-12345" \
  --permission-set-arn "$PERMISSION_SET_ARN" \
  --target-id "$ACCOUNT_ID" \
  --target-type "AWS_ACCOUNT"
```

---

## Step 4 — Post-deployment verification

```bash
# Verify account is ACTIVE
aws organizations describe-account \
  --account-id "$ACCOUNT_ID" \
  --query 'Account.Status' --output text
# Expected: ACTIVE

# Verify SCPs are inherited
aws organizations list-policies-for-target \
  --target-id "$ACCOUNT_ID" \
  --filter SERVICE_CONTROL_POLICY \
  --output table

# Verify baseline StackSets are deployed
for stackset in AWSControlTowerLogging AWSControlTowerSecurity; do
  echo "=== $stackset ==="
  aws cloudformation list-stack-instances \
    --stack-set-name "$stackset" \
    --query "Summaries[?Account=='$ACCOUNT_ID'].{Region:Region,Status:StackInstanceStatus}" \
    --output table
done

# Verify SSO assignments
aws sso-admin list-account-assignments \
  --instance-arn "arn:aws:sso:::instance/ssoins-12345" \
  --account-id "$ACCOUNT_ID" \
  --output table

# Verify alternate contacts
aws account get-alternate-contact \
  --account-id "$ACCOUNT_ID" \
  --alternate-contact-type "BILLING" \
  --query 'AlternateContact.EmailAddress' --output text
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Account creation | Raw Organizations CreateAccount | Service Catalog provision-product | Raw accounts miss Guardrails, baselines, and SSO enrollment |
| OU registration | Assumes all OUs get Guardrails | Verifies OU is registered | Only registered OUs get Guardrails and baselines |
| SSO provisioning | Assignment only (no provision step) | Assignment + provision-permission-set | Assignment without provisioning = no access |
| Alternate contacts | Not set | Set via put-alternate-contact | Not inherited from OU; must be per-account |
| Email uniqueness | Not verified | Verified before provisioning | Duplicate emails fail provisioning |
| Baseline StackSets | Not verified | StackSet deployment verified | Failed StackSets leave compliance gaps |
| OU moves | SCPs not re-verified | SCPs verified after any OU move | SCPs change immediately on OU move |

---

## Related artifacts

- **Skill definition:** `skills/account-factory-deployer/SKILL.md`
- **Guardrails and baseline guide:** `skills/account-factory-deployer/references/guardrails-and-baseline.md`
- **SSO and lifecycle guide:** `skills/account-factory-deployer/references/sso-and-lifecycle.md`
- **Slash command:** `commands/aws/deploy-account-factory.md`
- **Eval suite:** `skills/account-factory-deployer/evals/evals.json`
- **Legacy test cases:** `skills/account-factory-deployer/eval/test-cases.yaml`
