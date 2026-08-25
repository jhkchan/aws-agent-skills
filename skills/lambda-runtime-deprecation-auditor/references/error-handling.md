# Error Handling — Lambda Runtime Deprecation Auditor

Per-verdict remediation guidance moved verbatim from SKILL.md. Load on
demand.

### Remediation guidance


### For DEPRECATED_RUNTIME — runtime upgrade

1. Identify the target runtime from the supported-runtime table. Choose
   the closest major version (python3.9 → python3.12, nodejs16.x →
   nodejs20.x).
2. Test code compatibility: run unit/integration tests against the target
   runtime. Check for removed stdlib modules and language-feature changes.
3. Update the function:
   `aws lambda update-function-configuration --function-name <name> --runtime <target> --profile <p>`
4. Publish a new version: `aws lambda publish-version --function-name <name>`
5. If using aliases, point the production alias at the new version after
   validation.
6. Monitor CloudWatch Logs for runtime errors for 24-48 hours.

### For PUBLIC_EXPOSURE — restrict function URL

1. If the URL was created by mistake, delete it:
   `aws lambda delete-function-url-config --function-name <name>`
2. If the URL is required, switch to authenticated mode:
   `aws lambda update-function-url-config --function-name <name> --auth-type AWS_IAM`
3. Grant callers `lambda:InvokeFunctionUrl` via IAM policy.
4. If public access is genuinely required (e.g., a webhook receiver), add
   a CloudFront distribution + WAF in front of the URL for rate-limiting
   and request validation. Do not expose the raw Function URL.

### For OVERPERMISSIVE — scope down execution role

1. Identify the actual AWS API calls the function makes (CloudTrail,
  90-day window of events for the role ARN).
2. Build a least-privilege policy from observed actions + resources.
3. Use AWS IAM Access Analyzer policy generation for automated scoping.
4. Create a new scoped managed policy and attach it to the role.
5. Remove the over-permissive policy after validation.
6. Verify with `aws iam simulate-principal-policy` against the new policy.

### For CONFIG_GAP — close observability gaps

1. **Enable active tracing:**
   `aws lambda update-function-configuration --function-name <name> --tracing-config Mode=Active`
2. **Add a DLQ (for async-invoked functions):**
   `aws lambda update-function-configuration --function-name <name> --dead-letter-config TargetArn=<sqs-or-sns-arn>`
3. **Set log retention:**
   `aws logs put-retention-policy --log-group-name /aws/lambda/<name> --retention-in-days 30`
4. **Remove reserved-concurrency kill switch** (if `0`):
   `aws lambda delete-function-concurrency --function-name <name>`

### For OK

1. No remediation required.
2. Recommend periodic re-audit when AWS publishes new runtime deprecation
   schedules (check the AWS Lambda runtime release notes quarterly).
3. Recommend enabling CloudWatch Alarms on `Errors`, `Throttles`, and
   `Duration` (p99) as proactive monitoring.
