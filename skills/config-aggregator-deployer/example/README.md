# End-to-End Example: AWS Config Aggregator Provisioning

A walkthrough showing how to use the `config-aggregator-deployer` skill
from invocation through verification. Mirrors the structured-eval pattern
of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an AWS Config aggregator for an enterprise with
an AWS Organization. The aggregator requires:

- Organization aggregator with delegated administrator
- Aggregator account: 123456789012
- Organization ID: o-abc123def
- Source: all accounts, all regions
- Conformance pack: OperationalBestPractices-for-Security (org-level)
- Organization config rule with Lambda processor
- Tags: Environment=production, Governance=compliance

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-config-aggregator
```

Then paste the aggregator requirements.

### Option B: Natural language

```
You: "Provision an AWS Config aggregator in us-east-1. Organization
      aggregator. Org ID o-abc123def. Delegated admin 123456789012.
      All accounts, all regions. Deploy conformance pack
      OperationalBestPractices-for-Security at org level. Add a Lambda
      processor org config rule for tag policy compliance."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "deploy config aggregator"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
AGGREGATOR: org-compliance-aggregator
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓]      Aggregator type — OrganizationAggregationSource (OrganizationID: o-abc123def)
  [✓]      Delegated administrator — 123456789012 (Config enabled, all features)
  [✓]      Aggregator region — us-east-1
  [✓]      Source accounts — all accounts in Organization o-abc123def (auto-discovered)
  [✓]      Source regions — all enabled regions
  [✓]      Recorder — config recorder running on delegated admin (recording all resourceTypes)
  [✓]      Delivery channel — S3 bucket config-bucket-123456789012 (Config enabled)
  [✓]      Conformance packs — OperationalBestPractices-for-Security (deployed org-wide)
  [✓]      Organization config rules — tag-policy-compliance (Lambda processor, ACTIVE)
  [✓]      IAM permissions — ConfigRole with AWS_ConfigRole managed policy
  [✓]      Tags — Environment=production, Governance=compliance
  [OPTIONAL] Aggregation authorization — not needed (organization aggregator auto-authorizes)
VERIFICATION_COMMANDS:
  aws configservice describe-configuration-aggregators --configuration-aggregator-names org-compliance-aggregator --region us-east-1
  aws configservice describe-configuration-aggregator-sources-status --configuration-aggregator-name org-compliance-aggregator --region us-east-1
  aws configservice describe-organization-conformance-packs --region us-east-1
  aws configservice describe-config-rules --region us-east-1
```

---

## Step 3 — Provisioning commands

The skill generates the CLI sequence (from
`references/deployment-cli-commands.md`):

```bash
# Step 1: Enable Config as trusted service + register delegated admin
aws organizations enable-aws-service-access --service-principal config.amazonaws.com
aws organizations register-delegated-administrator \
  --account-id 123456789012 --service-principal config.amazonaws.com

# Step 2: Create the organization aggregator
cat > /tmp/aggregator.json <<'EOF'
{
  "ConfigurationAggregatorName": "org-compliance-aggregator",
  "OrganizationAggregationSource": {
    "RoleArn": "arn:aws:iam::123456789012:role/ConfigAggregatorRole",
    "AllAwsRegions": true
  },
  "Tags": [
    { "Key": "Environment", "Value": "production" },
    { "Key": "Governance", "Value": "compliance" }
  ]
}
EOF
aws configservice put-configuration-aggregator --cli-input-json file:///tmp/aggregator.json --region us-east-1

# Step 3: Deploy org-level conformance pack
aws configservice put-organization-conformance-pack \
  --organization-conformance-pack-name OperationalBestPractices-for-Security \
  --template-s3-uri s3://config-templates-123456789012/security-best-practices.yaml \
  --region us-east-1

# Step 4: Deploy Lambda processor org config rule
aws configservice put-organization-config-rule \
  --organization-config-rule-name tag-policy-compliance \
  --organization-custom-rule \
    LambdaFunctionArn=arn:aws:lambda:us-east-1:123456789012:function:config-tag-policy-rule,\
    OrganizationRuleStatus=ENABLED,\
    MaximumExecutionFrequency=One_Hour \
  --region us-east-1
```

---

## Step 4 — Post-provisioning verification

```bash
# Verify aggregator configuration
aws configservice describe-configuration-aggregators \
  --configuration-aggregator-names org-compliance-aggregator --region us-east-1

# Check source account aggregation status
aws configservice describe-configuration-aggregator-sources-status \
  --configuration-aggregator-name org-compliance-aggregator --region us-east-1

# List organization conformance packs
aws configservice describe-organization-conformance-packs --region us-east-1

# Check org config rule deployment status
aws configservice describe-organization-config-rule-statuses --region us-east-1

# Aggregate compliance summary across all accounts/regions
aws configservice get-aggregate-compliance-details-by-config-rule \
  --configuration-aggregator-name org-compliance-aggregator \
  --config-rule-name tag-policy-compliance \
  --account-id 111111111111 \
  --aws-region us-east-1 \
  --region us-east-1
```

---

## What the skill catches that a naive deployment misses

| Configuration | Naive deployment | Skill output | Why the skill is right |
|---|---|---|---|
| Delegated admin | Skips `enable-aws-service-access` | Enables Config trusted service first | Org aggregator silently shows no source accounts without it |
| Recorder status | Assumes recorders run everywhere | Verifies recorder per source account | Aggregator returns empty data for accounts with stopped recorders |
| Aggregation auth | Skips `PutAggregationAuthorization` | Required for authorized-account type | Source status shows FAILED without per-account authorization |
| Conformance pack scope | Deploys per-account | Deploys at org level for consistency | Individual packs override org packs, creating inconsistency |
| Lambda invoke permission | Forgets resource policy | Grants `lambda:InvokeFunction` to `config.amazonaws.com` | Lambda processor rules silently fail without it |
| Proactive rules | Only reactive | Enables `Proactive: true` for shift-left | Pre-deployment evaluation blocks non-compliant resources in CI/CD |
| Aggregator vs recorder | Confuses roles | Distinguishes recorder (records) vs aggregator (collects) | Aggregator depends on recorders — not interchangeable |

---

## Related artifacts

- **Skill definition:** `skills/config-aggregator-deployer/SKILL.md`
- **Deployment CLI commands:** `skills/config-aggregator-deployer/references/deployment-cli-commands.md`
- **Conformance packs, proactive rules guide:** `skills/config-aggregator-deployer/references/conformance-packs-and-proactive-rules.md`
- **Slash command:** `commands/aws/deploy-config-aggregator.md`
- **Eval suite:** `skills/config-aggregator-deployer/evals/evals.json`
- **Legacy test cases:** `skills/config-aggregator-deployer/eval/test-cases.yaml`
