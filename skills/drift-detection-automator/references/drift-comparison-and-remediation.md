# Drift Comparison and Remediation Reference

Supplementary reference for the Drift Detection Automator skill. Use
when designing the Lambda comparison function, selecting a remediation
strategy, or debugging a drift remediation failure.

## Drift severity classification matrix

| Property category | Example properties | Severity | Why |
|---|---|---|---|
| Security posture | `SecurityGroups`, `PolicyDocument`, `AssumeRolePolicyDocument` | CRITICAL | Direct security impact — possible unauthorized access |
| Encryption | `BucketEncryption`, `KmsMasterKeyId`, `EnableCloudwatchLogsExports` | CRITICAL | Data protection regression |
| Access control | `PublicAccessBlockConfiguration`, `BucketPolicy`, `AccessControl` | CRITICAL | Public exposure risk |
| IAM permissions | `ManagedPolicyArns`, `PermissionsBoundary`, `Policies` | HIGH | Privilege escalation risk |
| Network | `SubnetId`, `VpcId`, `RouteTableId` | HIGH | Network topology change — possible connectivity break |
| Capacity | `DesiredCapacity`, `MinSize`, `MaxSize` (if not suppressed) | MEDIUM | Capacity impact but not security |
| Tags | `Tags`, `TagSpecifications` | LOW | Metadata — compliance but not operational impact |
| Configuration | `EngineVersion`, `InstanceType`, `AllocatedStorage` | MEDIUM | Performance/cost impact |
| Logging | `LoggingProperties`, `CloudWatchLogsLogGroupArn` | MEDIUM | Observability loss |

## Comparison Lambda — full implementation

```python
import boto3
import json
from datetime import datetime

cfn = boto3.client('cloudformation')
sns = boto3.client('sns')
ssm = boto3.client('ssm')
s3 = boto3.client('s3')

CRITICAL_PROPS = [
    'SecurityGroups', 'GroupSet', 'SecurityGroupIngress', 'SecurityGroupEgress',
    'PolicyDocument', 'AssumeRolePolicyDocument', 'PermissionsBoundary',
    'BucketEncryption', 'ServerSideEncryptionConfiguration',
    'PublicAccessBlockConfiguration', 'BucketPolicy', 'AccessControl',
    'KmsMasterKeyId', 'EnableCloudwatchLogsExports'
]

HIGH_PROPS = [
    'ManagedPolicyArns', 'Policies', 'SubnetId', 'VpcId',
    'RouteTableId', 'InternetGatewayId', 'NatGatewayId'
]

def load_suppression_rules():
    """Load suppression rules from SSM Parameter Store."""
    try:
        resp = ssm.get_parameter(Name='/drift-detection/suppression-rules')
        return json.loads(resp['Parameter']['Value'])
    except ssm.exceptions.ParameterNotFound:
        return {}

def classify_drift(drift, suppression_rules):
    """Classify a single resource drift by severity."""
    resource_type = drift['ResourceType']
    differences = drift.get('PropertyDifferences', [])

    # Check if ALL differences are suppressed
    suppressed_props = suppression_rules.get(resource_type, [])
    non_suppressed = [d for d in differences if d['PropertyPath'] not in suppressed_props]

    if not non_suppressed and differences:
        return 'SUPPRESSED', differences

    if not differences:
        return 'NONE', []

    severity = 'LOW'
    for diff in non_suppressed:
        prop = diff['PropertyPath']
        if any(c in prop for c in CRITICAL_PROPS):
            return 'CRITICAL', non_suppressed
        elif any(h in prop for h in HIGH_PROPS):
            severity = 'HIGH'

    if severity == 'LOW' and any(d['DifferenceType'] in ['ADD', 'REMOVE'] for d in non_suppressed):
        severity = 'MEDIUM'

    return severity, non_suppressed

def compare_stack_drift(stack_name):
    """Full comparison for a single stack."""
    suppression_rules = load_suppression_rules()

    drifts = cfn.describe_stack_resource_drifts(
        StackName=stack_name,
        StackResourceDriftStatusFilters=['MODIFIED', 'DELETED', 'ADDITION']
    )

    results = []
    for drift in drifts['StackResourceDrifts']:
        severity, relevant_diffs = classify_drift(drift, suppression_rules)
        results.append({
            'stack_name': stack_name,
            'resource_id': drift['PhysicalResourceId'],
            'resource_type': drift['ResourceType'],
            'drift_status': drift['StackResourceDrift'],
            'severity': severity,
            'differences': relevant_diffs,
            'timestamp': datetime.utcnow().isoformat()
        })

    return sorted(results, key=lambda r: severity_rank(r['severity']), reverse=True)

def severity_rank(s):
    return {'CRITICAL': 0, 'HIGH': 1, 'MEDIUM': 2, 'LOW': 3, 'SUPPRESSED': 4, 'NONE': 5}.get(s, 9)
```

## Remediation strategies by drift type

### Strategy 1: CloudFormation change-set re-apply

Use when: the drift is unintentional and the stack template is the
correct desired state.

```python
def remediate_via_changeset(stack_name):
    """Create and execute a change-set to revert drift."""
    change_set_name = f"drift-remediation-{int(datetime.utcnow().timestamp())}"

    # Create change-set using previous template
    cs = cfn.create_change_set(
        StackName=stack_name,
        ChangeSetName=change_set_name,
        ChangeSetType='UPDATE',
        UsePreviousTemplate=True,
        Capabilities=['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
    )

    # Wait for change-set to be reviewable
    waiter = cfn.get_waiter('change_set_create_complete')
    waiter.wait(StackName=stack_name, ChangeSetName=change_set_name)

    # Review changes
    changes = cfn.describe_change_set(StackName=stack_name, ChangeSetName=change_set_name)

    # Check for replacements (downtime risk)
    has_replacements = any(
        action == 'Replace'
        for change in changes.get('Changes', [])
        for action in [change.get('ResourceChange', {}).get('Action')]
    )

    if has_replacements:
        # Do NOT auto-execute — require human approval
        return {'action': 'changeset-created', 'requires_approval': True,
               'reason': 'contains resource replacements (downtime risk)'}

    # Execute (non-replacement changes only)
    cfn.execute_change_set(StackName=stack_name, ChangeSetName=change_set_name)
    return {'action': 'changeset-executed', 'requires_approval': False}
```

### Strategy 2: Surgical Lambda fix

Use when: only specific properties need to be reverted (not a full
template re-apply).

```python
def remediate_surgical(drift_result):
    """Revert specific drifted properties via direct API calls."""
    for drift in drift_result:
        if drift['resource_type'] == 'AWS::EC2::SecurityGroup':
            revert_sg_changes(drift)
        elif drift['resource_type'] == 'AWS::IAM::Role':
            revert_iam_role_changes(drift)
        elif drift['resource_type'] == 'AWS::S3::Bucket':
            revert_s3_bucket_changes(drift)
```

### Strategy 3: Template update (for intentional drift)

Use when: the drift represents a desired change that should be
persisted to the template.

```python
def update_template_to_match(stack_name, drift_results):
    """Update the CFN template to match the actual (drifted) state.
    Use when drift is intentional and should be the new baseline."""
    # This requires generating a new template from the current state
    # or manually updating the template to match the drift
    # This is typically a manual step with human review
    pass
```

## SSM Automation document — full remediation runbook

```yaml
---
schemaVersion: '0.3'
assumeRole: '{{ AutomationAssumeRole }}'
description: 'Detect and remediate CloudFormation stack drift'
parameters:
  StackName:
    type: String
    description: 'The CloudFormation stack to check and remediate'
  AutoRemediate:
    type: Boolean
    default: false
    description: 'If true, execute change-set without approval. If false, require approval.'
  AutomationAssumeRole:
    type: String
mainSteps:
  - name: DetectDrift
    action: aws:executeAwsApi
    inputs:
      Service: cloudformation
      Api: DetectStackDrift
      StackName: '{{ StackName }}'
    outputs:
      - Name: DetectionId
        Selector: '$.StackDriftDetectionId'
        Type: String
  - name: WaitForDetection
    action: aws:waitFor
    inputs:
      Service: cloudformation
      Api: DescribeStackDriftDetectionStatus
      StackDriftDetectionId: '{{ DetectDrift.DetectionId }}'
      $.DetectionStatus: DETECTION_COMPLETE
  - name: CheckDriftStatus
    action: aws:executeAwsApi
    inputs:
      Service: cloudformation
      Api: DescribeStackResourceDrifts
      StackName: '{{ StackName }}'
      StackResourceDriftStatusFilters: ['MODIFIED']
    outputs:
      - Name: DriftedResources
        Selector: '$.StackResourceDrifts'
        Type: MapList
  - name: HasDrift
    action: aws:branch
    inputs:
      Choices:
        - NextStep: CreateChangeSet
          Variable: '{{ CheckDriftStatus.DriftedResources }}'
          Operation: NotEquals
          Value: []
      Default: NoDriftComplete
  - name: CreateChangeSet
    action: aws:executeAwsApi
    inputs:
      Service: cloudformation
      Api: CreateChangeSet
      StackName: '{{ StackName }}'
      ChangeSetName: 'drift-remediation-{{ global:TIMESTAMP }}'
      ChangeSetType: UPDATE
      UsePreviousTemplate: true
      Capabilities: ['CAPABILITY_IAM', 'CAPABILITY_NAMED_IAM']
    outputs:
      - Name: ChangeSetId
        Selector: '$.Id'
        Type: String
  - name: WaitForChangeSet
    action: aws:waitFor
    inputs:
      Service: cloudformation
      Api: DescribeChangeSet
      ChangeSetName: '{{ CreateChangeSet.ChangeSetId }}'
      StackName: '{{ StackName }}'
      $.Status: CREATE_COMPLETE
  - name: CheckAutoRemediate
    action: aws:branch
    inputs:
      Choices:
        - NextStep: ExecuteChangeSet
          Variable: '{{ AutoRemediate }}'
          Operation: Equals
          Value: true
      Default: ApproveRemediation
  - name: ApproveRemediation
    action: aws:approve
    inputs:
      NotificationArn: 'arn:aws:sns:us-east-1:111111111111:drift-approval'
      Message: 'Approve drift remediation for {{ StackName }}? Review the change-set first.'
      MinRequiredApprovals: 1
  - name: ExecuteChangeSet
    action: aws:executeAwsApi
    inputs:
      Service: cloudformation
      Api: ExecuteChangeSet
      ChangeSetName: '{{ CreateChangeSet.ChangeSetId }}'
      StackName: '{{ StackName }}'
    isCritical: true
    onFailure: abort
  - name: NoDriftComplete
    action: aws:sleep
    inputs:
      Duration: PT0S
```

## Common remediation failures

| Failure | Root cause | Fix |
|---|---|---|
| `InsufficientCapabilities` | Change-set requires CAPABILITY_NAMED_IAM | Add capabilities to create-change-set call |
| `ResourceNotReady` on waiter | Change-set creation still in progress | Increase waiter delay or timeout |
| Change-set contains replacements | An immutable property was drifted | Do NOT auto-execute — require human approval |
| `ValidationError: No updates` | No actual changes detected (false drift) | Ignore — the drift detection was a false positive |
| SSM `TIMEOUT` on ExecuteChangeSet | Stack update takes longer than step timeout | Increase ExecutionTimeout on the SSM document |
| `ACCESS_DENIED` on CFN APIs | Automation role missing cloudformation permissions | Add `cloudformation:CreateChangeSet`, `ExecuteChangeSet` to role |

## Rollback after remediation failure

If the change-set execution fails mid-stack-update, CloudFormation rolls
back automatically. But if the rollback itself fails, the stack enters
`UPDATE_ROLLBACK_FAILED` status. Recovery:

```bash
# Continue rollback (skip resources that failed to roll back)
aws cloudformation continue-update-rollback \
  --stack-name <stack-name> \
  --resources-to-skip <logical-resource-id>
```

Always test remediation in a non-production account first. A failed
remediation that leaves a stack in `UPDATE_ROLLBACK_FAILED` is worse
than the original drift.
