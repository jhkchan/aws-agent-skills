# Remediation Guidance — Secrets Manager Rotation Auditor

> Moved verbatim from SKILL.md for progressive disclosure (agentskills.io). Load on demand.

## Remediation guidance

### For UNROTATED secrets

1. **Determine the secret type** and whether a managed rotation template
   exists (see Step 2 sub-check).
2. **For RDS/Aurora/Redshift/DocDB secrets:** use the AWS managed rotation
   template via Serverless Application Repository or CloudFormation:
   ```bash
   aws secretsmanager rotate-secret \
     --secret-id <name> \
     --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<rotation-lambda> \
     --rotation-rules AutomaticallyAfterDays=30
   ```
3. **For API tokens / custom secrets (type `Other`):** author a custom
   rotation Lambda implementing the four-step contract
   (createSecret/setSecret/testSecret/finishSecret). See the AWS
   [Rotation function templates](https://docs.aws.amazon.com/secretsmanager/latest/userguide/reference_available-rotation-templates.html)
   reference for starter code.
4. **Set a rotation interval appropriate to the secret type:**
   - Database credentials: 30 days (industry standard; CIS benchmark)
   - API tokens: 7-90 days (depends on provider policy)
   - SSH keys: 90 days
5. **Trigger the first rotation manually** to verify the Lambda works
   before relying on the automatic schedule:
   ```bash
   aws secretsmanager rotate-secret --secret-id <name>
   ```

### For ROTATION_BROKEN secrets

1. **Lambda deleted (Step 3b):** recreate the Lambda from the rotation
   template, then update the secret's rotation config:
   ```bash
   aws secretsmanager update-secret --secret-id <name> \
     --rotation-lambda-arn arn:aws:lambda:<region>:<account>:function:<new-lambda>
   ```
2. **Lambda invocation erroring (Step 4a):** diagnose by reading the
   Lambda CloudWatch logs:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/<rotation-lambda> \
     --filter-pattern ERROR \
     --limit 20
   ```
   Apply the fix based on the error code table in Step 4a.
3. **Execution-role permission missing (Step 5):** attach the
   `SecretsManagerRotation` managed policy or a scoped custom policy
   with the four required actions. For customer-managed KMS keys, add
   `kms:Decrypt` to the role's policy.
4. **VPC connectivity broken (Step 5, Link 3):** verify the Lambda's
   subnet route table has a path to the DB subnet, and the Lambda's
   security group allows egress to the DB security group on the DB port.
5. **AWSPENDING stuck version (Step 6):** first determine which
   credential is live on the target (test a connection with both
   `AWSCURRENT` and `AWSPENDING` values). Then either:
   - If `AWSPENDING` is the live credential: promote it to `AWSCURRENT`
     manually:
     ```bash
     aws secretsmanager update-secret-version-stage \
       --secret-id <name> \
       --version-stage AWSCURRENT \
       --move-to-version-id <pending-version-id> \
       --remove-from-version-id <current-version-id>
     ```
   - If `AWSCURRENT` is still the live credential: cancel the pending
     version:
     ```bash
     aws secretsmanager update-secret-version-stage \
       --secret-id <name> \
       --version-stage AWSPENDING \
       --remove-from-version-id <pending-version-id>
     ```
6. **After fixing the root cause:** trigger a manual rotation to verify:
   ```bash
   aws secretsmanager rotate-secret --secret-id <name>
   ```
   Check that `LastRotatedDate` advances and no new `AWSPENDING` is left
   behind.

### For STALE secrets

1. **Check CloudWatch Logs** for intermittent Lambda errors:
   ```bash
   aws logs filter-log-events \
     --log-group-name /aws/lambda/<rotation-lambda> \
     --start-time <last-rotation-epoch> \
     --limit 50
   ```
2. **Increase the Lambda timeout** if timeouts are the cause (common for
   large databases).
3. **Trigger a manual rotation** to bring the credential current:
   ```bash
   aws secretsmanager rotate-secret --secret-id <name>
   ```
4. **Monitor the next scheduled rotation** to verify it succeeds
   automatically. If the next rotation also fails, escalate to
   ROTATION_BROKEN diagnosis.

### For OK secrets

1. No remediation required.
2. Optionally set up a CloudWatch alarm on rotation failure:
   ```bash
   aws cloudwatch put-metric-alarm \
     --alarm-name "<name>-rotation-failed" \
     --metric-name RotationFailed \
     --namespace AWS/SecretsManager \
     --dimensions Name=SecretId,Value=<name> \
     --threshold 1 --comparison-operator GreaterThanOrEqualToThreshold \
     --period 300 --evaluation-periods 1
   ```

### For secrets in the recovery window (DELETION_FLAG)

1. **Verify no workload references the secret** — search application
   configurations, environment variables, and infrastructure code for
   the secret ARN or name.
2. **If still needed, restore:**
   ```bash
   aws secretsmanager restore-secret --secret-id <name>
   ```
3. **If deletion is intentional and no workload references it:**
   allow the purge to proceed. Document the deletion in the change
   management record.

