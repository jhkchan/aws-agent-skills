# Diagnostic and Pre-flight Commands — Multi-Account Governance Automator

## Delegated administration commands (GuardDuty, Security Hub, Config)

```bash
# GuardDuty delegated admin
aws guardduty enable-organization-admin-account --admin-account-id <audit-id>

# Security Hub delegated admin
aws securityhub enable-organization-admin-account --admin-account-id <audit-id>

# Config aggregator (org source auto-discovers new members)
aws configservice put-configuration-aggregator \
  --configuration-aggregator-name OrgAggregator \
  --organization-aggregation-source \
    RoleArn=arn:aws:iam::<audit>:role/service-role/ConfigAggregatorRole,AllRegions=true
```

## AWS Config aggregator coverage verification

```bash
aws configservice describe-configuration-recorder-status \
  --configuration-recorder-names default
# IsRecording must be true; LastStatus must be SUCCESS
```

## CloudTrail organization trail creation

```bash
aws cloudtrail create-organization-trail \
  --name org-trail \
  --s3-bucket-name <log-archive-bucket> \
  --is-organization-trail \
  --include-global-service-events \
  --is-multi-region-trail \
  --enable-log-file-validation \
  --kms-key-id arn:aws:kms:us-east-1:<log-archive>:key/<key-id>
```

## Security Hub finding aggregator creation

```bash
aws securityhub create-finding-aggregator --region us-east-1
```

## IAM Identity Center permission set commands

```bash
aws sso-admin create-permission-set \
  --name AWSAdministratorAccess \
  --instance-arn <identity-center-instance-arn> \
  --session-duration PT1H

aws sso-admin create-account-assignment \
  --instance-arn <instance> --target-id <account-id> \
  --target-type AWS_ACCOUNT \
  --permission-set-arn <ps-arn> \
  --principal-type GROUP --principal-id <group-id>
```

## Pre-flight safety checks

- **MANDATORY CONFIRMATION GATE.** Before any state-changing operation
  (`organizations attach-policy`, `controltower create-landing-zone`,
  `configservice put-configuration-aggregator`), emit:
  `CONFIRM: About to <action> for <governance layer> in <account>.
  Proceed? (yes/no)` and wait for explicit `yes`.
- **Dry-run SCP attachment.** Test a new SCP by attaching to a single
  sandbox account first. Verify via the IAM Policy Simulator before
  attaching at the root.
- **Verify the management account has MFA + no access keys.**
- **Snapshot the current SCP tree before changes.**
- **Verify Config aggregator coverage after every account creation.**

