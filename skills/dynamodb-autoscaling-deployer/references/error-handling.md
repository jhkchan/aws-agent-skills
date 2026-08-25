# Error Handling (load on demand) — DynamoDB Auto-Scaling Deployer

API error remediation and IAM role mistakes, moved verbatim from SKILL.md.


---

## Step 2 — custom auto-scaling roles and role-confusion mistakes (moved from SKILL.md)

**For custom roles (advanced):** if you need a custom role instead
of the service-linked role, the trust policy must allow
`application-autoscaling.amazonaws.com` and the permission policy
must include `dynamodb:UpdateTable`, `dynamodb:DescribeTable`, and
`cloudwatch:PutMetricAlarm`, `cloudwatch:DescribeAlarms`,
`cloudwatch:DeleteAlarms` (target tracking creates CloudWatch
alarms internally).

**Common mistake:** using the DynamoDB service role instead of the
Application Auto Scaling role. The roles are different — DynamoDB
has `AWSServiceRoleForDynamoDBBackup`, `AWSServiceRoleForDynamoDB`,
etc. Auto-scaling specifically needs
`AWSServiceRoleForApplicationAutoScaling_DynamoDBFeedback`.

## Error handling (moved from SKILL.md)


### `ValidationException` on register-scalable-target
- Table is in on-demand mode. Switch to PROVISIONED:
  `aws dynamodb update-table --table-name <name> --billing-mode PROVISIONED`.
- MinCapacity > current provisioned capacity. Lower Min or raise current throughput.

### `AccessDenied` on register-scalable-target
- The application auto-scaling service-linked role is missing.
  Create it:
  `aws iam create-service-linked-role --aws-service-name dynamodb.application-autoscaling.amazonaws.com`.

### `LimitExceededException` on register-scalable-target
- MaxCapacity exceeds the account-level DynamoDB throughput limit.
  Request a limit increase via AWS Support, or lower MaxCapacity.

### Scaling policy not adjusting capacity
- Verify the scalable target is registered:
  `aws application-autoscaling describe-scalable-targets`.
- Verify the policy is attached:
  `aws application-autoscaling describe-scaling-policies`.
- Check CloudWatch for `DynamoDBReadCapacityUtilization` /
  `DynamoDBWriteCapacityUtilization` to confirm the metric is
  reporting.
- If the table was switched to on-demand and back, all policies
  were detached — re-register targets and re-create policies.

### GSI throttling despite table auto-scaling
- GSI scaling was not configured. Register scalable targets for
  the GSI:
  `--resource-id table/<table-name>/index/<gsi-name> --scalable-dimension dynamodb:index:ReadCapacityUnits`.
- Create target tracking policies for each GSI dimension.