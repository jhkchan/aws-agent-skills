# Incident Response Automator — diagnostic & response commands (moved verbatim from SKILL.md)

> Progressive-disclosure split: this content was moved verbatim from SKILL.md; nothing was rewritten.

## Live-account pre-flight checks (from Pre-flight: IR spec gate)

**Live-account pre-flight checks (skip for offline authoring):**
1. Verify GuardDuty detector is enabled: `aws guardduty list-detectors --query 'DetectorIds'`.
2. Verify Security Hub is enabled: `aws securityhub get-enabled-standards`.
3. Verify EventBridge and Step Functions IAM roles exist (or are in the
   template to be created).
4. Verify SSM Automation service-linked role exists:
   `aws iam get-role --role-name AWSServiceRoleForSSM`.
5. Verify Incident Manager is available in the region (not all regions
   support it — check the AWS regional services list).

### GuardDuty (preferred for resource-level threats) — CLI checks

```bash
# Verify detector is enabled
aws guardduty list-detectors --query 'DetectorIds'

# Create a filter for high-severity findings
aws guardduty create-filter \
  --detector-id <id> \
  --name high-severity-only \
  --finding-criteria '{"Criterion": {"severity": {"Gte": 7}}}'
```

## Response pattern 1 — isolate compromised resource

**EC2 instance quarantine via security group:**

```bash
# Pre-provision the quarantine SG (one-time per VPC)
QUARANTINE_SG=$(aws ec2 create-security-group \
  --group-name quarantine-sg \
  --description "Isolated instances under investigation - no inbound, no outbound" \
  --vpc-id <vpc-id> --query 'GroupId' --output text)

# Strip ALL inbound and outbound rules (deny-all)
aws ec2 revoke-security-group-ingress --group-id $QUARANTINE_SG --ip-permissions $(...)
aws ec2 revoke-security-group-egress --group-id $QUARANTINE_SG --ip-permissions [...]

# Add a single deny-all egress (SG default is allow-all-egress)
aws ec2 authorize-security-group-egress \
  --group-id $QUARANTINE_SG \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'

# Wait, the above ADDS allow-all. Revoke it instead:
aws ec2 revoke-security-group-egress --group-id $QUARANTINE_SG \
  --ip-permissions '[{"IpProtocol":"-1","IpRanges":[{"CidrIp":"0.0.0.0/0"}]}]'
# Now the SG has NO egress rules - effectively a deny-all.
```

**OR use the SSM managed document:**

```bash
aws ssm start-automation-execution \
  --document-name AWS-IsolateEC2Instance \
  --document-version 1 \
  --parameters "InstanceId=i-0abc12345,SubnetId=subnet-xxx"
```

`AWS-IsolateEC2Instance` moves the instance to a quarantine VPC subnet
where it can be investigated but cannot reach the internet or other
internal resources.

**IAM credential revocation:**

```bash
# Deactivate the access key
aws iam update-access-key \
  --user-name <user> \
  --access-key-id <AKIA...> \
  --status Inactive

# Revoke active sessions (forces re-auth, killing existing STS sessions)
aws iam put-user-policy \
  --user-name <user> \
  --policy-name RevokeSessions \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Deny",
      "Action": "*",
      "Resource": "*"
    }]
  }'

# OR use the SSM managed document (one-shot):
aws ssm start-automation-execution \
  --document-name AWS-RevokeSession \
  --parameters "RoleName=<role>"
```

**EKS pod isolation (2024-2025 — Runtime Monitoring):**

EKS pods cannot be "isolated via SG" directly. Use a network policy to
deny all egress from the compromised pod, or evict the pod and revert
the deployment. Calico or Cilium network policies provide the deny-all
mechanism.

## Response pattern 2 — forensic preservation

**EBS snapshot for disk forensics:**

```bash
# Snapshot ALL volumes attached to the instance (not just root)
VOLUME_IDS=$(aws ec2 describe-instances --instance-ids i-0abc12345 \
  --query 'Reservations[0].Instances[0].BlockDeviceMappings[*].Ebs.VolumeId' \
  --output text)

for VOL in $VOLUME_IDS; do
  aws ec2 create-snapshot \
    --volume-id $VOL \
    --description "Forensic snapshot $(date -u +%Y-%m-%dT%H:%M:%SZ) - $VOL" \
    --tag-specifications "ResourceType=snapshot,Tags=[{Key=IncidentId,Value=<id>},{Key=Preserve,Value=true}]"
done
```

**Memory capture via SSM Run Command (Linux):**

```bash
# Requires the SSM agent and a memory-capture utility (e.g., LiME)
aws ssm send-command \
  --document-name "AWS-RunShellScript" \
  --instance-ids i-0abc12345 \
  --parameters 'commands=["insmod lime.ko \"path=/tmp/mem.lime format=lime\"", "aws s3 cp /tmp/mem.lime s3://forensic-bucket/<incident-id>/"]' \
  --comment "Memory capture for incident <id>"
```

**Preserve CloudTrail / Lake data:**

```bash
# Export relevant CloudTrail events to S3 for the investigation window
aws cloudtrail lookup-events \
  --start-time 2026-08-01T00:00:00Z \
  --end-time 2026-08-05T00:00:00Z \
  --attribute-key EventName --attribute-value AssumeRole \
  --output json > /tmp/incident-events.json

# For long windows, use Athena on the CloudTrail S3 bucket or CloudTrail Lake.
```

## Response pattern 3 — containment (block attacker)

**Block source IP in WAF:**

```bash
# Add the attacker IP to an IP set
aws wafv2 update-ip-set \
  --ip-set-id <id> \
  --scope REGIONAL \
  --addresses "$(jq -r '.detail.service.action.remoteIpDetails.ipAddressV4' <event>)/32" \
  --lock-token <token>
```

**Block source IP in NACL (immediate, VPC-scoped):**

```bash
# Add a DENY rule for the source IP at the top of the NACL
aws ec2 create-network-acl-entry \
  --network-acl-id <acl-id> \
  --rule-number 10 \
  --protocol "-1" \
  --rule-action deny \
  --cidr-block <source-ip>/32 \
  --port-range From=0,To=65535
```

**Rotate exposed secrets:**

```bash
# Force immediate rotation
aws secretsmanager rotate-secret \
  --secret-id <arn> \
  --rotation-rule-type IMMEDIATE

# If rotation Lambda is broken, manually update the secret value
aws secretsmanager put-secret-value \
  --secret-id <arn> \
  --secret-string '<new-value>'
```

## Response pattern 4 — notification

**SNS -> Lambda -> Slack:**

```python
# Lambda subscribed to SNS, posts to Slack incoming webhook
import json, urllib.request, os

def lambda_handler(event, context):
    webhook = os.environ['SLACK_WEBHOOK_URL']  # from Parameter Store
    finding = json.loads(event['Records'][0]['Sns']['Message'])
    msg = {
        'text': f":rotating_light: *IR Alert* — {finding['title']}\n"
                f"Severity: {finding['severity']}\n"
                f"Resource: {finding['resource']}\n"
                f"Finding ID: {finding['id']}"
    }
    urllib.request.urlopen(
        urllib.request.Request(webhook, json.dumps(msg).encode(), {'Content-Type': 'application/json'})
    )
```

**EventBridge -> SNS for paging (e.g., PagerDuty via SNS webhook):**

```bash
# EventBridge rule -> SNS topic -> PagerDuty SNS integration
aws sns subscribe \
  --topic-arn <arn> \
  --protocol https \
  --notification-endpoint https://events.pagerduty.com/integration/.../enqueue
```

**Create Jira ticket via Lambda:**

Lambda calls Jira REST API with finding details. Store Jira API token in
Secrets Manager; never hardcode.

## Response pattern 5 — recovery

**Restore RDS from point-in-time:**

```bash
aws rds restore-db-instance-to-point-in-time \
  --source-db-instance-identifier <compromised-db> \
  --target-db-instance-identifier <compromised-db-recovered \
  --restore-time 2026-08-04T12:00:00Z \
  --no-deletion-protection
```

**Redeploy from clean AMI:**

```bash
# Launch a fresh instance from a known-good AMI (from the golden AMI pipeline)
aws ec2 run-instances \
  --image-id <clean-ami> \
  --instance-type <type> \
  --subnet-id <subnet> \
  --security-group-ids <prod-sg> \
  --tag-specifications "ResourceType=instance,Tags=[{Key=RestoredFrom,Value=<incident-id>}]"
```

**Verify integrity post-recovery:**

```bash
# Verify file hashes against known-good baseline
aws ssm send-command \
  --document-name AWS-RunShellScript \
  --instance-ids <restored-id> \
  --parameters 'commands=["sha256sum /usr/bin/* /opt/app/bin/* | diff - baseline.txt"]'
```

## Systems Manager Incident Manager — response plan and trigger

### Create a response plan

```bash
aws ssm-incidents create-response-plan \
  --name prod-ir-plan \
  --display-name "Production IR Response Plan" \
  --incident-template '{
    "title": "Production security incident",
    "impact": 5,
    "summary": "Triggered by GuardDuty severity >= 7",
    "notificationTargets": [{
      "snsTopicArn": "arn:aws:sns:us-east-1:111111111111:ir-incident"
    }]
  }' \
  --engagements arn:aws:ssm-contacts:us-east-1:111111111111:contact/oncall \
  --chat-channel '{"chatbotSns": ["arn:aws:sns:us-east-1:111111111111:slack-chatbot"]}' \
  --actions '[{
    "ssmAutomation": {
      "documentName": "AWS-IsolateEC2Instance",
      "roleArn": "arn:aws:iam::111111111111:role/IR-Automation"
    }
  }]'
```

### Trigger an incident

```bash
# Manual trigger from the console or CLI
aws ssm-incidents start-incident \
  --response-plan-arn arn:aws:ssm-incidents::111111111111:response-plan/prod-ir-plan \
  --title "EC2 malware detected by GuardDuty" \
  --impact 5
```

## Kill-switch Parameter Store pattern

### Kill-switch Parameter Store pattern

```bash
# Create the kill-switch parameter (default: enabled)
aws ssm put-parameter \
  --name /ir/kill-switch \
  --value "enabled" \
  --type String

# Disable the workflow in one command
aws ssm put-parameter \
  --name /ir/kill-switch \
  --value "disabled" \
  --type String \
  --overwrite

# Workflow checks this FIRST; if "disabled", exits without action.
```

## Audit checklist for every workflow

**Audit checklist for every workflow:**

- [ ] CloudTrail covers the account/region where the workflow runs.
- [ ] Step Functions execution history retention >= 90 days.
- [ ] SSM Automation outputs include the finding ID and incident ID.
- [ ] Every containment action includes a tag or annotation with the
      incident ID (`IncidentId=<id>`).
- [ ] Notification messages include the Step Functions execution ARN for
      traceability.
- [ ] Post-incident, an Athena query against CloudTrail can reconstruct
      the full action timeline.

## Pre-flight safety checks (run before any deploy)

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`cloudformation deploy`, `stepfunctions update-state-machine`,
  `events put-rule`, `ssm create-document`), the automator MUST emit:
  `CONFIRM: About to <action> for <workflow> in account <account>. This
  affects <consequence>. Proceed? (yes/no)` and wait for explicit `yes`.

- **Dry-run the EventBridge rule.** Before enabling the rule that
  triggers the workflow, run with the rule in `DISABLED` state, send a
  test event via `aws events put-events`, and verify the Step Functions
  execution starts. Then enable the rule for production findings.

- **Validate the kill-switch first.** Before wiring the EventBridge rule
  to a real detector, set `/ir/kill-switch` to "disabled" and verify a
  test finding does NOT trigger containment. Then flip to "enabled" and
  verify it does.

- **Capture the existing state.** Before deploying a workflow that
  modifies resources, snapshot the existing state:
  `aws ec2 describe-security-groups --group-ids <quarantine-sg>` and
  `aws guardduty list-detectors` to a backup file. If the workflow
  misbehaves, you have a rollback baseline.

- **Verify Slack/Teams webhook.** Send a test message to the configured
  webhook URL before relying on it for incident notifications. A
  misconfigured webhook URL silently drops messages.

- **Test in security-test account FIRST.** Run the full workflow end-to-
  end (trigger finding -> workflow runs -> resources contained) in a
  dedicated test account. Use AWS Factory or a non-prod account. Do not
  deploy to prod without a passing test run.

- **Verify incident ID propagation.** Every action, snapshot, SSM
  execution, and notification must include the incident ID. Verify by
  inspecting the Step Functions execution output and the S3 forensic
  bucket tags after a test run.
