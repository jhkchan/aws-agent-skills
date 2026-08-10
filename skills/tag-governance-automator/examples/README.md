# End-to-end usage scenario: tag-governance-automator

A walkthrough showing the skill designing a full tag governance
baseline for an organization: an Organizations TagPolicy, an
EventBridge + Lambda auto-tagger, a Config required-tags rule with
SSM Automation remediation, and cost allocation tag activation.
Demonstrates the full three-layer stack (define → enforce → remediate).

## Input (user prompt)

> Design a complete tag governance baseline for our organization.
> We need required tags (Environment, Owner, Project, CostCenter)
> enforced on all EC2 and S3 resources, auto-tagging on creation,
> remediation for existing untagged resources, and cost allocation
> tag activation.

```
Design reference: org-tag-governance-rollout
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111 (payer), 222222222222 (member)
Region: us-east-1

Required tags: Environment, Owner, Project, CostCenter.
Environment allowed_values: dev, staging, prod.
Target resource types: EC2 instances, S3 buckets, Lambda functions.
SSM service role ARN: arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Pre-prod validation: completed for Config rule and auto-tagger.
Cost allocation tags: NOT yet activated.
```

## Skill output

```text
GOVERNANCE: org-tag-governance-rollout
SCOPE: org root r-xxxx, all member accounts, us-east-1
STRATEGY:
  - Required tags: Environment, Owner, Project, CostCenter
  - Optional tags: Application, ComplianceTier
  - Enforcement layer: Organizations TagPolicy + Config required-tags rule
POLICY:
  - Type: Organizations TagPolicy (baseline-tag-policy) + Config required-tags-core
  - Attached to: root (TagPolicy), Config recorder (rule)
  - Template: see below
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances, CreateBucket, CreateFunction20150331
  - Remediation: SSM Automation Custom-AddRequiredTagsEC2 (manual trigger, placeholder values)
  - Trigger: manual (placeholder remediation requires human correction)
COMPLIANCE:
  - Detection: required-tags-core (Environment, Owner, Project, CostCenter, Application)
  - Reporting: Security Hub FSBP controls + Config compliance dashboard
  - Cost allocation: active (via ce update-cost-allocation-tags-status on payer)
VERDICT: AUTOMATED
GAP: None — placeholder remediation values (Environment=unknown, Owner=platform-team) require a secondary human-correction queue to set correct tag values. Auto-tagger covers new resources; backlog requires manual start-remediation-execution.
BLAST_RADIUS: org-root
VALIDATION_PHASE: root-enforce
TEMPLATE:
  # 1. Enable tag policies at root
  aws organizations enable-policy-type --root-id r-xxxx --policy-type TAG_POLICY

  # 2. Create TagPolicy (see Step 2 of SKILL.md for full JSON)
  aws organizations create-policy --type TAG_POLICY --name baseline-tag-policy --content file://tag-policy.json
  aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx

  # 3. Deploy Config required-tags rule
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"required-tags-core","Source":{"Owner":"AWS","SourceIdentifier":"REQUIRED_TAGS"},"Scope":{"ComplianceResourceTypes":["AWS::EC2::Instance","AWS::S3::Bucket","AWS::Lambda::Function"]},"InputParameters":"{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\",\"tag5Key\":\"Application\"}"}'

  # 4. Deploy auto-tagger (EventBridge + Lambda)
  aws events put-rule --name auto-tag-on-create --event-pattern '{"source":["aws.ec2","aws.s3","aws.lambda"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"eventSource":["ec2.amazonaws.com","s3.amazonaws.com","lambda.amazonaws.com"],"eventName":["RunInstances","CreateBucket","CreateFunction20150331"]}}'
  aws lambda create-function --function-name auto-tagger --runtime python3.12 --handler auto_tag.lambda_handler --role arn:aws:iam::111111111111:role/AutoTaggerRole --zip-file fileb://auto_tag.zip
  aws events put-targets --rule auto-tag-on-create --targets '[{"Id":"auto-tagger","Arn":"arn:aws:lambda:us-east-1:111111111111:function:auto-tagger","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:auto-tagger-dlq"}}]'

  # 5. Deploy remediation SSM document + Config remediation config
  aws ssm create-document --name Custom-AddRequiredTagsEC2 --document-type Automation --document-format YAML --content file://add-required-tags-ec2.yaml
  aws configservice put-remediation-configurations --remediation-configurations '[{"ConfigRuleName":"required-tags-core","TargetType":"SSM_DOCUMENT","TargetId":"Custom-AddRequiredTagsEC2","Automatic":false,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600,"Parameters":{"InstanceId":{"ResourceValue":{"Value":"RESOURCE_ID"}},"AutomationAssumeRole":{"StaticValue":{"Values":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}}}]'

  # 6. Activate cost allocation tags
  aws ce update-cost-allocation-tags-status --cost-allocation-tags-status '[{"TagKey":"Environment","Status":"Active"},{"TagKey":"Owner","Status":"Active"},{"TagKey":"Project","Status":"Active"},{"TagKey":"CostCenter","Status":"Active"}]'
```

**Account-level aggregate verdict: AUTOMATED.** The full three-layer
stack (define via TagPolicy → enforce via Config + auto-tagger →
remediate via SSM Automation) is wired. Cost allocation tags are
active for Cost Explorer reporting.

## What the skill caught that a generic assistant misses

1. **The `enforced_for` gotcha.** A generic assistant writes the
   TagPolicy JSON with `allowed_values` but omits `enforced_for`.
   The policy is advisory — AWS does not block non-compliant tag
   operations. The skill always lists the resource types explicitly.

2. **The cost allocation activation step.** A generic assistant tags
   resources and assumes Cost Explorer shows the dimensions. The
   skill flags that tag keys must be explicitly activated via
   `ce update-cost-allocation-tags-status` (or the Billing console)
   before they appear as cost dimensions.

3. **The 5-key limit on required-tags.** A generic assistant puts 6+
   tag keys in a single Config rule. The skill notes the managed
   rule silently ignores keys beyond the 5th and deploys a second
   rule (`required-tags-ext`) if needed.

4. **The placeholder-value caveat.** A generic assistant sets
   `Automatic: true` on the SSM remediation and walks away. The
   skill flags that placeholder values (`Environment=unknown`)
   satisfy Config but pollute ABAC and cost reporting — a
   secondary human-correction queue is required.

5. **The auto-tagging + tag policy pairing.** A generic assistant
   deploys auto-tagging alone. The skill notes that auto-tagging
   without a tag policy allows humans to modify tags afterward —
   the two layers must be deployed together.

6. **The ABAC case-sensitivity gap.** A generic assistant writes
   `StringEquals` for the ABAC condition. The skill notes that if
   the tag policy has `case_sensitive: false`, the IAM condition
   must use `StringEqualsIgnoreCase` to avoid silent gaps.

## Slash-command invocation

```
/aws:automate-tag-governance
```

Or via the orchestrator:

```
/aws:pipeline
You: "design tag governance baseline for the org"
```

## CLI routing

```bash
node cli/bin/cli.js route "design Organizations TagPolicy"
# [Phase: Automate | Skills routed: tag-governance-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Check if tag policies are enabled
aws organizations describe-organization \
  --query 'Organization.AvailablePolicyTypes[?Type==`TAG_POLICY`].Status' \
  --output text --profile default

# List existing tag policies
aws organizations list-policies --filter TAG_POLICY \
  --profile default

# Check Config required-tags rule status
aws configservice describe-config-rules \
  --config-rule-names required-tags-core \
  --region us-east-1 --profile default

# Check cost allocation tag status
aws ce list-cost-allocation-tags --status Active \
  --region us-east-1 --profile default

# Sample resource tag coverage
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=["prod"] \
  --resources-per-page 10 \
  --region us-east-1 --profile default
```

Then paste the output into the skill for governance design.
