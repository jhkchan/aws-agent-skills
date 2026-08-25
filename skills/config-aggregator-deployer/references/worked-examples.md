# Worked Examples (load on demand) — Config Aggregator Deployer

Deployment Steps 2-9 CLI walkthroughs (delegated admin, aggregator creation, account authorization, recorder verification, org conformance packs, Lambda processor rules, proactive rules, verification), moved verbatim from SKILL.md. Step 1 type selection stays in SKILL.md.


---

## Step 2: Delegated administrator setup (organization only) (moved from SKILL.md)

The management account designates the aggregator account as the
delegated administrator for AWS Config:

```bash
# Enable AWS Config as a trusted service in Organizations
aws organizations enable-aws-service-access \
  --service-principal config.amazonaws.com

# Designate the aggregator account as delegated admin
aws organizations register-delegated-administrator \
  --account-id 123456789012 \
  --service-principal config.amazonaws.com
```

The delegated admin account can now create organization
aggregators, deploy org conformance packs, and deploy org config
rules without needing per-account credentials.

## Step 3: Create the aggregator (moved from SKILL.md)

**Organization aggregator:**
```bash
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

aws configservice put-configuration-aggregator \
  --cli-input-json file:///tmp/aggregator.json \
  --region us-east-1
```

The `RoleArn` is a service-role in the management account that
Config assumes to read organization details. It needs
`organizations:ListAccounts` and `sts:AssumeRole` permissions.

**Authorized-account aggregator:**
```bash
cat > /tmp/aggregator-auth.json <<'EOF'
{
  "ConfigurationAggregatorName": "authorized-accounts-aggregator",
  "AccountAggregationSources": [
    {
      "AccountIds": ["111111111111", "222222222222", "333333333333"],
      "AllAwsRegions": true
    }
  ],
  "Tags": [
    { "Key": "Environment", "Value": "production" }
  ]
}
EOF

aws configservice put-configuration-aggregator \
  --cli-input-json file:///tmp/aggregator-auth.json \
  --region us-east-1
```

## Step 4: Authorize source accounts (authorized-account only) (moved from SKILL.md)

For each source account, the source account must grant the
aggregator account permission to collect data:

```bash
# Run on each SOURCE account
aws configservice put-aggregation-authorization \
  --authorized-account-id 123456789012 \
  --authorized-aws-region us-east-1
```

This creates an `AggregationAuthorization` record that lets the
aggregator account (123456789012) pull Config data from this
source account. Organization aggregators do NOT need this — the
delegated admin role auto-authorizes.

## Step 5: Verify recorders in source accounts (moved from SKILL.md)

The aggregator collects data from the Config recorder in each
source account. If the recorder is not running, the aggregator
will show empty results for that account.

```bash
# On each source account — verify recorder is running
aws configservice describe-configuration-recorder-status
```

If the recorder is not running, enable Config on the source
account:

```bash
# Create the Config role
aws iam create-role \
  --role-name AWS-ConfigRole \
  --assume-role-policy-document file:///tmp/config-trust-policy.json

aws iam attach-role-policy \
  --role-name AWS-ConfigRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWS_ConfigRole

# Create delivery channel (S3 bucket)
aws configservice put-delivery-channel \
  --delivery-channel file:///tmp/delivery-channel.json

# Start the recorder
aws configservice start-configuration-recorder \
  --configuration-recorder-name default
```

## Step 6: Conformance packs at organization level (moved from SKILL.md)

Organization conformance packs deploy a set of Config rules and
remediation actions to every account in the Organization. Deploy
from the delegated admin account:

```bash
# Deploy an org-level conformance pack from a sample template
aws configservice put-organization-conformance-pack \
  --organization-conformance-pack-name OperationalBestPractices-for-Security \
  --template-s3-uri s3://config-templates-123456789012/security-best-practices.yaml \
  --region us-east-1
```

AWS provides sample conformance pack templates for common
compliance frameworks:
- `OperationalBestPractices-for-CloudWatch`
- `OperationalBestPractices-for-Security`
- `OperationalBestPractices-for-EC2`
- `OperationalBestPractices-for-S3`
- `OperationalBestPractices-for-IAM`
- `FedRAMP-moderate`, `HIPAA-Security`, `PCI-DSS`, `CIS-AWS`

Organization conformance packs auto-deploy to all current and
future accounts. Individual account conformance packs can override
org-level packs if they share a name.

## Step 7: Organization config rules with Lambda processor (moved from SKILL.md)

Create a custom Config rule backed by a Lambda function and deploy
it across the organization:

```bash
# Deploy the Lambda function for the rule processor
aws lambda create-function \
  --function-name config-tag-policy-rule \
  --runtime python3.12 \
  --role arn:aws:iam::123456789012:role/ConfigLambdaRole \
  --handler index.handler \
  --zip-file fileb://config-rule.zip \
  --region us-east-1

# Create the organization config rule pointing to the Lambda
aws configservice put-organization-config-rule \
  --organization-config-rule-name tag-policy-compliance \
  --organization-managed-rule \
    ManagedRuleIdentifier=AWS_CONFIG_MANAGED_RULE_TAG_POLICY_CHECK,\
    OrganizationRuleStatus=ENABLED \
  --region us-east-1
```

The Lambda receives `ConfigurationItemChanged` events, evaluates
the resource, and returns `COMPLIANT` or `NON_COMPLIANT` via
`put_evaluations`.

## Step 8: Proactive rules (pre-deployment evaluation) (moved from SKILL.md)

Proactive Config rules evaluate resources BEFORE they are created.
A rule must have its `Proactive` mode enabled, then CloudFormation,
CDK, and Terraform can call `StartResourceEvaluation` to check
resources during deployment.

```bash
# Create or update a Config rule with proactive evaluation enabled
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-versioning-proactive",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_VERSIONING_ENABLED"
    },
    "Proactive": true
  }' \
  --region us-east-1

# Pre-deployment check — evaluate a hypothetical S3 bucket config
EVAL_TOKEN=$(aws configservice start-resource-evaluation \
  --resource-type "AWS::S3::Bucket" \
  --resource-id "my-new-bucket" \
  --evaluation-mode PROACTIVE \
  --configuration '{"BucketName":"my-new-bucket","VersioningConfiguration":{"Status":"Suspended"}}' \
  --query 'EvaluationToken' --output text \
  --region us-east-1)

# Retrieve the evaluation result
aws configservice get-resource-evaluation-status \
  --evaluation-token ${EVAL_TOKEN} \
  --region us-east-1
```

The result tells you whether the resource would be compliant or
non-compliant BEFORE provisioning — enabling shift-left
compliance in CI/CD pipelines.

## Step 9: Verification and post-deployment checks (moved from SKILL.md)

```bash
# Verify the aggregator exists and is configured
aws configservice describe-configuration-aggregators \
  --configuration-aggregator-names org-compliance-aggregator \
  --region us-east-1

# Check aggregation source status (are source accounts sending data?)
aws configservice describe-configuration-aggregator-sources-status \
  --configuration-aggregator-name org-compliance-aggregator \
  --region us-east-1

# List conformance packs deployed org-wide
aws configservice describe-organization-conformance-packs \
  --region us-east-1

# Check org config rule deployment status
aws configservice describe-organization-config-rule-statuses \
  --region us-east-1

# Aggregate compliance summary across all accounts/regions
aws configservice get-aggregate-compliance-details-by-config-rule \
  --configuration-aggregator-name org-compliance-aggregator \
  --config-rule-name s3-bucket-versioning-enabled \
  --account-id 111111111111 \
  --aws-region us-east-1 \
  --region us-east-1
```
