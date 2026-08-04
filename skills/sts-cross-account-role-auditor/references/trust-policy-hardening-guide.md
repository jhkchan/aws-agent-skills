# Trust Policy Hardening Guide

Reference for the `sts-cross-account-role-auditor` skill. Contains the
confused-deputy service-principal table, ExternalId generation snippet,
the SourceArn vs SourceAccount decision tree, and copy-pasteable
remediation commands for each verdict.

## Confused-deputy-risk service principals

Services that can be invoked by ANY AWS customer and therefore require
`aws:SourceArn` or `aws:SourceAccount` in the trust policy condition:

| Service Principal | Attack Vector |
|---|---|
| `lambda.amazonaws.com` | Any customer can create a Lambda function that calls AssumeRole |
| `ec2.amazonaws.com` | Any customer can launch an EC2 instance with an instance profile |
| `cloudformation.amazonaws.com` | Any customer can create a stack that passes a role |
| `eks.amazonaws.com` | EKS cluster creation cross-account |
| `eks-nodegroup.amazonaws.com` | EKS node group cross-account |
| `eks-fargate.amazonaws.com` | EKS Fargate profile cross-account |
| `ecs-tasks.amazonaws.com` | ECS task execution cross-account |
| `ecs.amazonaws.com` | ECS service-linked role cross-account |
| `states.amazonaws.com` | Step Functions can be invoked cross-account |
| `events.amazonaws.com` | EventBridge rules can be targeted cross-account |
| `pipes.amazonaws.com` | EventBridge Pipes cross-account |
| `sns.amazonaws.com` | SNS cross-account subscriptions |
| `sqs.amazonaws.com` | SQS cross-account messaging |
| `codebuild.amazonaws.com` | CodeBuild cross-account project builds |
| `codepipeline.amazonaws.com` | CodePipeline cross-account pipeline execution |
| `apigateway.amazonaws.com` | API Gateway cross-account forwarding |
| `backup.amazonaws.com` | AWS Backup cross-account backup roles |
| `cloudtrail.amazonaws.com` | CloudTrail cross-account logging |
| `config.amazonaws.com` | Config aggregator cross-account |
| `config-multiaccountsetup.amazonaws.com` | Config multi-account setup |
| `controltower.amazonaws.com` | Control Tower member roles |
| `member.org.stacksets.cloudformation.amazonaws.com` | Organizations StackSets |
| `auditmanager.amazonaws.com` | Audit Manager service-linked roles |
| `macie.amazonaws.com` | Macie cross-account aggregation |
| `securityhub.amazonaws.com` | Security Hub cross-account aggregation |
| `guardduty.amazonaws.com` | GuardDuty cross-account aggregation |
| `wafv2.amazonaws.com` | WAF v2 service roles |
| `waf-regional.amazonaws.com` | WAF Regional service roles |
| `firehose.amazonaws.com` | Kinesis Firehose cross-account delivery |
| `es.amazonaws.com` | OpenSearch cross-account delivery |
| `aoss.amazonaws.com` | OpenSearch Serverless cross-account |
| `bedrock.amazonaws.com` | Bedrock service roles |

## ExternalId generation snippet

Generate a cryptographically random ExternalId:

```bash
# Generate a 32-character alphanumeric ExternalId
python3 -c "import secrets, string; print(''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(32)))"
```

The ExternalId MUST be:
- At least 16 characters long (32 recommended).
- Alphanumeric (no special characters — some third-party integrations break).
- Opaque (not a company name, project code, or derivable pattern).
- Matched with `StringEquals`, NOT `StringLike` (wildcards weaken the guard).

## SourceArn vs SourceAccount decision tree

```
Does the service principal appear on the confused-deputy-risk list?
├── NO → Verify service docs; if single-account by design, OK without guard.
└── YES → Is aws:SourceArn available for this service?
    ├── YES → Use aws:SourceArn (ArnLike) + aws:SourceAccount (StringEquals)
    │        (defense-in-depth: SourceArn for precision, SourceAccount as fallback)
    └── NO → Is aws:SourceAccount available?
        ├── YES → Use aws:SourceAccount (StringEquals) — minimum acceptable guard
        └── NO → Service cannot be safely used as a Principal. Use a different
                 integration pattern (e.g., cross-account role with ExternalId).
```

## Remediation commands

### Add ExternalId to a cross-account trust policy

```bash
# 1. Backup the current trust policy
aws iam get-role --role-name <role-name> \
  --query Role.AssumeRolePolicyDocument \
  --output json > /tmp/<role-name>-trust-backup-$(date +%s).json

# 2. Create the updated trust policy file with ExternalId added
# (edit the backup file to add the Condition block)

# 3. Apply the updated trust policy
aws iam update-assume-role-policy \
  --role-name <role-name> \
  --policy-document file:///tmp/<role-name>-trust-updated.json
```

### Add SourceArn/SourceAccount to a service-principal trust

```bash
# 1. Backup
aws iam get-role --role-name <role-name> \
  --query Role.AssumeRolePolicyDocument \
  --output json > /tmp/<role-name>-trust-backup-$(date +%s).json

# 2. Edit to add Condition:
#    "Condition": {
#      "ArnLike": {
#        "aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"
#      },
#      "StringEquals": {
#        "aws:SourceAccount": "123456789012"
#      }
#    }

# 3. Apply
aws iam update-assume-role-policy \
  --role-name <role-name> \
  --policy-document file:///tmp/<role-name>-trust-updated.json
```

### Remove a wildcard Principal statement

```bash
# 1. Backup FIRST (critical — this is a destructive operation)
aws iam get-role --role-name <role-name> \
  --query Role.AssumeRolePolicyDocument \
  --output json > /tmp/<role-name>-trust-backup-$(date +%s).json

# 2. Remove the wildcard statement from the backup file
# 3. Apply the updated policy (without the wildcard statement)
aws iam update-assume-role-policy \
  --role-name <role-name> \
  --policy-document file:///tmp/<role-name>-trust-updated.json

# 4. Audit CloudTrail for unauthorized AssumeRole events during exposure window
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=AssumeRole \
  --max-results 50
```

## Common trust-policy patterns found in the wild

### Pattern: "Everyone can assume" (most dangerous)

```json
{"Principal": "*", "Action": "sts:AssumeRole"}
```

Verdict: WILDCARD_TRUST / CRITICAL. Seen in dev/test environments that
were promoted to production without review.

### Pattern: Cross-account SaaS without ExternalId

```json
{"Principal": {"AWS": "arn:aws:iam::VENDOR:root"}, "Action": "sts:AssumeRole"}
```

Verdict: EXTERNAL_TRUST / HIGH. The vendor's account admin can grant
access to any principal in their account. Add ExternalId.

### Pattern: Confused-deputy service role

```json
{"Principal": {"Service": "lambda.amazonaws.com"}, "Action": "sts:AssumeRole"}
```

Verdict: EXTERNAL_TRUST / HIGH. Any AWS customer's Lambda function can
trigger the assumption. Add SourceArn + SourceAccount.

### Pattern: Properly guarded cross-service role

```json
{
  "Principal": {"Service": "lambda.amazonaws.com"},
  "Action": "sts:AssumeRole",
  "Condition": {
    "ArnLike": {"aws:SourceArn": "arn:aws:lambda:us-east-1:123456789012:function:*"},
    "StringEquals": {"aws:SourceAccount": "123456789012"}
  }
}
```

Verdict: CONDITIONAL / MODERATE. Confused-deputy protected; the role is
still assumable via a service outside direct account control.

### Pattern: Same-account scoped

```json
{"Principal": {"AWS": "arn:aws:iam::123456789012:role/app-role"}, "Action": "sts:AssumeRole"}
```

Verdict: OK / LOW. Same account, specific role ARN.
