---
description: Provision an AWS Firewall Manager (FMS) policy with production-grade defaults (WAF, Security Group, Network Firewall, Shield Advanced; OU-based targeting; remediation mode; managed rule groups; policy priority). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create fms policy"
  - "deploy fms policy"
  - "firewall manager policy"
  - "fms waf policy"
  - "fms security group policy"
  - "fms network firewall policy"
  - "fms shield advanced"
  - "fms remediation"
  - "fms managed rule groups"
  - "fms ou targeting"
  - "fms policy priority"
  - "firewall manager"
  - "fms policy"
routes_to: firewall-manager-deployer
---

# /aws:deploy-firewall-manager

Activate the `firewall-manager-deployer` skill and provision an AWS
Firewall Manager policy with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Administrator account delegation (FMS admin setup)
2. Policy type selection (WAF, SG, NFW, Shield Advanced)
3. AWS Organizations targeting (OU vs account scope)
4. Remediation mode (auto-apply vs monitor-only + grace period)
5. WAF managed rule group association
6. Security group policies (common vs content audit)
7. Network Firewall policy deployment (subnet mappings)
8. Shield Advanced policy deployment
9. Resource tag inclusion/exclusion
10. Policy priority ordering (first-match wins)
11. Compliance monitoring via AWS Config
12. Recent features (third-party rule groups, DNS Firewall, Security Hub)

## When to use

- You need to create an FMS WAF policy across an Organization or OU.
- You are enforcing security group policies centrally.
- You are deploying Network Firewall policies at scale.
- You are enabling Shield Advanced protection organization-wide.
- You need to manage WAF managed rule groups centrally.
- You need to configure resource tag inclusion/exclusion.
- You need to understand policy priority ordering.

## When NOT to use

- **Standalone WAFv2 Web ACL** — use wafv2-web-acl-deployer for single-
  account WAF deployments.
- **Standalone Network Firewall rules** — use network-firewall skills.
- **Shield Advanced without FMS** — use Shield-specific skills.
- **Auditing existing FMS policies** — use firewall-manager-compliance
  auditor skills.

## How to invoke

### Slash command

```
/aws:deploy-firewall-manager
```

Then provide: FMS admin account ID, policy type (WAF/SG/NFW/Shield),
target scope (OU/account/Organization), remediation mode (auto-apply/
monitor-only + grace period), managed rule groups (WAF), baseline SG
(SG common), subnet mappings (NFW), include/exclude tags, policy
priority.

### Natural language

Any of these routes to the same skill:

- "create an FMS WAF policy targeting the Prod OU"
- "enforce security group policies across my Organization"
- "deploy a Network Firewall policy with auto-remediation"
- "enable Shield Advanced protection org-wide"
- "configure FMS resource tag inclusion and exclusion"

### CLI routing

```bash
node cli/bin/cli.js route "create an fms waf policy"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create FMS
policies. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-firewall-manager

     Create an FMS WAF policy targeting OU ou-prod-abcdef in
     us-east-1. Admin account 111111111111. Use
     AWSManagedRulesCommonRuleSet. Auto-remediation with 7-day
     grace. Include Environment=production, exclude
     ComplianceExempt=true. Priority 1.

Skill:
  FMS_POLICY: org-waf-common-rules (type: WAFV2)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] FMS admin: 111111111111 (delegated)
    [✓] Target scope: ORG_UNIT (ou-prod-abcdef)
    [✓] Remediation: auto-apply (grace: 7 days)
    [✓] Managed rule groups: AWSManagedRulesCommonRuleSet
    [✓] Include tags: Environment=production
    [✓] Exclude tags: ComplianceExempt=true
    [✓] Policy priority: 1
  VERIFICATION_COMMANDS:
    aws fms list-policies --region us-east-1
    aws fms get-admin-account --region us-east-1
```

## References

- Skill definition: `skills/firewall-manager-deployer/SKILL.md`
- Policy types and remediation guide: `skills/firewall-manager-deployer/references/policy-types-and-remediation.md`
- Targeting and priority guide: `skills/firewall-manager-deployer/references/targeting-and-priority.md`
- Eval suite: `skills/firewall-manager-deployer/evals/evals.json`
