# Diagnostic Commands — IaC Template Automator

Validation toolchain pipelines and drift-detection command listings moved verbatim from SKILL.md. Loaded on demand.

## Validation toolchain

### CloudFormation validation pipeline

```bash
# 1. Spec compliance — property names, types, required fields
cfn-lint template.yaml

# 2. Security posture — wildcard IAM, missing encryption, plaintext secrets
cfn-nag template.yaml

# 3. CloudFormation server-side validation (catches macros and transforms)
aws cloudformation validate-template \
  --template-body file://template.yaml

# 4. Change-set preview against an existing stack
aws cloudformation create-change-set \
  --stack-name <stack> --change-set-name preview-$(date +%s) \
  --template-body file://template.yaml \
  --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND

aws cloudformation describe-change-set \
  --stack-name <stack> --change-set-name preview-XXXXX \
  --query 'Changes[*].ResourceChange.[Action,LogicalResourceId,Replacement]'
```

### CDK validation pipeline

```bash
# 1. Synthesize to CloudFormation
cdk synth --all

# 2. Type-check the source (TypeScript)
npm run build  # tsc --noEmit

# 3. Unit tests with CDK assertions
npm test  # jest — uses @aws-cdk/assertions

# 4. Lint the synthesized template
cfn-lint cdk.out/*.template.json
cfn-nag cdk.out/*.template.json
```

**CDK assertions example:**

```typescript
import { Template } from 'aws-cdk-lib/assertions';

test('bucket is encrypted', () => {
  const template = Template.fromStack(stack);
  template.hasResourceProperties('AWS::S3::Bucket', {
    BucketEncryption: {
      ServerSideEncryptionConfiguration: [{
        ServerSideEncryptionByDefault: { SSEAlgorithm: 'aws:kms' },
      }],
    },
  });
});
```

### Terraform validation pipeline

```bash
# 1. Format check (does not modify)
terraform fmt -check -recursive -diff

# 2. Syntax and provider validation
terraform init -backend=false
terraform validate

# 3. Lint with tflint (provider-aware — catches deprecated resources)
tflint --init
tflint

# 4. Security with checkov
checkov -d . --framework terraform

# 5. Plan (REQUIRED before apply — shows diff against real state)
terraform plan -out=tfplan

# Inspect the plan JSON for destructive actions
terraform show -json tfplan | jq '.resource_changes[] | select(.change.actions[] | test("delete|replace|create-delete"))'
```

### checkov baseline suppression

When a checkov finding is a false positive or accepted risk, suppress it
explicitly — never disable the rule globally.

```hcl
# Terraform inline suppression
resource "aws_s3_bucket" "logs" {
  bucket = "app-logs"
  #checkov:skip=CKV_AWS_18:Logs bucket does not need access logging (chicken-and-egg)
}
```

## Drift detection & state management

### CloudFormation drift detection

```bash
# Schedule drift detection (runs async)
DRIFT_ID=$(aws cloudformation detect-stack-drift --stack-name prod-app --query 'StackDriftDetectionId --output text)

# Poll status (returns DETECTION_IN_PROGRESS | DETECTION_COMPLETE | DETECTION_FAILED)
aws cloudformation describe-stack-drift-detection-status \
  --stack-name prod-app --stack-drift-detection-id $DRIFT_ID

# Get the drift report
aws cloudformation describe-stack-resource-drifts --stack-name prod-app \
  --stack-resource-drift-status-filters MODIFIED DELETED NOT_CHECKED
```

**Caveat:** drift detection does NOT cover every property. Service-side
auto-updates (Lambda runtime patches, RDS engine minor version bumps) do
not register as drift. Run drift detection weekly on prod stacks as a
baseline; pair with `configservice get-resource-config-history` for
property-level drift on critical resources.

### Terraform drift detection

```bash
# Plan shows drift as a diff
terraform plan -detailed-exitcode
# Exit codes:
#   0 = no diff (no drift)
#   1 = error
#   2 = diff present (DRIFT DETECTED)
```

**Caveat:** `terraform plan` compares state file to AWS API. If the state
file itself is stale (someone ran `terraform apply` on a different machine
without pushing state), `plan` shows a false drift. Always verify state
recency via `terraform state pull` timestamp before interpreting plan output.

### Common drift causes

- Console clicks (operator edits a resource in the AWS console).
- Out-of-band CLI commands (`aws s3api put-bucket-policy` outside IaC).
- Service-side auto-remediation (Config rule or SSM Automation kicks in).
- Lambda runtime auto-update (deprecation handling).
- AWS Support troubleshooting (rare but real).
