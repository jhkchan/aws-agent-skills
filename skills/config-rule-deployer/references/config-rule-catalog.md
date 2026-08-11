# AWS Config Rule Catalog and Deployment Reference

Load this reference when planning or executing any Config rule
deployment. The procedures below are the canonical sequences for each
rule archetype, with pre-checks, command sequence, post-verification,
and remediation wiring.

## Decision tree — which rule type

| Scenario | Use | Why |
|---|---|---|
| Common security/compliance check (S3, IAM, EC2, VPC) | **Managed rule** | AWS-maintained, no Lambda needed, pre-built |
| Custom logic (tag format, naming convention, multi-resource check) | **Custom Lambda rule** | Full control over evaluation logic |
| Bulk baseline (CIS, PCI-DSS, NIST) | **Conformance pack** | Deploy 20+ rules from one YAML template |
| Org-wide compliance (all accounts) | **Organization config rule** | Deploy once from management account |
| Pre-deployment validation (block non-compliant creation) | **Proactive rule (CFN hook)** | Prevent non-compliant resources at creation |
| Auto-fix non-compliant resources | **SSM Automation remediation** | Trigger auto-remediation on non-compliance |
| Multi-account compliance visibility | **Aggregator + Security Hub** | Central view across accounts/regions |

## Managed rule procedure

**When to use:** common security and compliance checks covered by 100+
AWS-managed rules.

**Pre-checks:**
1. Configuration recorder running (`describe-configuration-recorders`).
2. Delivery channel configured (`describe-delivery-channels`).
3. ManagedRuleIdentifier valid.
4. Resource scope matches supported resource types.

**Command sequence:**
```bash
# 1. Snapshot existing rule (if updating)
aws configservice describe-config-rules \
  --config-rule-names <name> --output json \
  > /tmp/<name>-backup-$(date +%s).json

# 2. CONFIRM gate, then put-config-rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "s3-bucket-public-read-prohibited",
    "Description": "Detects S3 buckets with public read access",
    "Source": {
      "Owner": "AWS",
      "SourceIdentifier": "S3_BUCKET_PUBLIC_READ_PROHIBITED"
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::S3::Bucket"]
    },
    "ConfigRuleState": "ACTIVE"
  }'

# 3. Force evaluation
aws configservice start-config-rules-evaluation \
  --config-rule-names s3-bucket-public-read-prohibited

# 4. Verify compliance (wait 1-30 min)
aws configservice get-compliance-summary \
  --config-rule-names s3-bucket-public-read-prohibited
```

**Common managed rules by category:**

| Category | Rule identifier | What it checks |
|---|---|---|
| S3 Security | S3_BUCKET_PUBLIC_READ_PROHIBITED | No public read ACLs |
| S3 Security | S3_BUCKET_SERVER_SIDE_ENCRYPTION_ENABLED | SSE enabled |
| S3 Security | S3_BUCKET_VERSIONING_ENABLED | Versioning enabled |
| IAM | IAM_USER_NO_POLICIES | No policies on users (use groups) |
| IAM | IAM_MFA_REQUIREMENT_FOR_CONSOLE | MFA enabled for console users |
| IAM | ROOT_ACCOUNT_MFA_ENABLED | Root MFA enabled |
| IAM | IAM_PASSWORD_POLICY | Password policy meets minimum |
| EC2 | EC2_VOLUME_INUSE_CHECK | EBS volumes attached |
| EC2 | INSTANCES_IN_VPC_ONLY | No EC2-Classic instances |
| VPC | VPC_FLOW_LOGS_ENABLED | Flow logs on all VPCs |
| Security | CLOUD_TRAIL_ENABLED | CloudTrail active |
| Security | GUARDDUTY_ENABLED_CIF | GuardDuty enabled |
| Compliance | MULTI_REGION_CLOUD_TRAIL_ENABLED | Trail covers all regions |
| Tagging | REQUIRED_TAGS | Required tags present |

**Common failure modes:**
- Recorder stopped — all rules report stale compliance. Verify via
  `describe-configuration-recorder-status`.
- Unsupported resource type in scope — rule evaluates nothing. Check
  the managed rule documentation for supported types.

## Custom Lambda rule procedure

**When to use:** custom evaluation logic not covered by managed rules
(custom tag formats, naming conventions, cross-resource checks).

**Pre-checks:**
1. Lambda function exists (`get-function`).
2. Lambda resource-based policy includes permission for
   `config.amazonaws.com`.
3. Lambda IAM role has `config:PutEvaluations` permission.
4. Lambda timeout <= 60s.
5. Recorder running.

**Command sequence:**
```bash
# 1. Create the Lambda function
aws lambda create-function \
  --function-name config-rule-required-tags \
  --runtime python3.12 \
  --role arn:aws:iam::111111111111:role/config-rule-lambda-role \
  --handler index.lambda_handler \
  --zip-file fileb://function.zip \
  --timeout 30 \
  --memory-size 256

# 2. Add permission for Config to invoke
aws lambda add-permission \
  --function-name config-rule-required-tags \
  --statement-id AllowConfigToInvoke \
  --action lambda:InvokeFunction \
  --principal config.amazonaws.com \
  --source-account 111111111111

# 3. Create the Config rule
aws configservice put-config-rule \
  --config-rule '{
    "ConfigRuleName": "ec2-required-tags",
    "Source": {
      "Owner": "CUSTOM_LAMBDA",
      "SourceIdentifier": "arn:aws:lambda:us-east-1:111111111111:function:config-rule-required-tags",
      "SourceDetails": [
        {
          "EventSource": "aws.config",
          "MessageType": "ConfigurationItemChangeNotification"
        }
      ]
    },
    "Scope": {
      "ComplianceResourceTypes": ["AWS::EC2::Instance"]
    },
    "InputParameters": "{\"requiredTags\": \"Environment,Owner,CostCenter\"}"
  }'

# 4. Force evaluation
aws configservice start-config-rules-evaluation --config-rule-names ec2-required-tags
```

**Lambda function IAM role policy (minimum):**
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["config:PutEvaluations", "config:GetResourceConfigHistory"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
      "Resource": "arn:aws:logs:*:*:*"
    }
  ]
}
```

**Lambda function skeleton:**
```python
import json
import boto3

config = boto3.client('config')
ec2 = boto3.client('ec2')

def lambda_handler(event, context):
    invoking_event = json.loads(event['invokingEvent'])
    configuration_item = invoking_event['configurationItem']
    rule_parameters = json.loads(event['ruleParameters'])
    required_tags = rule_parameters.get('requiredTags', '').split(',')
    
    tags = {t['key']: t['value'] for t in configuration_item.get('tags', [])}
    missing = [t for t in required_tags if t not in tags]
    
    compliance_type = 'COMPLIANT' if not missing else 'NON_COMPLIANT'
    annotation = f'Missing tags: {", ".join(missing)}' if missing else 'All required tags present'
    
    config.put_evaluations(
        Evaluations=[{
            'ComplianceResourceType': configuration_item['resourceType'],
            'ComplianceResourceId': configuration_item['resourceId'],
            'ComplianceType': compliance_type,
            'Annotation': annotation,
            'OrderingTimestamp': configuration_item['configurationItemCaptureTime']
        }],
        ResultToken=event['resultToken']
    )
```

**Common failure modes:**
- EvaluationError for all resources — Lambda permission for Config
  missing. Add via `lambda:add-permission`.
- EvaluationError for some resources — Lambda function erroring on
  specific resource configurations. Check CloudWatch Logs for the
  function.

## Conformance pack procedure

**When to use:** bulk deployment of 10+ rules as a compliance baseline.

**Pre-checks:**
1. Template body valid YAML/JSON with at least one rule.
2. Template body <= 256 KB.
3. All managed rule identifiers in template are valid.
4. Total conformance pack count + new <= 25 per region.

**Command sequence:**
```bash
aws configservice put-conformance-pack \
  --conformance-pack-name "cis-aws-benchmark" \
  --template-body file://conformance-pack.yaml \
  --conformance-pack-input-parameters \
    ParameterKey=ConformancePackName,ParameterValue=cis-aws-benchmark

# Verify pack status
aws configservice describe-conformance-pack-status \
  --conformance-pack-names cis-aws-benchmark
```

**Conformance pack template structure (YAML):**
```yaml
Resources:
  Rule1:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: iam-no-inline-policy
      Source:
        Owner: AWS
        SourceIdentifier: IAM_NO_INLINE_POLICY_CHECK
      Scope:
        ComplianceResourceTypes: ["AWS::IAM::User"]
  Rule2:
    Type: AWS::Config::ConfigRule
    Properties:
      ConfigRuleName: root-mfa-enabled
      Source:
        Owner: AWS
        SourceIdentifier: ROOT_ACCOUNT_MFA_ENABLED
      MaximumExecutionFrequency: One_Hour
  Remediation1:
    Type: AWS::Config::RemediationConfiguration
    Properties:
      ConfigRuleName: iam-no-inline-policy
      TargetType: SSM_DOCUMENT
      TargetId: AWS-RemoveIAMUserPolicy
      Automatic: false
      Parameters: {}
```

## Remediation wiring matrix

| Non-compliance | SSM document | Auto? |
|---|---|---|
| S3 public read | AWS-DisableS3BucketPublicReadWrite | Yes |
| S3 no encryption | AWS-EnableS3BucketEncryption | Yes |
| IAM access key old | AWS-IAMRotateAccessKey | Manual |
| Security group open | AWS-DisablePublicAccessSecurityGroup | Yes |
| RDS public snapshot | AWS-ModifyRDSInstanceSnapshotPublicAccess | Yes |
| EC2 instance public IP | AWS-TerminateEC2Instance (destructive) | Manual |

**Remediation parameters pattern:**
```json
{
  "S3BucketName": {
    "ResourceValue": {"Value": "RESOURCE_ID"}
  }
}
```
The `ResourceValue` extracts the resource ID from the non-compliant
resource and passes it to the SSM document as input.

## Evaluation mode decision guide

| Rule type | Evaluation trigger | Max frequency | Best for |
|---|---|---|---|
| Configuration-change | Resource create/update/delete | N/A (event-driven) | Security rules (detect drift immediately) |
| Periodic | Timer (1h/3h/6h/12h/24h) | MaximumExecutionFrequency | Account-level checks (password policy, root MFA) |
| Hybrid | Config-change + periodic re-check | MaximumExecutionFrequency for re-check | Rules needing both immediate + periodic coverage |
| Proactive | CloudFormation create/update | N/A (pre-deployment) | Prevent non-compliant resource creation |

## Recorder setup

```bash
# Create the configuration recorder
aws configservice put-configuration-recorder \
  --configuration-recorder name=default,roleARN=arn:aws:iam::111111111111:role/Config-Role \
  --recording-group allSupported=true,includeGlobalResourceTypes=true

# Create the delivery channel
aws configservice put-delivery-channel \
  --delivery-channel name=default,s3BucketName=config-bucket-111111111111,configSnapshotDeliveryProperties={deliveryFrequency=TwentyFour_Hours}

# Start the recorder
aws configservice start-configuration-recorder \
  --configuration-recorder-name default

# Verify
aws configservice describe-configuration-recorder-status
```

## Security Hub integration

Security Hub automatically imports Config compliance findings when
enabled. To verify:

```bash
# Check Security Hub is enabled
aws securityhub get-enabled-standards

# View Config findings in Security Hub
aws securityhub get-findings \
  --filters '{"ProductFields":[{"Key":"aws/securityhub/ProductName","Value":["CIS AWS Foundations","AWS Config"],"Comparison":"EQUALS"}]}'
```

To suppress a finding in Security Hub without changing Config compliance:
```bash
aws securityhub update-findings \
  --filters '{"Id":[{"Value":"<finding-id>","Comparison":"EQUALS"}]}' \
  --note "Suppressed: known exception approved by security team" \
  --record-state ARCHIVED
```

Note: archiving in Security Hub does NOT change the Config rule
compliance status. They are separate systems.

## Cost reference (2026)

- Configuration recording: $0.003 per configuration item recorded.
- Config rule evaluations: $0.001 per rule evaluation.
- Conformance pack evaluations: included in rule evaluation cost.
- S3 storage for configuration data: standard S3 pricing.
- Lambda invocations for custom rules: standard Lambda pricing.
- Typical account (50 resource types, 100 resources, 10 rules):
  ~$50-150/month.
- Large enterprise (500+ resources, 100+ rules, multi-region):
  ~$500-2000/month.

Cost optimization: use resource scope to limit which resource types
are evaluated. Scoping a rule to `AWS::S3::Bucket` instead of
`allSupported` reduces evaluation count by ~80% in typical accounts.

## Full anti-patterns NEVER list

- NEVER deploy a Config rule without first verifying the configuration
  recorder is running. A stopped recorder means ALL rules report stale
  compliance.
- NEVER assume `put-config-rule` triggers immediate evaluation. The rule
  evaluates on the next resource change or at the next
  MaximumExecutionFrequency interval. Always run
  `start-config-rules-evaluation` after creating a rule.
- NEVER assume remediation is automatic. Adding an SSM Automation document
  does NOT auto-remediate unless `Automatic: true` is explicitly set.
- NEVER deploy a custom Lambda rule without verifying the Lambda resource-
  based permission for `config.amazonaws.com`.
- NEVER deploy a custom Lambda rule where the function timeout exceeds 60
  seconds. Config's invocation has a hard 60s timeout.
- NEVER use a Config rule scope that includes unsupported resource types.
  The rule accepts the config but evaluates nothing.
- NEVER exceed 150 Config rules per region without requesting a limit
  increase. The 151st rule is silently rejected.
- NEVER deploy a conformance pack with an invalid template body. The
  CloudFormation stack creation fails silently.
- NEVER assume Security Hub integration is bi-directional. Config forwards
  TO Security Hub; remediating in Security Hub does NOT change Config
  compliance status.
- NEVER delete a Config rule to "stop noise" without understanding why
  resources are non-compliant. Set `ConfigRuleState: INACTIVE` instead.
- NEVER forget the SSM Automation document must be in the SAME region as
  the Config rule. Cross-region remediation is not supported.
- NEVER auto-execute a state-changing Config CLI without the CONFIRM gate.
  `put-config-rule` overwrites with no version history.
- NEVER deploy an organization config rule from a member account. Org rules
  must be deployed from the management account or delegated administrator.
- NEVER use periodic evaluation for security-critical rules when
  configuration-change evaluation is available. Periodic can take up to 24h.
- NEVER deploy proactive rules without testing the CloudFormation hook in a
  non-production account. A misconfigured hook can block ALL CFN deployments.

## Expert heuristic: stale compliance diagnostic decision tree

```
Rule shows "Compliant" for all resources
   ├─ Is the configuration recorder running?
   │    ├─ NO → Stale compliance — restart recorder, force evaluation
   │    └─ YES → Check last evaluation time
   │              ├─ LastSuccessfulInvocationTime is old (> MaximumExecutionFrequency)?
   │              │    ├─ YES → Stale — force start-config-rules-evaluation
   │              │    └─ NO → Likely real compliance
   │              └─ For custom rules: Lambda had errors?
   │                   ├─ Check describe-config-rule-evaluation-status
   │                   └─ Check CloudWatch Logs for the Lambda function
   │
   └─ Confirm via get-compliance-details-by-config-rule:
        aws configservice get-compliance-details-by-config-rule \
          --config-rule-name <name>
        If empty result → no evaluations performed (stale or broken)
```

**Per-rule-type staleness indicators:**

| Rule type | What to check when compliance looks stale |
|---|---|
| Managed rule | Recorder running? `describe-configuration-recorder-status`. Rule ACTIVE? |
| Custom Lambda rule | Lambda exists? Permission for Config? Last invocation had errors? Check CW Logs. |
| Periodic rule | MaximumExecutionFrequency elapsed since last evaluation? Force evaluation. |
| Conformance pack | CloudFormation stack status = CREATE_COMPLETE? Any drift? |
| Org rule | Management account permissions intact? Aggregator authorized? |

## Pre-flight safety checks (full detail)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation, the
  operator MUST emit CONFIRM and await approval.
- **PutConfigRule overwrites the entire rule configuration.** Always
  snapshot before modification.
- For custom Lambda rules, verify the function's resource-based policy
  includes a permission statement for `config.amazonaws.com`. #1 cause of
  custom rule evaluation errors.
- For remediation configurations, verify the SSM Automation document exists
  AND the Config service-linked role has `ssm:StartAutomationExecution`.
- For conformance packs, validate the template YAML before deployment.
  Errors surface as CloudFormation stack events, not Config API errors.
- For organization config rules, verify the management account has
  authorized the Config service as a delegated administrator.
- Prefer configuration-change rules over periodic for security-critical
  checks. Configuration-change detects within minutes; periodic can take 24h.
