# SSM Session Manager VPC Endpoint & IAM Reference Guide

Supplementary reference for the SSM Session Troubleshooter skill.
Loaded on-demand when a diagnostic needs the three-endpoint matrix,
the instance-role permission map, the caller-role permission map,
or the agent version support matrix.

## Three VPC endpoints for private-subnet SSM

Session Manager in a VPC without internet egress (no IGW, no NAT)
requires THREE interface VPC endpoints. Each carries different
traffic; missing any one produces distinct symptoms.

| Endpoint service name | Type | Traffic | Missing → symptom |
|---|---|---|---|
| `com.amazonaws.<region>.ssm` | Interface | Control plane: `UpdateInstanceInformation`, `StartSession` API | Instance never registers; absent from `describe-instance-information` |
| `com.amazonaws.<region>.ec2messages` | Interface | Run Command and Association delivery | Instance Online but Run Command fails; associations stuck |
| `com.amazonaws.<region>.ssmmessages` | Interface | Session data channel (terminal stream) | Instance Online; session starts then times out within 10s |

### Creating the three endpoints

```bash
VPC_ID=vpc-priv
SUBNET_ID=subnet-priv-a
SG_ID=sg-ssm-endpoint

for svc in ssm ec2messages ssmmessages; do
  aws ec2 create-vpc-endpoint \
    --vpc-id $VPC_ID \
    --vpc-endpoint-type Interface \
    --service-name com.amazonaws.us-east-1.$svc \
    --subnet-ids $SUBNET_ID \
    --security-group-ids $SG_ID \
    --private-dns-enabled --output json
done
```

### Endpoint security group

The endpoint's security group must allow 443 inbound from the
instance subnet CIDR (or the instance SG). Without inbound 443, the
endpoint exists but is unreachable.

```json
{
  "IpPermissions": [{
    "FromPort": 443,
    "ToPort": 443,
    "IpProtocol": "tcp",
    "IpRanges": [{"CidrIp": "10.0.1.0/24"}]
  }]
}
```

### Private DNS

`PrivateDnsEnabled: true` is required for the instance to resolve
`ssm.<region>.amazonaws.com`, `ec2messages.<region>.amazonaws.com`,
and `ssmmessages.<region>.amazonaws.com` to the endpoint's private
IPs. Without private DNS, the instance resolves the public IPs and
the session fails in a no-egress VPC.

### S3 Gateway endpoint (for agent self-update)

The agent downloads updates from an S3 bucket in the same Region.
Add a Gateway endpoint (free, automatic) so the agent can self-
update without NAT:

```bash
aws ec2 create-vpc-endpoint --vpc-id $VPC_ID \
  --service-name com.amazonaws.us-east-1.s3 \
  --route-table-ids <rtb-id> --output json
```

Without this, a locked-down private instance stays on the agent
version it was launched with.

## Instance role permissions (AmazonSSMManagedInstanceCore)

The instance role (attached via the instance profile) needs the
following actions for Session Manager. `AmazonSSMManagedInstanceCore`
includes all of them; a custom role must grant each explicitly.

### Core session actions

| Action | Resource | Purpose |
|---|---|---|
| `ssm:UpdateInstanceInformation` | `*` | Heartbeat / registration |
| `ssmmessages:CreateControlChannel` | `*` | Session control channel create |
| `ssmmessages:CreateDataChannel` | `*` | Session data channel create |
| `ssmmessages:OpenControlChannel` | `*` | Session control channel open |
| `ssmmessages:OpenDataChannel` | `*` | Session data channel open |
| `ec2messages:GetMessages` | `*` | Run Command polling |

### Session output actions (added if audit/recording configured)

| Action | Resource | Purpose |
|---|---|---|
| `s3:PutObject` | `arn:aws:s3:::<session-bucket>/*` | Audit JSON write |
| `logs:CreateLogStream` | `arn:aws:logs:<region>:<account>:log-group:<group>*` | CloudWatch stream |
| `logs:PutLogEvents` | `arn:aws:logs:<region>:<account>:log-group:<group>*` | CloudWatch events |
| `kms:GenerateDataKey` | `<kms-key-arn>` | SSE-KMS session encryption |

### Deprecated policy

`AmazonEC2RoleforSSM` is deprecated and does NOT include all
`ssmmessages:*` actions. Instances on this policy appear Online but
fail to open sessions. Switch to `AmazonSSMManagedInstanceCore`.

## Caller role permissions

The human or service invoking `start-session` needs:

| Action | Resource | Purpose |
|---|---|---|
| `ssm:StartSession` | `arn:aws:ssm:<region>:<account>:instance/<i-id>` and `arn:aws:ssm:<region>:<account>:document/<doc-name>` | Start a session |
| `ssm:TerminateSession` | `arn:aws:ssm:<region>:<account>:session/<session-id>` | Terminate own sessions |
| `ssm:ResumeSession` | `arn:aws:ssm:<region>:<account>:session/<session-id>` | Reconnect to a session |

A common pattern is to scope `ssm:StartSession` to specific
documents and instances via resource ARNs to prevent access to
arbitrary targets.

## Agent version support matrix

| Agent version | Session Manager | Port forwarding | macOS | Windows |
|---|---|---|---|---|
| < 2.3.68.0 | Not supported | Not supported | Not supported | Not supported |
| 2.3.68.0 – 2.3.x | Supported | Not supported | Not supported | Supported |
| 3.0.196+ | Supported | Supported | Not supported | Supported |
| 3.1.x+ | Supported | Supported | Supported | Supported |

The agent self-updates if the instance can reach
`s3.<region>.amazonaws.com` (or has an S3 VPC endpoint). Locked-
down instances may stay on the launch agent version indefinitely.

## Common failure signatures

| Error | Most common cause |
|---|---|
| Instance absent from `describe-instance-information` | Agent stopped; role missing `AmazonSSMManagedInstanceCore`; no `ssm` endpoint |
| `ChannelClosedException` / session times out | Missing `ssmmessages` endpoint; missing `ssmmessages:OpenDataChannel` on role |
| `AccessDeniedException` on `start-session` CLI | Caller missing `ssm:StartSession` |
| `NotSupported` on port forwarding | Agent below 3.0.196 |
| Session opens, closes immediately | Shell profile error (`.bashrc` with `exit`) |
| Sessions work, no S3 output | Document `s3BucketName` empty |
| Sessions work, no CloudWatch Logs | Document `cloudWatchLogGroupName` empty or `logs:PutLogEvents` denied |
