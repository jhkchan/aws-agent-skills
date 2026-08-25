# Error Handling — ssm-session-troubleshooter

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

### For INSTANCE_NOT_REGISTERED — agent or role missing

```bash
# Attach the instance profile if missing
aws ec2 associate-iam-instance-profile \
  --instance-id <i-id> --iam-instance-profile Name=<profile-name>

# Ensure the role has AmazonSSMManagedInstanceCore
aws iam attach-role-policy --role-name <role-name> \
  --policy-arn arn:aws:iam::aws:policy/AmazonSSMManagedInstanceCore

# Start the agent on the instance (Linux)
sudo systemctl enable --now amazon-ssm-agent
```

### For IAM_PERMISSION_MISSING — role or caller missing ssm actions

Add the missing actions to the instance role (use
AmazonSSMManagedInstanceCore if the role is on the deprecated
policy) or to the caller's policy.

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name SsmSessionAccess \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["ssmmessages:CreateControlChannel",
                  "ssmmessages:CreateDataChannel",
                  "ssmmessages:OpenControlChannel",
                  "ssmmessages:OpenDataChannel"],
      "Resource": "*"
    }]
  }'
```

Verify with `simulate-principal-policy`.

### For VPC_ENDPOINT_MISSING — add the missing endpoint

```bash
aws ec2 create-vpc-endpoint --vpc-id <vpc-id> \
  --service-name com.amazonaws.<region>.ssmmessages \
  --subnet-ids <private-subnet-id> \
  --security-group-ids <sg-id> \
  --vpc-endpoint-type Interface --output json
```

Repeat for `ssm` and `ec2messages` if those are also missing.
Ensure the endpoint's security group allows 443 inbound from the
instance's subnet.

### For SESSION_CONNECTION_TIMEOUT — network path

Add the SG egress rule for 443 to the VPC endpoint CIDRs or service
ranges. Enable private DNS on the VPC endpoint if disabled.

### For AGENT_OUTDATED — update the agent

On the instance, force an update or install the latest agent:

```bash
sudo yum update -y amazon-ssm-agent    # Amazon Linux 2 / 2023
sudo snap refresh amazon-ssm-agent     # Ubuntu 16.04+
brew upgrade amazon-ssm-agent          # macOS
```

For a private subnet without internet, add an S3 VPC endpoint so
the agent can self-update from the S3 package bucket.

### For SESSION_DOCUMENT_ERROR / SSM_DOCUMENT_ERROR

```bash
# Reset the default document
aws ssm update-document --name SSM-SessionManagerRunShell \
  --content file://default-session-document.json

# Or create a custom document
aws ssm create-document --name Custom-Session \
  --document-type Session \
  --content file://custom-session-document.json
```

### For PORT_FORWARDING_FAILURE

1. Verify the target host is reachable from the instance (not the
   caller): `ssh <i-id> ping <target-host>`.
2. Update the agent to >= 3.0.196.
3. Use `AWS-StartPortForwardingSessionToRemoteHost` for remote-host
   forwarding (different from local forwarding to the instance
   itself).

### For SHELL_PROFILE_ERROR

1. Inspect the shell profile on the instance:
   `cat ~/.bashrc ~/.bash_profile` (or the configured `shellProfile`).
2. Remove any `exit` / `logout` / syntax errors.
3. Update the document `shellProfile` to a tested script.

### For AUDIT_LOG_S3_MISSING / SESSION_RECORDING_S3

1. Set `s3BucketName` in the session document.
2. Update the bucket policy to grant the instance role `s3:PutObject`:
   ```bash
   aws s3api put-bucket-policy --bucket <session-bucket> --policy '{
     "Version": "2012-10-17",
     "Statement": [{
       "Effect": "Allow",
       "Principal": {"AWS": "arn:aws:iam::<account>:role/<instance-role>"},
       "Action": "s3:PutObject",
       "Resource": "arn:aws:s3:::<session-bucket>/*"
     }]
   }'
   ```
3. For SSE-KMS buckets, add `kms:GenerateDataKey` to the instance
   role on the KMS key ARN.

### For CLOUDWATCH_LOGS_MISSING

1. Set `cloudWatchLogGroupName` and `cloudWatchStreamingEnabled: true`
   in the document.
2. Add `logs:CreateLogStream`, `logs:PutLogEvents` to the instance
   role on the log group ARN.
3. For cross-account log groups, add a resource policy on the
   destination account granting `logs:PutLogEvents` to the SSM
   service or the source-account role.

### For PATCH_BASELINE_BLOCKING

Wait for the patch association to complete, or reschedule the
maintenance window outside session hours.
