# End-to-End Example: Firewall Manager Deployment

A walkthrough showing how to use the `firewall-manager-deployer` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an FMS WAF policy with managed rule groups
targeting the Prod OU, with auto-remediation and include/exclude tags.
The policy needs:

- FMS admin account: 111111111111 (delegated)
- Target: OU ou-prod-abcdef
- Region: us-east-1
- Managed rule groups: AWSManagedRulesCommonRuleSet, AWSManagedRulesKnownBadInputsRuleSet
- Remediation: auto-apply with 7-day grace period
- Include tags: Environment=production
- Exclude tags: ComplianceExempt=true
- Policy priority: 1

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-firewall-manager
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an FMS WAF policy targeting OU ou-prod-abcdef in
      us-east-1. Admin account 111111111111. Use
      AWSManagedRulesCommonRuleSet. Auto-remediation with 7-day
      grace. Include Environment=production, exclude
      ComplianceExempt=true."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create an fms waf policy"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
FMS_POLICY: org-waf-common-rules (type: WAFV2)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] FMS admin account: 111111111111 (delegated)
  [✓] AWS Organizations: enabled (management account 000000000000)
  [✓] AWS Config: enabled in all target accounts
  [✓] Policy type: WAFV2
  [✓] Target scope: ORG_UNIT (ou-prod-abcdef)
  [✓] Remediation: auto-apply (grace: 7 days)
  [✓] Managed rule groups: AWSManagedRulesCommonRuleSet, AWSManagedRulesKnownBadInputsRuleSet
  [✓] Include tags: Environment=production
  [✓] Exclude tags: ComplianceExempt=true
  [✓] Policy priority: 1 (first-match evaluation)
  [✓] Compliance reporting: AWS Config (COMPLIANT|NON_COMPLIANT|INFORMATIONAL)
VERIFICATION_COMMANDS:
  aws fms list-policies --region us-east-1
  aws fms get-policy --policy-id <policy-id> --region us-east-1
  aws fms list-compliance-status --policy-id <policy-id> --region us-east-1
  aws fms get-admin-account --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Verify FMS admin account is delegated
aws fms get-admin-account --region us-east-1
# Expected: { AdminAccount: "111111111111" }

# Step 2: Create the FMS WAF policy
aws fms put-policy \
  --policy-name "org-waf-common-rules" \
  --region us-east-1 \
  --cli-input-json '{
    "PolicyName": "org-waf-common-rules",
    "SecurityServicePolicyData": {
      "Type": "WAFV2",
      "ManagedServiceData": "{\"type\":\"WAFV2\",\"preProcessRuleGroups\":[{\"managedRuleGroupStatement\":{\"vendorName\":\"AWS\",\"name\":\"AWSManagedRulesCommonRuleSet\"}},{\"managedRuleGroupStatement\":{\"vendorName\":\"AWS\",\"name\":\"AWSManagedRulesKnownBadInputsRuleSet\"}}]}"
    },
    "IncludeMap": {"ORG_UNIT": ["ou-prod-abcdef"]},
    "RemediationEnabled": true,
    "RemediationGracePeriodDays": 7,
    "IncludeResourceTags": [{"Key": "Environment", "Value": "production"}],
    "ExcludeResourceTags": [{"Key": "ComplianceExempt", "Value": "true"}],
    "DeleteUnusedFMSPortals": false
  }'

# Step 3: Verify policy was created
aws fms list-policies --region us-east-1 \
  --query 'PolicyList[?PolicyName==`org-waf-common-rules`]'

# Step 4: Check compliance status (after 15-30 minutes)
aws fms list-compliance-status \
  --policy-id <policy-id> \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# FMS admin account — should be delegated
aws fms get-admin-account --region us-east-1

# Policy details — verify type, scope, remediation
aws fms get-policy --policy-id <policy-id> --region us-east-1

# Compliance status — verify resources are being evaluated
aws fms list-compliance-status --policy-id <policy-id> --region us-east-1

# Violation details for a specific account
aws fms get-compliance-detail \
  --policy-id <policy-id> \
  --member-account 111111111111 \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Admin delegation | Not checked | Verified with get-admin-account | Without delegation, put-policy fails with AccessDeniedException |
| Remediation mode | Defaults to auto-apply immediately | Monitor-only first, then auto-apply with grace | Auto-apply on a new policy can cause unexpected resource changes |
| Grace period | Not set | Explicit grace period (e.g., 7 days) | Grace period gives resources time to comply before force-fix |
| Policy priority | Not considered | First-match-wins evaluation verified | Lower-priority policies silently do NOT apply to covered resources |
| Exclude tags | Not checked | Exclude tags override include tags | A resource with both include and exclude tags is excluded |
| AWS Config | Assumed enabled | Verified in all target accounts | Without Config, resources show as "unknown" compliance |
| Managed rule group versioning | Uses default (latest) | Version-pinned for stability | Default version can change behavior when AWS updates rules |

---

## Related artifacts

- **Skill definition:** `skills/firewall-manager-deployer/SKILL.md`
- **Policy types and remediation guide:** `skills/firewall-manager-deployer/references/policy-types-and-remediation.md`
- **Targeting and priority guide:** `skills/firewall-manager-deployer/references/targeting-and-priority.md`
- **Slash command:** `commands/aws/deploy-firewall-manager.md`
- **Eval suite:** `skills/firewall-manager-deployer/evals/evals.json`
- **Legacy test cases:** `skills/firewall-manager-deployer/eval/test-cases.yaml`
