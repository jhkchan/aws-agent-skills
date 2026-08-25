# Error Handling — Lambda Invocation Troubleshooter

Per-layer remediation guidance moved verbatim from SKILL.md. Load on
demand.

### Remediation guidance


### For TIMEOUT_CONFIG — timeout too low

```bash
aws lambda update-function-configuration --function-name <name> \
  --timeout <new> --profile <p>
```
Acceptable range: 1-900 seconds. Consider async invocation if the
operation legitimately exceeds 29s (the API Gateway limit).

### For TIMEOUT_DOWNSTREAM — downstream genuinely slow

Address the downstream service:
- DynamoDB: switch to on-demand or raise WriteCapacityUnits.
- S3: use multipart upload for large objects; check bucket region.
- RDS: add RDS Proxy for connection reuse.
- External HTTP: implement client-side retry with exponential backoff;
  consider caching responses.

### For MEMORY_CONFIG — memory too low

```bash
aws lambda update-function-configuration --function-name <name> \
  --memory-size <new> --profile <p>
```
Target ≥ 20% headroom over observed `MaxMemoryUsed`. Note that CPU
proportion increases with memory — a CPU-bound function may resolve
both OOM and timeout symptoms with one memory bump.

### For COLD_START

- Java: enable SnapStart (`--snap-start ApplyOn=PublishedVersion`).
- Any runtime, sync-facing: enable provisioned concurrency on the
  invoked alias.
- Container: reduce image size.
- Generic: raise memory (linearly shrinks CPU-bound init).

### For PERMISSION_EXECUTION_ROLE

Add the minimum-scope permission to the role's identity-based policy:

```bash
aws iam put-role-policy --role-name <role-name> \
  --policy-name <name> \
  --policy-document '<JSON with specific Action and Resource>'
```
Prefer a new managed policy version over inline edits for audit
history. Verify with `simulate-principal-policy`.

### For PERMISSION_RESOURCE_POLICY

Add a statement to the function's resource-based policy:

```bash
aws lambda add-permission --function-name <name> \
  --statement-id <sid> --action lambda:InvokeFunction \
  --principal <caller-account-id> --output json --profile <p>
```

### For VPC_CONNECTIVITY

- Move function to a private subnet: `update-function-configuration
  --vpc-config SubnetIds=<private>,SecurityGroupIds=<sg>`.
- Add a NAT Gateway in the private subnet's route table.
- Or add a VPC endpoint for the destination AWS service.

### For VPC_ENDPOINT

Update the endpoint policy to allow the denied action. Test by bypassing
the endpoint (route via NAT) to confirm the endpoint is the cause.

### For ENV_VAR_KMS

Add `kms:Decrypt` on the customer-managed key ARN to the execution
role's identity-based policy. Verify with `simulate-principal-policy`.

### For ENV_VAR_MISSING

Add the variable:

```bash
aws lambda update-function-configuration --function-name <name> \
  --environment "Variables={X=value}" --profile <p>
```

### For INVOCATION_ASYNC

- Add a DLQ:
    `update-function-configuration --dead-letter-config TargetArn=<sqs-or-sns-arn>`.
- Or add an OnFailure destination:
    `put-function-event-invoke-config --destination-config ...`.
- For EventSourceMapping: tune `MaximumRetryAttempts` and
  `BisectBatchOnFunctionError`.

### For INVOCATION_SYNC

Align timeouts: Lambda Timeout ≤ caller's timeout. For operations
exceeding 29s, move to async invocation (caller receives 202, function
processes in the background).

### For ECR_IMAGE

- Re-push the image with the correct tag.
- Reduce image size below 10 GB (target < 500 MB for fast cold starts).
- Update `ImageConfig.Command` to match the image's entry point.

### For ECR_POLICY

Add a statement to the ECR repository policy:

```bash
aws ecr set-repository-policy --repository-name <repo> \
  --policy-text '<JSON granting ecr:BatchGetImage and
    ecr:GetDownloadUrlForLayer to the function account>' --profile <p>
```
