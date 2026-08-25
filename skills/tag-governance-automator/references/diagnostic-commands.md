# Diagnostic Commands — Tag Governance Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Step 10: Audit and verify a deployed governance baseline

End-to-end verification of the tag governance stack:

```bash
# 1. Tag policy is attached and enforced
aws organizations list-policies --filter TAG_POLICY \
  --query 'Policies[].{Name:Name,Id:Id,State:AwsManaged}'
aws organizations describe-policy --policy-id p-xxxxxxx

# 2. Config required-tags rule is evaluating
aws configservice describe-config-rules \
  --config-rule-names required-tags-core
aws configservice get-compliance-summary-by-config-rule

# 3. Auto-tagger Lambda is firing
aws logs filter-log-events \
  --log-group-name /aws/lambda/auto-tagger \
  --filter-pattern '"tagged": true' \
  --start-time $(date -d '1 hour ago' +%s)000

# 4. Security Hub has the tag findings
aws securityhub get-findings \
  --filters '{"GeneratorId":[{"Value":"required-tags","Comparison":"CONTAINS"}]}' \
  --query 'Findings[].{Id:Id,Severity:Severity.Label,Title:Title}'

# 5. Cost allocation tags are active
aws ce list-cost-allocation-tags --status Active

# 6. Resource tag coverage (sample)
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=["prod"] \
  --resources-per-page 50
```

A governance baseline that passes Steps 1-3 but has zero active cost
allocation tags (Step 5) is incomplete — cost reporting will show no
tag dimensions.

## Pre-flight safety checks (run before applying any tag governance CLI)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`create-policy`, `attach-policy`, `put-config-rule`,
  `put-remediation-configurations`, `tag-resources` bulk), emit:
  `CONFIRM: About to <action> for scope <scope>. This affects
  <consequence>. Proceed? (yes/no)`

- **Back up the existing tag policy** before modifying:
  `aws organizations describe-policy --policy-id p-xxxxxxx > /tmp/tag-policy-backup-$(date +%s).json`
  Tag policies have no version history.

- **Test the tag policy in a sandbox OU first.** Attach to a
  non-production OU, create a test resource with a non-compliant tag,
  verify the `CreateTags` call is blocked, then promote to root.

- **Before activating cost allocation tags**, verify the payer account
  supports `ce update-cost-allocation-tags-status`. Legacy accounts or
  accounts with restricted IAM may require the Billing console path.

- **Before deploying ABAC**, inventory principal tags:
  `aws iam list-user-tags --user-name <name>`. An ABAC policy on
  untagged principals is a guaranteed access outage.
