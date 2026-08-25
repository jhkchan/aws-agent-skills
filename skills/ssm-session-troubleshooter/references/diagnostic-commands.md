# Diagnostic Commands — ssm-session-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Pre-flight probes (instance and session state)

```bash
# 1. Instance information (AgentVersion, PingStatus, PlatformName,
#    RegistrationDate, LastPingDateTime, AssociationStatus, IamRole)
aws ssm describe-instance-information --output json

aws ssm describe-instance-properties --instance-id <i-id> --output json

# 2. Recent sessions (Status, Output, StartDate, EndDate)
aws ssm describe-sessions --state History \
  --instance-id <i-id> --output json

# 3. Session document (the SSM-SessionManagerRunShell default or custom)
aws ssm get-document --name SSM-SessionManagerRunShell --output json

# 4. Instance role — simulate the session permissions
aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].IamInstanceProfile.Arn' --output text

aws iam simulate-principal-policy \
  --policy-source-arn "<instance-role-arn>" \
  --action-names ssm:StartSession ssm:UpdateInstanceInformation \
    ssmmessages:CreateControlChannel ssmmessages:CreateDataChannel \
    ssmmessages:OpenControlChannel ssmmessages:OpenDataChannel \
    s3:PutObject logs:CreateLogStream \
  --output json

# 5. VPC endpoints for the instance's VPC (ssm, ec2messages, ssmmessages)
VPC_ID=$(aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].VpcId' --output text)
aws ec2 describe-vpc-endpoints --filters Name=vpc-id,Values=$VPC_ID \
  --query 'VpcEndpoints[].ServiceName' --output json

# 6. Security group egress (must allow 443 to the endpoints or service)
SG_ID=$(aws ec2 describe-instances --instance-ids <i-id> \
  --query 'Reservations[0].Instances[0].SecurityGroups[0].GroupId' --output text)
aws ec2 describe-security-groups --group-ids $SG_ID --output json

# 7. SSM agent log (CloudWatch Logs if configured, or fetch via SSM Run Command)
aws logs filter-log-events \
  --log-group-name /aws/ssm/<i-id>/amazon-ssm-agent \
  --start-time $(date -d '-30 minutes' +%s)000 \
  --filter-pattern '"SessionManager" OR "ssmmessages" OR "AccessDenied"' \
  --output json

# 8. AWS Health (regional SSM events, scheduled maintenance)
aws health describe-events --filter eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

## Step 2 — caller-role probe

```bash
aws iam simulate-principal-policy \
  --policy-source-arn "<caller-role-arn>" \
  --action-names ssm:StartSession ssm:TerminateSession \
  --resource-arns "arn:aws:ssm:<region>:<account>:instance/<i-id>" \
    "arn:aws:ssm:<region>:<account>:document/SSM-SessionManagerRunShell" \
  --output json
```

## Step 7 — port-forwarding probe

```bash
aws ssm start-session \
  --document-name AWS-StartPortForwardingSession \
  --target <i-id> \
  --parameters '{"portNumber":["22"], "hostName":["10.0.1.50"]}'
```

## Step 9 — audit-log / S3 output probe

```bash
aws ssm get-document --name SSM-SessionManagerRunShell --output json | \
  jq '.DocumentContent.inputs.s3BucketName, .DocumentContent.inputs.s3KeyPrefix'
aws s3api get-bucket-policy --bucket <session-output-bucket> --output json | jq '.'
aws s3api head-bucket --bucket <session-output-bucket>
```

## Step 10 — CloudWatch Logs delivery probe

```bash
aws ssm get-document --name SSM-SessionManagerRunShell --output json | \
  jq '.DocumentContent.inputs.cloudWatchLogGroupName, .DocumentContent.inputs.cloudWatchStreamingEnabled'
aws logs describe-log-groups --log-group-name-prefix <prefix> --output json
aws iam simulate-principal-policy --policy-source-arn "<role-arn>" \
  --action-names logs:CreateLogStream logs:PutLogEvents --output json
```

## Step 11 — patch-baseline association probe

```bash
aws ssm describe-instance-associations-status --instance-id <i-id> --output json
aws ssm describe-association --association-id <assoc-id> --output json
```
