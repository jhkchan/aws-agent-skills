# End-to-End Example: SSM Association Operation

A walkthrough showing how to use the `ssm-association-operator` skill
from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are creating a State Manager association that applies the AWS-
managed patch baseline to the production fleet, runs every 30
minutes, uses integer rate control, and routes execution output to
a KMS-encrypted S3 bucket. The association needs:

- Name: PatchProductionFleet
- Document: AWS-ApplyPatchBaseline
- Targets: instances tagged Environment=production (dynamic)
- Schedule: rate(30 minutes)
- Apply-at-creation: enabled (immediate first run)
- Rate control: max-concurrency=10, max-errors=3 (integer form)
- Output S3: s3://my-ssm-output/ssm-output/ (SSE-KMS, customer-managed key)
- Parameters: Operation=Install, SnapshotId=latest
- Tags: Environment=production, Owner=cloudops

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:operate-ssm-association
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create an SSM association named PatchProductionFleet that
      patches instances tagged Environment=production every 30
      minutes. Allow 10 in parallel, stop after 3 errors. Send
      output to my-ssm-output with KMS encryption."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create ssm association"
```

---

## Step 2 — Skill produces the OPERATION_COMPLETED checklist

```text
SSM_ASSOCIATION: PatchProductionFleet (a-1a2b3c4d5e6f7g8h9)
VERDICT: OPERATION_COMPLETED
CHECKLIST:
  [✓] Document: AWS-ApplyPatchBaseline (default version)
  [✓] Targets: tag:Environment=production (dynamic)
  [✓] Schedule: rate(30 minutes)
  [✓] Apply-at-creation: ENABLED
  [✓] Rate control: max-concurrency=10, max-errors=3 (integer form)
  [✓] Output S3: s3://my-ssm-output/ssm-output/ (SSE-KMS, key arn:aws:kms:us-east-1:123456789012:key/abc123)
  [✓] Parameters: Operation=Install, SnapshotId=latest
  [✓] Compliance: COMPLIANT
  [✓] Status: Success
  [✓] Association version: 3
  [✓] CloudWatch alarm: ssm-patch-failures-prod
  [✓] Tags: Environment=production, Owner=cloudops
VERIFICATION_COMMANDS:
  aws ssm describe-association --association-id a-1a2b3c4d5e6f7g8h9 --region us-east-1
  aws ssm describe-association-executions --association-id a-1a2b3c4d5e6f7g8h9 --region us-east-1
  aws ssm list-compliance-items --filters Key=ComplianceType,Values=Association --region us-east-1
  aws s3api get-bucket-encryption --bucket my-ssm-output --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 0: verify prerequisites
aws ssm describe-document --name AWS-ApplyPatchBaseline --region us-east-1

aws ssm describe-instance-information \
  --filters "Key=tag:Environment,Values=production" \
  --query 'InstanceInformationList[*].InstanceId' \
  --region us-east-1 --output table

aws s3api get-bucket-encryption --bucket my-ssm-output --region us-east-1

# Step 1: create the association with integer rate control and apply-at-creation
ASSOC_ID=$(aws ssm create-association \
  --name "AWS-ApplyPatchBaseline" \
  --targets "Key=tag:Environment,Values=production" \
  --schedule-expression "rate(30 minutes)" \
  --max-concurrency 10 \
  --max-errors 3 \
  --parameters "Operation=Install,SnapshotId=latest" \
  --output-location '{"S3Location":{"OutputS3BucketName":"my-ssm-output","OutputS3KeyPrefix":"ssm-output/","OutputS3Region":"us-east-1"}}' \
  --apply-at-creation \
  --tags "Key=Environment,Value=production" "Key=Owner,Value=cloudops" \
  --query 'AssociationDescription.AssociationId' \
  --region us-east-1 --output text)

echo "Association ID: $ASSOC_ID"

# Step 2: wait for the first execution (apply-at-creation triggers it)
sleep 30

# Step 3: verify the association ran
aws ssm describe-association-executions \
  --association-id "$ASSOC_ID" \
  --query 'AssociationExecutions[0].{Status:Status,ExecutedOn:ExecutedTime}' \
  --region us-east-1
```

---

## Step 4 — Post-deployment verification

```bash
# Association status — should be Success
aws ssm describe-association \
  --association-id "$ASSOC_ID" \
  --query 'AssociationDescription.Overview.{Status:Status,DetailedStatus:DetailedStatus}' \
  --region us-east-1

# Per-instance execution detail
aws ssm describe-association-execution-targets \
  --association-id "$ASSOC_ID" \
  --execution-id "$(aws ssm describe-association-executions --association-id $ASSOC_ID --query 'AssociationExecutions[0].ExecutionId' --output text --region us-east-1)" \
  --query 'AssociationExecutionTargets[*].{Instance:ResourceId,Status:Status}' \
  --region us-east-1 --output table

# Compliance state — should be COMPLIANT
aws ssm list-compliance-items \
  --filters "Key=ComplianceType,Values=Association" \
  --query 'ComplianceItems[*].{Resource:ResourceId,Status:Status}' \
  --region us-east-1 --output table

# Output delivered to S3 with KMS encryption
aws s3 ls "s3://my-ssm-output/ssm-output/$ASSOC_ID/" --region us-east-1 --recursive | head -5
```

---

## Step 5 — Wire CloudWatch alarm and remediation

```bash
# Create an SNS topic for alarm notifications
TOPIC_ARN=$(aws sns create-topic --name ssm-patch-alerts --region us-east-1 --query 'TopicArn' --output text)

# Create a CloudWatch alarm on association failures
aws cloudwatch put-metric-alarm \
  --alarm-name "ssm-patch-failures-prod" \
  --metric-name "AssociationFailed" \
  --namespace "AWS/SSM" \
  --statistic "Sum" \
  --period 300 \
  --threshold 1 \
  --comparison-operator "GreaterThanOrEqualToThreshold" \
  --dimensions "Name=AssociationId,Value=$ASSOC_ID" \
  --evaluation-periods 1 \
  --alarm-actions "$TOPIC_ARN" \
  --region us-east-1

# Create an EventBridge rule for auto-remediation on NON_COMPLIANT
RULE_ARN=$(aws events put-rule \
  --name "ssm-patch-remediation" \
  --event-pattern '{
    "source": ["aws.ssm"],
    "detail-type": ["Configuration Compliance State Change"],
    "detail": {"status": ["NON_COMPLIANT"]}
  }' \
  --query 'RuleArn' --output text --region us-east-1)

# Target: trigger an immediate re-run of the association
aws events put-targets \
  --rule "ssm-patch-remediation" \
  --targets '[{"Id":"1","Arn":"arn:aws:ssm:us-east-1:123456789012:automation-definition/AWS-StartAssociation","RoleArn":"arn:aws:iam::123456789012:role/SSMRemediationRole","Input":"{\"AssociationId\":[\"'$ASSOC_ID'\"]}"}]' \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Rate control | Percentage strings (`"10%"`) | Integer counts (`10`) | Deterministic across fleet sizes; no rounding ambiguity |
| Targets on autoscaling fleet | Instance IDs (static) | Tag targets (dynamic) | New instances auto-included; no association edits on scale-out |
| First-run execution | No apply-at-creation | Apply-at-creation ENABLED | Otherwise waits 30+ min for first scheduled tick |
| Output encryption | SSE-S3 or none | SSE-KMS with customer-managed key | Execution artifacts can contain secrets; SSE-S3 lacks per-key audit |
| Schedule syntax | Unix cron (5 fields) | AWS cron (6 fields, seconds-first) | AWS cron is NOT Unix cron; mismatch causes API errors or wrong schedule |
| Compliance gating | Assumes immediate COMPLIANT | Notes PENDING until first run | Compliance only computed AFTER first execution |
| Remediation | Wires without idempotency check | Confirms document is idempotent | Non-idempotent documents cause side effects on remediation re-run |
| Output bucket policy | Assumes bucket accepts writes | Verifies s3:PutObject for ssm service principal | SSM silently drops output without policy; no error surfaced |

---

## Related artifacts

- **Skill definition:** `skills/ssm-association-operator/SKILL.md`
- **Rate control and targeting guide:** `skills/ssm-association-operator/references/rate-control-and-targets.md`
- **Output and compliance guide:** `skills/ssm-association-operator/references/output-and-compliance.md`
- **Slash command:** `commands/aws/operate-ssm-association.md`
- **Eval suite:** `skills/ssm-association-operator/evals/evals.json`
- **Legacy test cases:** `skills/ssm-association-operator/eval/test-cases.yaml`
