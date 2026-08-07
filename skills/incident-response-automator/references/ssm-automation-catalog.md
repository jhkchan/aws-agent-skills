# SSM Automation Documents for Incident Response — Reference

This reference catalogues AWS-managed and common custom SSM Automation
documents used in automated incident response workflows. Each entry
includes parameters, IAM requirements, and known failure modes.

## AWS-managed documents (preferred when applicable)

### AWS-IsolateEC2Instance

**Purpose:** Move an EC2 instance into a designated quarantine VPC
subnet where it cannot reach the internet or other internal resources.

**Parameters:**
- `InstanceId` (required) — the compromised instance ID.
- `SubnetId` (required) — the quarantine subnet (pre-provisioned, no
  internet gateway, no route to prod CIDRs).
- `AutomationAssumeRole` (optional) — IAM role for the automation.

**Required IAM permissions on the assume role:**
- `ec2:ModifyInstanceAttribute` on the target instance ARN
- `ec2:DescribeInstances` (read)
- `ec2:DescribeSubnets` (read)
- `ec2:DescribeVpcs` (read)

**Failure modes:**
- Instance does not exist (terminated before automation runs) —
  `InvalidInstanceID.NotFound`. Handle by catching and exiting cleanly.
- Quarantine subnet does not exist or is misconfigured — pre-provision
  via CloudFormation with `DeletionPolicy: Retain`.
- Instance is in a different VPC than the quarantine subnet — moves
  require VPC peering or TGW; the document does NOT support cross-VPC
  moves.

### AWS-DisableIAMUserAccessKey

**Purpose:** Deactivate a specific IAM user's access key.

**Parameters:**
- `UserName` (required)
- `AccessKeyId` (required) — the AKIA... identifier.
- `AutomationAssumeRole` (optional)

**Required IAM permissions:**
- `iam:UpdateAccessKey` on `arn:aws:iam::*:user/*`

**Limitation:** Does NOT revoke active STS sessions. Pair with
`AWS-RevokeSession` or a custom `put-user-policy` Deny-all for full
revocation.

### AWS-RevokeSession

**Purpose:** Force re-evaluation of active STS sessions for a role by
attaching a Deny-all permission boundary.

**Parameters:**
- `RoleName` (required) — the role whose sessions to revoke.
- `AutomationAssumeRole` (optional)

**Required IAM permissions:**
- `iam:PutRolePermissionsBoundary` on the target role ARN
- `iam:DeleteRolePermissionsBoundary` (for rollback)

**Behavior:**
1. Attaches a permissions boundary that denies ALL actions.
2. Active sessions re-evaluate their permissions on the next API call
   and find Deny-all — effectively ends them.
3. The boundary remains until manually removed (rollback).

**Important:** This affects ALL sessions on the role, including
legitimate ones. Use sparingly and have a rollback path documented.

### AWS-RestartEC2InstanceLaunchedTemplate

**Purpose:** Restart an EC2 instance from a known-good launch template
(recovery from a compromised instance).

**Parameters:**
- `InstanceId` (required) — the compromised instance.
- `LaunchTemplateId` (required) — the clean template to use for the
  replacement.
- `AutomationAssumeRole` (optional)

**Behavior:** Terminates the old instance and launches a new one from
the specified template, preserving the Elastic IP and tags.

### AWS-CreateManagedLinuxInstance

**Purpose:** Launch a managed forensic analysis instance with pre-
installed tools (Volatility, SIFT, LiME for memory capture).

**Parameters:**
- `SubnetId` (required)
- `InstanceType` (optional, default `t3.large`)
- `AmiId` (optional — defaults to latest Amazon Linux 2023 forensic AMI)

**Use case:** Spin up a forensic workstation in the quarantine subnet to
analyze snapshots from the compromised instance.

### AWSSupport-ExecuteEC2Rescue

**Purpose:** Run EC2 Rescue (an AWS tool for diagnosing and fixing EC2
boot/configuration issues) on a target instance.

**Parameters:**
- `InstanceId` (required)

**Use case:** Post-incident recovery — repair a compromised instance
that cannot boot cleanly.

## Custom documents

### Memory capture (Linux)

**Custom document for capturing RAM from a Linux EC2 instance for
forensic analysis.** Requires the LiME kernel module pre-installed on
the target AMI.

```yaml
---
schemaVersion: '0.3'
description: Capture memory from a Linux EC2 instance for forensic analysis
assumeRole: '{{ AutomationAssumeRole }}'
parameters:
  InstanceId:
    type: String
    description: The target instance ID
  S3Bucket:
    type: String
    description: S3 bucket for the memory dump
  IncidentId:
    type: String
    description: Incident identifier (used in snapshot tags)
  AutomationAssumeRole:
    type: String
    description: The role for this automation
    default: ''
mainSteps:
  - name: CaptureMemory
    action: aws:runCommand
    inputs:
      DocumentName: AWS-RunShellScript
      InstanceIds:
        - '{{ InstanceId }}'
      Parameters:
        commands:
          - set -euo pipefail
          - TIMESTAMP=$(date -u +%Y%m%dT%H%M%SZ)
          - OUTPUT="/tmp/mem-${TIMESTAMP}.lime"
          - insmod /opt/lime/lime.ko "path=${OUTPUT} format=lime"
          - aws s3 cp "${OUTPUT}" "s3://{{ S3Bucket }}/forensic/{{ IncidentId }}/${TIMESTAMP}-mem.lime"
          - rm -f "${OUTPUT}"
          - echo "Memory capture uploaded to s3://{{ S3Bucket }}/forensic/{{ IncidentId }}/${TIMESTAMP}-mem.lime"
    timeoutSeconds: 1800
    onFailure: Abort
outputs:
  - CaptureMemory.Output
```

**IAM requirements:**
- `ssm:SendCommand` on the target instance
- `s3:PutObject` on `arn:aws:s3:::<forensic-bucket>/forensic/*`

**Failure modes:**
- LiME not installed on the target — fails at `insmod`. Pre-bake the
  module into the golden AMI.
- Memory dump larger than instance ephemeral disk — fails at the
  `aws s3 cp`. Use an instance type with sufficient ephemeral storage
  or stream directly to S3 multipart.
- SSM agent offline on the target — fails at `aws:runCommand`. Check
  `aws ssm describe-instance-information` first.

### EBS multi-volume snapshot

**Custom document for snapshotting ALL EBS volumes attached to an
instance with consistent tagging.**

```yaml
---
schemaVersion: '0.3'
description: Snapshot all EBS volumes attached to an instance for forensics
assumeRole: '{{ AutomationAssumeRole }}'
parameters:
  InstanceId:
    type: String
  IncidentId:
    type: String
  AutomationAssumeRole:
    type: String
    default: ''
mainSteps:
  - name: GetVolumeIds
    action: aws:executeAwsApi
    inputs:
      Service: ec2
      Api: DescribeInstances
      InstanceIds:
        - '{{ InstanceId }}'
    outputs:
      - Name: VolumeIds
        Selector: '$.Reservations[0].Instances[0].BlockDeviceMappings[*].Ebs.VolumeId'
        Type: StringList
  - name: SnapshotEach
    action: aws:loop
    inputs:
      Iterators:
        - Name: VolumeId
          Values: '{{ GetVolumeIds.VolumeIds }}'
      Steps:
        - Name: SnapshotOne
          Action: aws:executeAwsApi
          Inputs:
            Service: ec2
            Api: CreateSnapshot
            VolumeId: '{{ VolumeId }}'
            Description: 'Forensic snapshot for incident {{ IncidentId }}'
            TagSpecifications:
              - ResourceType: snapshot
                Tags:
                  - { Key: IncidentId, Value: '{{ IncidentId }}' }
                  - { Key: Preserve, Value: 'true' }
                  - { Key: SourceVolume, Value: '{{ VolumeId }}' }
    timeoutSeconds: 600
outputs:
  - SnapshotEach.Output
```

**IAM requirements:**
- `ec2:DescribeInstances` (read)
- `ec2:CreateSnapshot` on `arn:aws:ec2:*:*:volume/*`
- `ec2:CreateTags` on `arn:aws:ec2:*:*:snapshot/*`

## Document invocation patterns

### Direct (one-shot)

```bash
aws ssm start-automation-execution \
  --document-name AWS-IsolateEC2Instance \
  --parameters InstanceId=i-0abc12345,SubnetId=subnet-xxx
```

### From Step Functions (synchronous with task token)

```json
{
  "Type": "Task",
  "Resource": "arn:aws:states:::ssm:start-automation-execution:waitForTaskToken",
  "Parameters": {
    "DocumentName": "AWS-IsolateEC2Instance",
    "Parameters": {
      "InstanceId.$": "$.instanceId",
      "SubnetId.$": "$.quarantineSubnetId"
    }
  },
  "Next": "NotifyComplete"
}
```

### From Lambda (asynchronous, poll for status)

```python
import boto3
ssm = boto3.client('ssm')

def lambda_handler(event, context):
    response = ssm.start_automation_execution(
        DocumentName='AWS-IsolateEC2Instance',
        Parameters={
            'InstanceId': [event['instanceId']],
            'SubnetId': [event['quarantineSubnetId']]
        }
    )
    return {'automationExecutionId': response['AutomationExecutionId']}
```

## Pre-flight validation

Before relying on any SSM Automation document in production:

1. **Verify the document exists in the target region:**
   ```bash
   aws ssm describe-document --name AWS-IsolateEC2Instance --region <region>
   ```

2. **Verify the assume role has the required permissions:** use the IAM
   Policy Simulator with the specific action sequence.

3. **Run the document in dry-run mode** (if supported) or against a test
   instance first.

4. **Verify the SSM agent is online on the target instance:**
   ```bash
   aws ssm describe-instance-information \
     --filters "Key=InstanceIds,Values=i-0abc12345" \
     --query 'InstanceInformationList[0].[PingStatus,LastPingDateTime]'
   ```
   PingStatus must be `Connection Lost` or `Online`. `NotConnected` means
   the agent is offline and SSM actions will fail.
