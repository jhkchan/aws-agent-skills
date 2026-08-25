# Targeting and Priority — Firewall Manager Deployer

Deep reference on FMS policy targeting (Organization, OU, account
scopes, OU auto-expansion), policy priority ordering (first-match
wins), resource tag inclusion/exclusion (exclude overrides include),
and compliance reporting via AWS Config. Loaded on demand by the skill
— kept out of the main SKILL.md body so the provisioning procedure
stays scannable.

## Policy targeting

### Scope options

FMS policies can target the entire Organization, specific OUs, or
individual accounts. The IncludeMap determines the scope.

| Scope | IncludeMap Key | Behavior |
|---|---|---|
| Entire Organization | `ROOT` | All accounts including future |
| Specific OU | `ORG_UNIT` | Accounts in the OU + future additions |
| Individual accounts | `ACCOUNT` | Only listed accounts (no auto-expansion) |

```text
IncludeMap options:
  {"ROOT": ["r-xxxx"]}                      → entire Organization
  {"ORG_UNIT": ["ou-xxxx-yyyy"]}            → one OU
  {"ORG_UNIT": ["ou-aaa-bbb", "ou-ccc-ddd"]} → multiple OUs
  {"ACCOUNT": ["111111111111"]}             → one account
  {"ACCOUNT": ["111111111111", "222222222222"]} → multiple accounts
```

### OU auto-expansion

OU-based targeting is dynamic. When a new account is moved into a
targeted OU, it is automatically included in the policy scope. No
policy update is needed.

```text
Policy targets OU=Workloads:
  Day 1: OU contains accounts 111, 222, 333 → all targeted
  Day 2: account 444 moved into OU → automatically targeted
  Day 3: account 222 moved out of OU → no longer targeted
```

### Account exclusion

Use `ExcludeAccounts` to exclude specific accounts from an OU or
Organization-wide scope.

```json
{
  "includeMap": {"ORG_UNIT": ["ou-xxxx-yyyy"]},
  "excludeAccounts": ["333333333333"]
}
```

Account 333333333333 is in the OU but excluded from the policy.

### Resource tag inclusion/exclusion

Resource tags provide fine-grained resource scoping within accounts.

| Tag Scope | Behavior |
|---|---|
| Include tags | Only resources with these tags are targeted |
| Exclude tags | Resources with these tags are NEVER targeted |
| No tags | All supported resources in scope are targeted |

**Critical rule: exclude tags ALWAYS override include tags.**

```text
Include tags: Environment=production
Exclude tags: ComplianceExempt=true

Resource A: Environment=production, no exclude tag → TARGETED
Resource B: Environment=production, ComplianceExempt=true → EXCLUDED
Resource C: Environment=dev → NOT targeted (include tag mismatch)
Resource D: Environment=production, EnvironmentOverride=temp → TARGETED (include tag matches)
```

### Cross-account and cross-Region scope

FMS policies can span multiple accounts and Regions. For cross-Region
scope, deploy the policy in each Region where resources exist.

```bash
# Deploy in multiple Regions
for REGION in us-east-1 us-west-2 eu-west-1; do
  aws fms put-policy \
    --policy-name "org-waf-common-rules" \
    --region "$REGION" \
    --cli-input-json file://fms-waf-policy.json
done
```

## Policy priority ordering

### First-match wins

When multiple policies of the same type (e.g., two WAF policies) target
overlapping resources, FMS evaluates in priority order. The first
matching policy wins — lower-priority policies do NOT apply to
resources already covered.

```text
WAF Policy Priority Stack:
  Priority 1: org-waf-primary    → targets OU=Prod
  Priority 2: org-waf-secondary  → targets OU=Root (all)

Account in OU=Prod:
  → Evaluated by org-waf-primary (priority 1, first match)
  → org-waf-secondary does NOT apply (already covered)

Account NOT in OU=Prod:
  → org-waf-primary does not match (OU scope excludes it)
  → Evaluated by org-waf-secondary (priority 2)
```

### Priority is per-type

Policy priority is evaluated per-type. A WAF policy at priority 1 and
a security group policy at priority 1 do NOT conflict — they are
different types and both apply independently.

```text
WAF policies:        Priority 1 → Priority 2 → ...
SG policies:         Priority 1 → Priority 2 → ...
NFW policies:        Priority 1 → Priority 2 → ...
Shield policies:     Priority 1 → Priority 2 → ...

Each type has its own independent priority stack.
```

### Reordering priorities

To change the evaluation order, update the policy's priority. FMS
re-evaluates all policies in the new order.

```bash
# List policies in priority order
aws fms list-policies --region us-east-1 \
  --query 'PolicyList[*].{Name:PolicyName,Type:SecurityServicePolicyData.Type,Pri:ResourceTags}' \
  --output table

# Update a policy's priority (via put-policy with new priority value)
aws fms put-policy \
  --policy-id <policy-id> \
  --policy-name "org-waf-secondary" \
  --priority 3 \
  ...
```

## Compliance reporting via AWS Config

### Compliance states

FMS evaluates each resource against the policy and reports compliance:

| State | Meaning |
|---|---|
| COMPLIANT | Resource meets policy requirements |
| NON_COMPLIANT | Resource violates the policy |
| INFORMATIONAL | Resource is being evaluated or is exempt |

### Querying compliance

```bash
# Get compliance detail for a policy in a specific account
aws fms get-compliance-detail \
  --policy-id <policy-id> \
  --member-account 111111111111 \
  --region us-east-1

# List compliance status across all member accounts
aws fms list-compliance-status \
  --policy-id <policy-id> \
  --region us-east-1

# List violation details
aws fms list-violation-details \
  --policy-id <policy-id> \
  --member-accounts 111111111111 \
  --region us-east-1
```

### AWS Config prerequisite

AWS Config MUST be enabled in every member account for FMS to evaluate
compliance. Without Config, resources show as "unknown" compliance.

```bash
# Verify Config is enabled (run in each member account)
aws configservice describe-configuration-recorders --region us-east-1

# Enable Config if not already
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::111:role/ConfigRole \
  --recording-group allSupported=true,includeGlobalResourceTypes=true \
  --region us-east-1
```

## Common targeting pitfalls

1. **Targeting the admin account.** The FMS admin account cannot be
   both manager and target. Exclude it explicitly if it is inside a
   targeted OU.

2. **Forgetting that OU targeting auto-expands.** New accounts moved
   into the OU are automatically targeted. This is usually desired but
   can surprise operators who add accounts to the OU without realizing
   FMS policies will apply.

3. **Assuming include tags are additive.** Include tags are a filter —
   only resources with the specified tags are targeted. Without include
   tags, ALL supported resources in scope are targeted.

4. **Assuming exclude tags are symmetric with include tags.** Exclude
   tags ALWAYS override include tags. A resource with both is excluded.
   This is the most common tag-scoping surprise.

5. **Not deploying policies in all needed Regions.** FMS policies are
   Regional. If resources exist in multiple Regions, deploy the policy
   in each Region.

6. **Forgetting that AWS Config is required.** Without Config, FMS
   cannot evaluate compliance. Resources show as "unknown," not
   "compliant." Ensure Config is enabled in all target accounts.

## Step 10 — Policy priority ordering
When multiple policies of the same type target overlapping resources,
FMS evaluates in priority order. The first matching policy wins.

| Priority | Behavior |
|---|---|
| Lower number = higher priority | Evaluated first |
| First match wins | Resource is managed by the first matching policy |
| Lower-priority policies | NOT applied to resources already covered |

**Reorder priorities:**

```bash
# List policies in priority order
aws fms list-policies --region us-east-1 \
  --query 'PolicyList[*].{Name:PolicyName,Type:SecurityServicePolicyData.Type,Pri:Priority}' \
  --output table

# Reorder (use put-apps-list or update policy priority)
# Priority is set when creating/updating the policy
```
