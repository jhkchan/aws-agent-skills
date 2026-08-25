# Diagnostic Commands — GuardDuty Finding Investigator

Diagnostic, pre-flight, and per-step probe command listings, moved verbatim from SKILL.md. Load on demand.

## Account-wide pre-flight commands

```bash
# Detector IDs and the finding itself (preferred path)
aws guardduty list-detectors --output json
aws guardduty get-findings --detector-id <detector-id> \
  --finding-ids <finding-id> --output json

# Finding statistics, trusted IPs, and enabled features
aws guardduty get-findings-statistics --detector-id <detector-id> \
  --finding-statistics-types COUNT_BY_SEVERITY COUNT_BY_TYPE --output json
aws guardduty list-ip-sets --detector-id <detector-id> --output json
aws guardduty list-threat-intel-sets --detector-id <detector-id> --output json
aws guardduty list-features --detector-id <detector-id> --output json

# CloudTrail lookup for the finding's actor and time window
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>

# VPC Flow Log location (log group or S3) for the resource's VPC
aws ec2 describe-flow-logs --filter Name=resource-id,Values=<vpc-id> --output json

# AWS Health (regional events for GuardDuty)
aws health describe-events \
  --filter services=GUARDDUTY,eventStatusCodes=OPEN,UPCOMING \
  --region us-east-1 --output json
```

## Step 2a: Recon — port probe commands (`Recon:EC2/PortProbe`, `Recon:IAMUser/PortProbe`)

```bash
# Identify the probing source from the finding
jq '.service.action.portProbeAction.remoteIpDetails' finding.json
# ipAddressV4, organization {asn, org}, location {country, city}

# Compare against the trusted IP list
aws guardduty list-ip-sets --detector-id <detector-id> --output json
aws guardduty get-ip-set --detector-id <detector-id> \
  --ip-set-id <ip-set-id> --output json

# Check CloudTrail for the actor behind the probe (IAM findings only)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ListBuckets \
  --start-time <finding-utc-minus-30m> --end-time <finding-utc-plus-30m>
```

## Step 2b: Recon — IAM permission discovery commands (`Recon:IAMUser/UserPermissions`)

```bash
# CloudTrail burst pattern — List* / Get* calls
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=<iam-user> \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>
# Look for: ListBuckets, GetCallerIdentity, ListRoles, ListUsers bursts

# Access key last used (is the key still active?)
aws iam get-access-key-last-used --access-key-id <AKIA...>
```

## Step 3a: UnauthorizedAccess — ConsoleLogin commands

```bash
# CloudTrail ConsoleLogin event
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ConsoleLogin \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>
# Capture: sourceIPAddress, userIdentity.arn, additionalEventData.MFAUsed
aws iam get-login-profile --user-name <iam-user>
```

## Step 3b: UnauthorizedAccess — SSH/RDP brute force commands

```bash
# VPC Flow Logs — concentration of dstport=22 from many source IPs
aws logs start-query --log-group-name <flow-log-group> \
  --start-time <epc-finding-utc-minus-30m> --end-time <epc-finding-utc-plus-30m> \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort
    | filter dstPort=22 and action=ACCEPT
    | stats count() by srcAddr | sort count desc | limit 20'

# Check the EC2 instance's security group — is port 22 open to 0.0.0.0/0?
aws ec2 describe-security-groups \
  --group-ids $(aws ec2 describe-instances --instance-ids <i-id> \
    --output json | jq -r '.Reservations[0].Instances[0].SecurityGroups[].GroupId') \
  --output json | jq '.SecurityGroups[].IpPermissions[] | select(.FromPort==22)'
```

## Step 4: Backdoor:EC2 — C&C / spambot commands

```bash
# Extract the remote IP from the finding
jq '.service.action.networkConnectionAction.remoteIpDetails' finding.json

# VPC Flow Logs — sustained outbound to the suspicious IP
aws logs start-query --log-group-name <flow-log-group> \
  --start-time <epc-finding-utc-minus-1h> --end-time <epc-finding-utc-plus-1h> \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort, bytes
    | filter (srcAddr="<instance-private-ip>" and dstAddr="<remote-ip>")
    | sort @timestamp desc | limit 100'

# Route 53 Resolver logs (DNS-based C&C)
aws logs start-query --log-group-name <resolver-log-group> \
  --query-string 'fields @timestamp, srcaddr, query_name
    | filter srcaddr="<instance-private-ip>" | sort @timestamp desc'
```

## Step 5: CryptoCurrency:EC2 — crypto mining commands

```bash
# DNS variant — mining pool domain lookup
jq '.service.action.dnsRequestAction.domain' finding.json

# VPC Flow Logs — outbound to mining pool CIDRs (ports 3333, 4444, 8888, 14444)
aws logs start-query --log-group-name <flow-log-group> \
  --query-string 'fields @timestamp, srcAddr, dstAddr, dstPort, bytes
    | filter srcAddr="<instance-private-ip>" and
      (dstPort=3333 or dstPort=4444 or dstPort=8888 or dstPort=14444)
    | stats sum(bytes) by dstAddr'

# CloudWatch — CPU spike around the finding time
aws cloudwatch get-metric-statistics --namespace AWS/EC2 \
  --metric-name CPUUtilization --dimensions Name=InstanceId,Value=<i-id> \
  --start-time <finding-utc-minus-1h> --end-time <finding-utc-plus-1h> \
  --period 300 --statistics Average,Maximum --output json
```

## Step 6: Persistence:IAMUser — anomalous IAM change commands

```bash
# CloudTrail — CreateUser, CreateAccessKey, AttachRolePolicy around the finding
for EV in CreateUser CreateAccessKey AttachUserPolicy; do
  aws cloudtrail lookup-events \
    --lookup-attributes AttributeKey=EventName,AttributeValue=$EV \
    --start-time <finding-utc-minus-30m> --end-time <finding-utc-plus-30m>
done
```

## Step 7: Policy:IAMUser — suspicious policy grant commands

```bash
# S3BucketAnonymousGranted — confirm the ACL change
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutBucketAcl \
  --start-time <finding-utc-minus-30m> --end-time <finding-utc-plus-30m>
aws s3api get-bucket-acl --bucket <bucket>

# RootCredentialUsage — root API call source
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=root \
  --start-time <finding-utc-minus-15m> --end-time <finding-utc-plus-15m>
```

## Step 8: Exfiltration — data-leaving-account commands

```bash
# S3 variant — anomalous GetObject volume (needs CloudTrail data events)
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time <finding-utc-minus-1h> --end-time <finding-utc-plus-1h>

# VPC Flow Logs — anomalous outbound volume
aws logs start-query --log-group-name <flow-log-group> \
  --query-string 'fields srcAddr, dstAddr, bytes
    | filter srcAddr="<instance-private-ip>"
    | stats sum(bytes) as totalBytes by dstAddr | sort totalBytes desc | limit 20'

# S3 access logs (for S3 exfil)
aws s3api get-bucket-logging --bucket <bucket>
```

## Step 9: Runtime Monitoring findings commands

```bash
# Inspect the runtime evidence from the finding itself
jq '.service.runtimeData' finding.json
# processDetails: name, path, pid, user, cmdline, parent
# networkConnection: direction, local, remote
# moduleInformation: loaded libraries

# CloudWatch Container Insights (ECS/EKS), EKS context, agent status
aws logs describe-log-groups --log-group-name-prefix /aws/ecs/containerinsights
jq '.resource.eksClusterDetails, .resource.containerDetails' finding.json
aws ssm describe-instance-information --filters Key=InstanceIds,Values=<i-id>
```

## Step 10: Malware Protection scan commands

```bash
aws malware-scan start-malware-scan \
  --resource-arn arn:aws:ec2:<region>:<acct>:snapshot/<snap-id>
aws malware-scan list-scans --filter-criteria '<json>' --output json
aws malware-scan get-scan --scan-id <scan-id> --output json
```

