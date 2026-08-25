# Worked Examples — Security Hub Remediation Automator

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

### Step 6: Build the Lambda remediation dispatcher

```python
import boto3
ssm = boto3.client('ssm')
hub = boto3.client('securityhub')
sns = boto3.client('sns')

RUNBOOK_MAP = {
    'S3.1':  {'runbook': 'AWS-DisableS3BucketPublicAccess', 'param': 'S3BucketName'},
    'S3.4':  {'runbook': 'AWS-EnableS3BucketEncryption', 'param': 'S3BucketName'},
    'IAM.3': {'runbook': 'AWS-IAMRevokeUnusedAccessKey', 'param': 'UserName'},
}

def lambda_handler(event, context):
    finding = event['finding']
    fid = finding['Id']
    parn = finding['ProductArn']
    resource = finding['Resources'][0]
    ctrl = finding.get('GeneratorId', '').split('/')[-1]

    if ctrl in RUNBOOK_MAP:
        m = RUNBOOK_MAP[ctrl]
        param_val = resource['Id'].split(':')[-1].split('/')[-1]
        try:
            resp = ssm.start_automation_execution(
                DocumentName=m['runbook'],
                Parameters={m['param']: [param_val],
                    'AutomationAssumeRole': ['arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole']}
            )
            hub.batch_update_findings(
                FindingIdentifiers=[{'Id': fid, 'ProductArn': parn}],
                Workflow={'Status': 'NOTIFIED'},
                Note={'Text': f'Remediation executed: {resp["AutomationExecutionId"]}', 'UpdatedBy': 'dispatcher'})
            return {'status': 'remediated'}
        except Exception as e:
            hub.batch_update_findings(
                FindingIdentifiers=[{'Id': fid, 'ProductArn': parn}],
                Note={'Text': f'Remediation FAILED: {e}', 'UpdatedBy': 'dispatcher'})
            raise
    else:
        sns.publish(TopicArn='arn:aws:sns:us-east-1:111111111111:security-alerts',
            Message=f'No auto-remediation for {ctrl}. Manual triage.\nFinding: {fid}')
        hub.batch_update_findings(
            FindingIdentifiers=[{'Id': fid, 'ProductArn': parn}],
            Workflow={'Status': 'NOTIFIED'},
            Note={'Text': f'No runbook for {ctrl}. Notified.', 'UpdatedBy': 'dispatcher'})
        return {'status': 'notified'}
```


### Literal output labels

Every remediation design MUST emit exactly one block per finding type using
the labels `FINDING_ID:`, `FINDING_TYPE:`, `VERDICT:`, `CHECKLIST:`, `GAP:`,
and `TEMPLATE:`. Do NOT preface with prose.

```text
FINDING_ID: <finding Id — arn:aws:securityhub:us-east-1:ACCT:subscription/...>
FINDING_TYPE: <Security Hub finding type>
STANDARD: <CIS | PCI | FSBP | Custom | N/A>
VERDICT: AUTOMATION_DEPLOYED | REVIEW_REQUIRED
CHECKLIST:
  [✓|✗] Severity route: CRITICAL_AUTO | HIGH_AUTO | MEDIUM_NOTIFY | LOW_NOTIFY
  [✓|✗] EventBridge rule: <rule name + pattern>
  [✓|✗] SSM runbook / Lambda fixer: <name | ARN | NONE>
  [✓|✗] batch-update-findings: wired
  [✓|✗] SQS DLQ: <ARN>
  [✓|✗] Suppression: <NONE | rule+expiration>
  [✓|✗] Insight: <ARN | TBD>
  [✓|✗] Safety gate: <validated>
GAP: <specific missing piece or None>
TEMPLATE: <CLI snippet or IaC>
```


### Worked example — REVIEW_REQUIRED, no runbook mapped

```text
FINDING_ID: arn:aws:securityhub:us-east-1:111111111111:subscription/custom/lambda-cred-exposure/finding/02b34567
FINDING_TYPE: Software and Configuration Checks/Custom/ExposedCredentialsInLambda
STANDARD: Custom
VERDICT: REVIEW_REQUIRED
CHECKLIST:
  [✗] Severity route: HIGH_AUTO — no runbook available
  [✓] EventBridge rule: securityhub-high-auto-remediation (configured)
  [✗] SSM runbook / Lambda fixer: NONE — no managed runbook for Lambda env-var credential exposure
  [✓] batch-update-findings: NOTIFIED (SNS to security channel)
  [✓] SQS DLQ: arn:aws:sqs:us-east-1:111111111111:securityhub-remediation-dlq
  [✓] Suppression: NONE
  [✗] Insight: TBD — create insight for tracking
  [✗] Safety gate: not yet built
GAP: No managed runbook exists. Build a custom Lambda that (1) reads the finding, (2) rotates the credential via Secrets Manager, (3) updates the environment variable, (4) calls batch-update-findings RESOLVED. Then wire the EventBridge rule.
TEMPLATE: (custom Lambda — see Step 6 pattern in skill body)
```
