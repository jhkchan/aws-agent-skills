# SSM Automation Runbooks Reference

Supplementary reference for the Auto-Remediation Automator skill. Use
when selecting a managed runbook, designing a custom Automation
document, or debugging a runbook execution failure.

## AWS-managed runbooks for common Config findings

| Runbook | Input parameters | Config rule pairing | Safety profile |
|---|---|---|---|
| `AWS-DisableS3BucketPublicAccess` | `S3BucketName`, `AutomationAssumeRole` | `s3-bucket-public-read-prohibited`, `s3-bucket-level-public-access-prohibited` | Reversible — automatic OK |
| `AWS-DisableS3BucketPublicReadWrite` | `S3BucketName`, `AutomationAssumeRole` | `s3-bucket-public-write-prohibited` | Reversible — automatic OK |
| `AWS-EnableS3BucketEncryption` | `S3BucketName`, `KMSKeyARN` (optional), `AutomationAssumeRole` | `s3-bucket-server-side-encryption-enabled` | Reversible — automatic OK |
| `AWS-EnableS3BucketVersioning` | `S3BucketName`, `AutomationAssumeRole` | `s3-bucket-versioning-enabled` | Reversible — automatic OK |
| `AWS-IAMRevokeUnusedAccessKey` | `UserName`, `AccessKeyId` (or look up via IAM), `AutomationAssumeRole` | `iam-access-no-unused-access-keys`, `iam-access-key-rotated` | Reversible — automatic with caveat (active keys in use) |
| `AWS-AttachIAMManagedPolicy` | `UserName`, `PolicyARN`, `AutomationAssumeRole` | Custom IAM rules | Reversible — but adds privilege; manual recommended |
| `AWS-EnableCloudTrailLogging` | `TrailName`, `AutomationAssumeRole` | `cloudtrail-enabled`, `multi-region-cloudtrail-enabled` | Reversible — automatic OK |
| `AWS-RestartEC2Instance` | `InstanceId`, `AutomationAssumeRole` | `ec2-instance-running-check` | Reversible but disruptive — manual |
| `AWS-UpdateLinuxAmi` | `SourceAmiId`, `IamInstanceProfileName`, `AutomationAssumeRole` | Patch compliance rules | Long-running; manual |
| `AWS-CreateManagedLinuxInstanceWithApproval` | Many | Compliance rules requiring approval | Includes `aws:approve` step |

## Runbook parameter patterns

Config's `put-remediation-configurations` accepts two parameter value
types:

- **`ResourceValue`** — Config injects a value derived from the
  finding. Only one supported: `Value: RESOURCE_ID` which maps to the
  non-compliant resource's ID (e.g., bucket name, instance ID).
- **`StaticValue`** — A fixed value supplied at configuration time.
  Used for `AutomationAssumeRole` and any constant.

A common pitfall: trying to inject `RESOURCE_ID` into a parameter that
expects an ARN. Config provides the bare resource ID; the runbook (or
your custom document) must construct the ARN. For managed runbooks,
cross-check the parameter type.

## Custom Automation document structure

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: '<purpose>'
parameters:
  ResourceId:
    type: String
    description: 'Injected by Config via RESOURCE_ID'
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: <stepName>
    action: aws:executeAwsApi | aws:changeInstanceState | aws:approve | aws:sleep | aws:branch | aws:createImage | aws:copySnapshot
    inputs: { ... }
    outputs:
      - Name: <outputName>
        Selector: '<JSONPath>'
        Type: String | StringList | Map | Boolean
    isCritical: true | false  # true = failure aborts the runbook
    onFailure: abort | step:<stepName> | Continue
    nextStep: <nextStepName>  # optional, otherwise sequential
```

Key actions reference:

| Action | Use |
|---|---|
| `aws:executeAwsApi` | Call any AWS API (e.g., `ec2:RevokeSecurityGroupIngress`) |
| `aws:branch` | Conditional branching based on step output |
| `aws:approve` | SNS-based approval gate (required for destructive auto-remediations) |
| `aws:sleep` | Pause (e.g., wait for resource state propagation) |
| `aws:changeInstanceState` | Stop/start/terminate EC2 |
| `aws:createImage` | Snapshot EC2 before destructive step |
| `aws:copySnapshot` | Snapshot EBS |
| `aws:invokeLambdaFunction` | Delegate to Lambda for complex logic |
| `aws:executeAutomation` | Run another runbook (composition) |

## Execution role requirements

The `AutomationAssumeRole` MUST have:

1. A trust policy allowing `ssm.amazonaws.com` to assume it.
2. `AmazonSSMAutomationRole` managed policy (or equivalent) for SSM
   actions.
3. Inline permissions for the AWS APIs the runbook calls (e.g.,
   `ec2:RevokeSecurityGroupIngress` for a custom SG runbook).
4. A pass-role permission if the runbook assumes another role.

Bootstrap command:

```bash
aws iam create-role \
  --role-name AWS-SSM-AutomationExecutionRole \
  --assume-role-policy-document file://ssm-trust-policy.json
aws iam attach-role-policy \
  --role-name AWS-SSM-AutomationExecutionRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AmazonSSMAutomationRole
```

`ssm-trust-policy.json`:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "ssm.amazonaws.com"},
    "Action": "sts:AssumeRole"
  }]
}
```

## Execution status values

| Status | Meaning | Operator action |
|---|---|---|
| `Pending` | Queued, not yet started | None |
| `InProgress` | Running | None |
| `Waiting` | Blocked on `aws:approve` | Approve or reject via SNS |
| `Success` | All steps completed | Verify Config compliance flip |
| `TimedOut` | Exceeded `ExecutionTimeout` (default 60 min) | Investigate slow step; increase timeout or optimize |
| `Cancelled` | Operator cancelled | Investigate root cause |
| `Failed` | A `isCritical: true` step errored | Check `StepExecutions[].FailureMessage` |

## Common execution failures and fixes

| Failure | Root cause | Fix |
|---|---|---|
| `ACCESS_DENIED` on `sts:AssumeRole` | Trust policy missing `ssm.amazonaws.com` | Update trust policy |
| `ACCESS_DENIED` on target API | Inline permission missing | Attach service-specific policy to the role |
| `INVALID_PARAMETER_VALUE` | Static parameter malformed (e.g., ARN typo) | Re-issue `put-remediation-configurations` |
| `RESOURCE_NOT_FOUND` | The resource ID injected by Config no longer exists | Acceptable — resource was deleted; rule will flip COMPLIANT on next eval |
| `THROTTLING` | Runbook invoked at high rate against API-throttled service | Reduce `MaximumAutomaticAttempts` and increase `RetryAttemptSeconds` |
| Step output selector returns null | JSONPath in `Selector` does not match API response shape | Adjust path; test with `aws:executeAwsApi` standalone first |

## Versioning discipline

For AWS-managed runbooks:
- Default `DocumentVersion: "$DEFAULT"` follows AWS updates.
- Pin `DocumentVersion: "1"` for stability; review quarterly.

For custom runbooks:
- Always create with `--version-name <semver>` (e.g., `1.0.0`).
- Use `update-document` with a new `--version-name`; never overwrite
  in place.
- Mark the tested version as default via
  `update-document-default-version --document-version <n>`.

## Custom runbook: revoke open security-group ingress (moved from SKILL.md Step 6)

Custom runbook template (YAML shorthand):

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Revoke ingress rule on a security group open to 0.0.0.0/0'
parameters:
  GroupId:
    type: String
    description: 'The security group ID (Config injects via RESOURCE_ID)'
  AutomationAssumeRole:
    type: String
    description: 'The SSM execution role ARN'
mainSteps:
  - name: GetOpenRules
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: DescribeSecurityGroupRules
      Filters:
        - Name: group-id
          Values: ['{{ GroupId }}']
        - Name: cidr
          Values: ['0.0.0.0/0']
    outputs:
      - Name: RuleIds
        Selector: '$.SecurityGroupRules[].SecurityGroupRuleId'
        Type: StringList
  - name: VerifyFinding
    action: aws:branch
    inputs:
      Choices:
        - NextStep: RevokeRules
          Variable: '{{ GetOpenRules.RuleIds }}'
          Operation: NotEquals
          Value: '[]'
      Default: CompleteNoOp
  - name: RevokeRules
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: RevokeSecurityGroupIngress
      GroupId: '{{ GroupId }}'
      IpPermissions: '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
    isCritical: true
    onFailure: abort
  - name: CompleteNoOp
    action: aws:sleep
    inputs:
      Duration: PT0S
```

Create the document:

```bash
aws ssm create-document \
  --name Custom-RevokeOpenSecurityGroupIngress \
  --document-type Automation \
  --document-format YAML \
  --content file://custom-runbook.yaml \
  --target-type '/AWS::EC2::SecurityGroup'
```

Test before wiring remediation:

```bash
aws ssm start-automation-execution \
  --document-name Custom-RevokeOpenSecurityGroupIngress \
  --parameters '{"GroupId":["sg-0abc123"],"AutomationAssumeRole":["arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole"]}'

aws ssm get-automation-execution \
  --automation-execution-id <execution-id> \
  --query 'AutomationExecution.AutomationExecutionStatus'
```

A custom runbook without a tested execution is the most common cause
of a "remediation wired but doesn't actually fix" failure.
