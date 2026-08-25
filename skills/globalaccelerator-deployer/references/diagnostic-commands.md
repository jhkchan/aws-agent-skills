# Diagnostic Commands — Global Accelerator Deployer

Diagnostic and pre-flight command listings moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Live-account pre-flight checks (moved from SKILL.md)

**Live-account pre-flight checks (skip if doing offline architecture plan):**

1. Verify IAM permissions: `globalaccelerator:CreateAccelerator`,
   `CreateListener`, `CreateEndpointGroup`, `AddEndpoints`,
   `UpdateEndpointGroup`, and (for BYOIP) `ec2:AdvertiseByoipCidr`,
   `ec2:ProvisionByoipCidr`, `route53:AssociateVpcWithHostedZone`.
2. Verify endpoint ARNs resolve and region matches its endpoint group
   region (cross-region endpoints within a group are NOT supported):
   - ALB/NLB: `aws elbv2 describe-load-balancers --load-balancer-arns <arn>` returns `active`.
   - EC2: `aws ec2 describe-instances --instance-ids <id>` returns `running`.
   - EIP: `aws ec2 describe-addresses --allocation-ids <id>` returns `allocated`.
3. For BYOIP, verify the CIDR is `PROVISIONED` in Route 53:
   `aws ec2 describe-byoip-cidrs` — only `PROVISIONED` can be advertised.
4. For cross-account endpoints, verify the RAM resource share is
   `ACTIVE` and accepted by the consumer account.
5. For flow logs to CloudWatch, verify the log group exists and the
   `AWSServiceRoleForGlobalAccelerator` service-linked role has
   `logs:CreateLogStream` and `logs:PutLogEvents`.
6. For flow logs to S3, verify the bucket policy grants `s3:PutObject`
   to `flowlogs.globalaccelerator.amazonaws.com`.

