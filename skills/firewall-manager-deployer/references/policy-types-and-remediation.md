# Policy Types and Remediation — Firewall Manager Deployer

Deep reference on FMS policy types (WAF, Security Group, Network
Firewall, Shield Advanced), remediation modes (auto-apply vs monitor-
only), grace period mechanics, and managed rule group lifecycle. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## WAF policy details

### Managed rule groups vs custom rule groups

FMS WAF policies reference managed rule groups (AWS-provided or
marketplace) or custom rule groups. FMS creates the Web ACLs in each
target account; you only specify the rule groups.

**AWS managed rule groups:**

| Rule Group | Purpose | Rules |
|---|---|---|
| AWSManagedRulesCommonRuleSet | Core protection | LFI, RFI, SQLi, XSS, generic RCE |
| AWSManagedRulesKnownBadInputsRuleSet | Known exploits | Log4j, SSRF, bad inputs |
| AWSManagedRulesAmazonIpReputationList | IP reputation | Known malicious IPs |
| AWSManagedRulesSQLiRuleSet | SQL injection | SQLi patterns |
| AWSManagedRulesLinuxRuleSet | Linux exploits | Linux-specific signatures |
| AWSManagedRulesWindowsRuleSet | Windows exploits | Windows-specific signatures |
| AWSManagedRulesWordPressRuleSet | WordPress | WP-specific exploits |
| AWSManagedRulesPHPRuleSet | PHP exploits | PHP-specific signatures |

### Rule group versioning

Managed rule groups are versioned. You can pin to a specific version or
use the default (latest). Version pinning prevents silent rule updates.

```json
{
  "managedRuleGroupStatement": {
    "vendorName": "AWS",
    "name": "AWSManagedRulesCommonRuleSet",
    "version": "Version_2.0"
  }
}
```

**Warning:** the default (no version) uses the latest, which can change
behavior when AWS updates the rule group. Pin to a version for
production stability.

### Pre-process vs post-process rule groups

FMS WAF policies support pre-process and post-process rule groups:

- **Pre-process:** evaluated first, before managed rule groups.
- **Post-process:** evaluated last, after managed rule groups.

Use pre-process for custom blocking rules that should take priority.
Use post-process for rate-limiting or logging rules.

## Security group policy details

### Common mode (SECURITY_GROUPS_COMMON)

Common mode applies the SAME security group rules to all targeted ENIs.
This is useful for enforcing a baseline SG across accounts.

```json
{
  "type": "SECURITY_GROUPS_COMMON",
  "securityGroups": [
    {"id": "sg-baseline-aaa"}
  ]
}
```

The referenced SG must exist in each target account (or FMS creates it
based on the policy definition).

### Content audit mode (SECURITY_GROUPS_CONTENT_AUDIT)

Content audit mode checks existing SGs against audit rules. It does NOT
apply a specific SG — it evaluates existing SGs for compliance.

```json
{
  "type": "SECURITY_GROUPS_CONTENT_AUDIT",
  "securityGroupAction": {"type": "ALLOW"},
  "recursiveSecurityGroupEgressRules": false
}
```

**Audit rule examples:**
- Flag SGs with port 22 open to 0.0.0.0/0
- Flag SGs with port 3389 open to 0.0.0.0/0
- Flag SGs with any port open to 0.0.0.0/0

Nonconforming SGs are reported as NON_COMPLIANT. With auto-remediation,
FMS can automatically remove the nonconforming rules.

## Network Firewall policy details

### Stateless vs stateful rule groups

Network Firewall policies reference stateless and stateful rule groups:

- **Stateless:** evaluated per-packet, no connection tracking. Fast,
  used for L3/L4 filtering.
- **Stateful:** evaluated with connection tracking, deep packet
  inspection. Used for L7 and domain filtering.

### Firewall subnet mappings

Each target account needs firewall subnet mappings for Network Firewall
placement. The firewall is deployed into the specified subnets.

```json
{
  "type": "NETWORK_FIREWALL",
  "networkFirewallStatelessRuleGroupReferences": [
    {"resourceArn": "arn:aws:network-firewall:us-east-1:111:stateless-rulegroup/rs-stateless-aaa"}
  ],
  "networkFirewallStatefulRuleGroupReferences": [
    {"resourceArn": "arn:aws:network-firewall:us-east-1:111:stateful-rulegroup/rs-stateful-bbb"}
  ]
}
```

## Remediation mode details

### Monitor-only (RemediationEnabled=false)

- Reports noncompliant resources in FMS console and via Config.
- NO automatic changes to resources.
- Use for phased rollout, auditing, and understanding compliance
  posture before enforcing.

### Auto-apply (RemediationEnabled=true)

- Automatically creates or modifies resources to comply.
- Grace period (RemediationGracePeriodDays) delays remediation after
  detection.
- Grace period 0 = immediate remediation; 7 = 1 week buffer.

### Grace period mechanics

```text
Day 0: Resource detected as noncompliant
Day 0 to N: Resource is noncompliant, NOT remediated (grace period)
Day N+1: FMS auto-remediates the resource
```

During the grace period, the resource shows as NON_COMPLIANT in the FMS
console. After the grace period, FMS applies the fix.

## Shield Advanced policy details

Shield Advanced policies enable automatic DDoS protection. No
additional configuration beyond the policy is needed — Shield
automatically protects supported resources:

- ALBs and NLBs
- CloudFront distributions
- Route 53 hosted zones
- Global Accelerators
- Elastic IPs

Shield Advanced requires a subscription (1-year commitment). Ensure the
admin account and all target accounts have Shield Advanced enabled.

## Terraform examples

```hcl
# FMS admin account delegation
resource "aws_fms_admin_account" "main" {
  account_id = "111111111111"
}

# FMS WAF policy
resource "aws_fms_policy" "waf_common" {
  name                  = "org-waf-common-rules"
  delete_unused_fm_portals = false
  include_map = {
    org_unit = ["ou-prod-abcdef"]
  }
  remediation_enabled         = true
  remediation_grace_period_days = 7

  security_service_policy_data {
    type = "WAFV2"
    managed_service_data = jsonencode({
      type = "WAFV2"
      preProcessRuleGroups = [
        {
          managedRuleGroupStatement = {
            vendorName = "AWS"
            name       = "AWSManagedRulesCommonRuleSet"
          }
        }
      ]
    })
  }
}

# FMS security group content audit policy
resource "aws_fms_policy" "sg_audit" {
  name = "org-sg-audit-no-ssh-open"
  include_map = {
    account = ["111111111111", "222222222222"]
  }
  remediation_enabled = false

  security_service_policy_data {
    type = "SECURITY_GROUPS_CONTENT_AUDIT"
    managed_service_data = jsonencode({
      type                              = "SECURITY_GROUPS_CONTENT_AUDIT"
      securityGroupAction               = { type = "ALLOW" }
      recursiveSecurityGroupEgressRules = false
    })
  }
}
```

## Common policy-type pitfalls

1. **Using a Web ACL ARN instead of a managed rule group.** FMS creates
   the Web ACLs; you specify the rule groups. Using a Web ACL ARN
   results in an invalid policy configuration.

2. **Forgetting subnet mappings for Network Firewall.** Without
   subnets, the policy deploys but no firewall is created. Resources
   show as NON_COMPLIANT.

3. **Starting with auto-apply on a content audit SG policy.** Content
   audit with auto-apply can automatically REMOVE security group rules
   across all targeted accounts. Always start with monitor-only.

4. **Not version-pinning managed rule groups.** The default (latest)
   version can change behavior when AWS updates the rule group. Pin to
   a version for production stability.

5. **Assuming Shield Advanced policies need resource-level config.**
   Shield Advanced policies auto-protect supported resources. No
   additional resource-level configuration is needed.

## Step 5 — WAF managed rule group association
WAF policies reference managed rule groups (AWS or marketplace) or
custom rule groups. The managed rule group set determines which rules
are applied to all Web ACLs created by the policy.

**Common managed rule groups:**

| Rule Group | Purpose |
|---|---|
| AWSManagedRulesCommonRuleSet | Core rules (LFI, RFI, SQLi, XSS) |
| AWSManagedRulesKnownBadInputsRuleSet | Log4j, SSRF, bad inputs |
| AWSManagedRulesAmazonIpReputationList | Malicious IP reputation |
| AWSManagedRulesSQLiRuleSet | SQL injection |
| AWSManagedRulesLinuxRuleSet | Linux-specific exploits |
| AWSManagedRulesWindowsRuleSet | Windows-specific exploits |
| AWSManagedRulesWordPressRuleSet | WordPress exploits |

**Create a WAF FMS policy:**

```bash
aws fms put-policy \
  --policy-name "org-waf-common-rules" \
  --policy-type "WAFV2" \
  --region us-east-1 \
  --cli-input-json file://fms-waf-policy.json
```

**fms-waf-policy.json structure:**

```json
{
  "PolicyName": "org-waf-common-rules",
  "SecurityServicePolicyData": {
    "Type": "WAFV2",
    "ManagedServiceData": "{\"type\":\"WAFV2\",\"preProcessRuleGroups\":[{\"managedRuleGroupStatement\":{\"vendorName\":\"AWS\",\"name\":\"AWSManagedRulesCommonRuleSet\"}}]}"
  },
  "IncludeMap": {"ORG_UNIT": ["ou-xxxx-yyyy"]},
  "RemediationEnabled": true,
  "RemediationGracePeriodDays": 7,
  "DeleteUnusedFMSPortals": false
}
```

**Common mistake:** using a standalone WAF Web ACL ARN instead of a
managed rule group. FMS creates the Web ACLs; you only specify the rule
groups.

## Step 6 — Security group policies (common vs content audit)
Security group policies have two modes:

| Mode | Behavior | Use Case |
|---|---|---|
| Common | Applies the SAME security group rules to all targeted ENIs | Enforce a baseline SG across accounts |
| Content Audit | Checks existing SGs against audit rules; flags/remediates nonconforming SGs | Ensure SGs comply with policy (e.g., no port 22 open to 0.0.0.0/0) |

**Common SG policy:**

```json
{
  "PolicyName": "org-sg-baseline",
  "SecurityServicePolicyData": {
    "Type": "SECURITY_GROUPS_COMMON",
    "ManagedServiceData": "{\"type\":\"SECURITY_GROUPS_COMMON\",\"securityGroups\":[{\"id\":\"sg-aaa11122\"}]}"
  },
  "IncludeMap": {"ORG_UNIT": ["ou-xxxx-yyyy"]},
  "RemediationEnabled": true
}
```

**Content audit SG policy (audit existing SGs):**

```json
{
  "PolicyName": "org-sg-audit-no-ssh-open",
  "SecurityServicePolicyData": {
    "Type": "SECURITY_GROUPS_CONTENT_AUDIT",
    "ManagedServiceData": "{\"type\":\"SECURITY_GROUPS_CONTENT_AUDIT\",\"securityGroupAction\":{\"type\":\"ALLOW\"},\"recursiveSecurityGroupEgressRules\":false}"
  },
  "IncludeMap": {"ORG_UNIT": ["ou-xxxx-yyyy"]},
  "RemediationEnabled": false
}
```

## Step 7 — Network Firewall policy deployment
Network Firewall policies deploy managed Network Firewall firewalls in
target accounts. Each target account needs firewall subnet mappings for
firewall placement.

```bash
aws fms put-policy \
  --policy-name "org-nfw-inspection" \
  --policy-type "NETWORK_FIREWALL" \
  --region us-east-1 \
  --cli-input-json file://fms-nfw-policy.json
```

**fms-nfw-policy.json structure:**

```json
{
  "PolicyName": "org-nfw-inspection",
  "SecurityServicePolicyData": {
    "Type": "NETWORK_FIREWALL",
    "ManagedServiceData": "{\"type\":\"NETWORK_FIREWALL\",\"networkFirewallStatelessRuleGroupReferences\":[],\"networkFirewallStatefulRuleGroupReferences\":[]}"
  },
  "IncludeMap": {"ORG_UNIT": ["ou-xxxx-yyyy"]},
  "RemediationEnabled": true,
  "RemediationGracePeriodDays": 14
}
```

## Step 8 — Shield Advanced policy deployment
Shield Advanced policies enable automatic DDoS protection for supported
resources in targeted accounts. No additional configuration is needed
beyond the policy — Shield automatically protects ALBs, NLBs,
CloudFront distributions, Route53 hosted zones, and Global Accelerators.

```bash
aws fms put-policy \
  --policy-name "org-shield-advanced" \
  --policy-type "SHIELD_ADVANCED" \
  --region us-east-1 \
  --cli-input-json file://fms-shield-policy.json
```

**fms-shield-policy.json structure:**

```json
{
  "PolicyName": "org-shield-advanced",
  "SecurityServicePolicyData": {
    "Type": "SHIELD_ADVANCED"
  },
  "IncludeMap": {"ORG_UNIT": ["ou-xxxx-yyyy"]},
  "RemediationEnabled": true
}
```
