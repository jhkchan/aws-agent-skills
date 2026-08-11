# End-to-end usage scenario: tag-compliance-automator

A walkthrough showing the skill designing a full tag compliance
automation baseline for an organization: an Organizations TagPolicy
with `enforced_for`, a Config `required-tags` + `allowed-tag-values`
pair, an EventBridge + Lambda auto-tagger with EC2-to-EBS/ENI
propagation, cost allocation tag activation via the API, and a
CloudFormation StackSet for cross-account consistency. Demonstrates the
four-layer pipeline (define, detect, propagate, remediate) and the
AUTOMATION_DEPLOYED verdict.

## Input (user prompt)

> Design a complete tag compliance automation baseline for our
> organization. We need required tags (Environment, Owner, CostCenter,
> Project) enforced on all EC2, S3, RDS, and Lambda resources. We want
> auto-tagging on creation with propagation to child resources, drift
> detection, and cost allocation tags activated.

```
Design reference: org-tag-compliance-rollout
Organization ID: o-xxxxxxx
Root ID: r-xxxx
Account: 111111111111 (payer), 222222222222 (member)
Region: us-east-1

Required tags: Environment, Owner, CostCenter, Project.
Environment allowed_values: dev, staging, prod.
CostCenter allowed_values: cc-100, cc-200, cc-300.
Target resource types: EC2 instances, S3 buckets, RDS instances, Lambda functions.
SSM service role ARN: arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole
Auto-tagger Lambda role ARN: arn:aws:iam::111111111111:role/AutoTaggerRole
Pre-prod validation: completed (auto-tagger with EC2->EBS/ENI propagation tested).
Cost allocation tags: API activation confirmed available.
```

## Skill output

```text
COMPLIANCE: org-tag-compliance-rollout
SCOPE: org root r-xxxx, all member accounts, us-east-1
SCHEMA:
  - Required keys: Environment, Owner, CostCenter, Project
  - Allowed values: Environment=[dev,staging,prod], CostCenter=[cc-100,cc-200,cc-300]
  - Case sensitivity: true
POLICY:
  - Type: Organizations TagPolicy (baseline-compliance-tag-policy) + Config required-tags-core + allowed-tag-values-environment + allowed-tag-values-costcenter
  - Attached to: root r-xxxx
  - enforced_for: AWS::EC2::Instance, AWS::S3::Bucket, AWS::RDS::DBInstance, AWS::Lambda::Function
DETECTION:
  - Config rules: required-tags-core, allowed-tag-values-environment, allowed-tag-values-costcenter
  - Drift detection: enabled via EventBridge on Config CI change for EC2, S3, RDS, Lambda
AUTOMATION:
  - Auto-tagging: EventBridge + Lambda on RunInstances, CreateBucket, CreateFunction20150331
  - Tag propagation: EC2 -> EBS volumes (covered), EC2 -> ENIs (covered)
  - Remediation: SSM Custom-AddRequiredTagEC2, manual trigger (placeholder values require human correction)
PROPAGATION:
  - EC2 -> EBS: covered
  - EC2 -> ENI: covered
COST:
  - Cost allocation tags: active for Environment, Owner, CostCenter, Project
  - Activation method: ce update-cost-allocation-tags-status (API)
CROSS_ACCOUNT:
  - StackSet: tag-compliance-baseline, OUs ou-xxxx-xxxxxxxx, regions us-east-1 us-west-2
VERDICT: AUTOMATION_DEPLOYED
GAP: None — placeholder remediation values (Environment=unknown, Owner=platform-team) require a secondary human-correction queue to set correct tag values.
TEMPLATE:
  # 1. Enable and attach TagPolicy at root
  aws organizations enable-policy-type --root-id r-xxxx --policy-type TAG_POLICY
  aws organizations create-policy --type TAG_POLICY --name baseline-compliance-tag-policy --content file://tag-policy.json
  aws organizations attach-policy --policy-id p-xxxxxxx --target-id r-xxxx

  # 2. Deploy Config rules
  aws configservice put-config-rule --config-rule '{"ConfigRuleName":"required-tags-core","Source":{"Owner":"AWS","SourceIdentifier":"REQUIRED_TAGS"},"Scope":{"ComplianceResourceTypes":["AWS::EC2::Instance","AWS::S3::Bucket","AWS::RDS::DBInstance","AWS::Lambda::Function"]},"InputParameters":"{\"tag1Key\":\"Environment\",\"tag2Key\":\"Owner\",\"tag3Key\":\"Project\",\"tag4Key\":\"CostCenter\"}"}'

  # 3. Deploy auto-tagger with EC2->EBS/ENI propagation
  aws events put-rule --name auto-tag-on-create --event-pattern '{"source":["aws.ec2","aws.s3","aws.lambda"],"detail-type":["AWS API Call via CloudTrail"],"detail":{"eventSource":["ec2.amazonaws.com","s3.amazonaws.com","lambda.amazonaws.com"],"eventName":["RunInstances","CreateBucket","CreateFunction20150331"]}}'
  aws lambda create-function --function-name auto-tagger --runtime python3.12 --handler auto_tag.lambda_handler --role arn:aws:iam::111111111111:role/AutoTaggerRole --zip-file fileb://auto_tag.zip
  aws events put-targets --rule auto-tag-on-create --targets '[{"Id":"auto-tagger","Arn":"arn:aws:lambda:us-east-1:111111111111:function:auto-tagger","DeadLetterConfig":{"Arn":"arn:aws:sqs:us-east-1:111111111111:auto-tagger-dlq"}}]'

  # 4. Deploy remediation SSM document + Config remediation config
  aws ssm create-document --name Custom-AddRequiredTagEC2 --document-type Automation --document-format YAML --content file://add-tag-ec2.yaml
  aws configservice put-remediation-configurations --remediation-configurations '[{"ConfigRuleName":"required-tags-core","TargetType":"SSM_DOCUMENT","TargetId":"Custom-AddRequiredTagEC2","Automatic":false,"MaximumAutomaticAttempts":3,"RetryAttemptSeconds":600,"Parameters":{"ResourceId":{"ResourceValue":{"Value":"RESOURCE_ID"}},"TagKey":{"StaticValue":{"Values":["Environment"]}},"TagValue":{"StaticValue":{"Values":["unknown"]}},"AutomationAssumeRole":{"StaticValue":{"Values":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}}}}]'

  # 5. Activate cost allocation tags
  aws ce update-cost-allocation-tags-status --cost-allocation-tags-status '[{"TagKey":"Environment","Status":"Active"},{"TagKey":"Owner","Status":"Active"},{"TagKey":"CostCenter","Status":"Active"},{"TagKey":"Project","Status":"Active"}]'

  # 6. Deploy StackSet for cross-account Config rules
  aws cloudformation create-stack-set --stack-set-name tag-compliance-baseline --template-body file://tag-compliance-stackset.yaml --permission-model SERVICE_MANAGED --auto-deployment Enabled=true,RetainStacksOnAccountRemoval=false --capabilities CAPABILITY_IAM
  aws cloudformation create-stack-instances --stack-set-name tag-compliance-baseline --deployment-targets OrganizationalUnitIds=["ou-xxxx-xxxxxxxx"] --regions us-east-1 us-west-2
```

**Account-level aggregate verdict: AUTOMATION_DEPLOYED.** The full
four-layer stack (define via TagPolicy, detect via Config, propagate via
EventBridge + Lambda, remediate via SSM Automation) is wired. Cost
allocation tags are active. The StackSet deploys Config rules to all
member accounts.

## What the skill caught that a generic assistant misses

1. **The `enforced_for` gotcha.** A generic assistant writes the
   TagPolicy JSON with `allowed_values` but omits `enforced_for`. The
   policy is advisory — AWS does not block non-compliant operations.
   The skill always lists resource types under `enforced_for`.

2. **The EC2-to-child propagation gap.** A generic assistant tags only
   the EC2 instance. The skill flags that EBS volumes and ENIs created
   in the same `RunInstances` call are untagged and adds the propagation
   handler to the Lambda.

3. **The case-sensitivity matrix.** A generic assistant assumes that
   `case_sensitive: false` in the TagPolicy makes Config
   case-insensitive. The skill notes that Config always checks the exact
   key name in InputParameters and normalizes casing in the auto-tagger.

4. **The 5-key limit on `required-tags`.** A generic assistant puts 6+
   tag keys in a single Config rule. The skill notes the managed rule
   silently ignores keys beyond the 5th and deploys a second rule.

5. **The cost allocation propagation delay.** A generic assistant
   activates tags and expects immediate Cost Explorer updates. The skill
   notes the 24-hour propagation delay and surfaces the
   `ProcessingStatus` field for polling.

6. **The Billing-console IAM gate.** A generic assistant assumes the
   API always works. The skill checks whether the payer account has
   enabled "IAM User and Role Access to Billing Information" and flags
   `REVIEW_REQUIRED` if not.

## Slash-command invocation

```
/aws:automate-tag-compliance
```

Or via the orchestrator:

```
/aws:pipeline
You: "design tag compliance baseline for the org"
```

## CLI routing

```bash
node cli/bin/cli.js route "design Organizations TagPolicy with enforcement"
# [Phase: Automate | Skills routed: tag-compliance-automator]
```

## Live-account invocation (requires AWS CLI)

```bash
# Check if tag policies are enabled
aws organizations describe-organization \
  --query 'Organization.AvailablePolicyTypes[?Type==`TAG_POLICY`].Status' \
  --output text --profile default

# List existing tag policies
aws organizations list-policies --filter TAG_POLICY --profile default

# Check Config required-tags rule status
aws configservice describe-config-rules \
  --config-rule-names required-tags-core \
  --region us-east-1 --profile default

# Check cost allocation tag status
aws ce list-cost-allocation-tags --status Active \
  --region us-east-1 --profile default

# Sample resource tag coverage
aws resourcegroupstaggingapi get-resources \
  --tag-filters Key=Environment,Values=[] \
  --resources-per-page 10 \
  --region us-east-1 --profile default
```

Then paste the output into the skill for compliance design.
