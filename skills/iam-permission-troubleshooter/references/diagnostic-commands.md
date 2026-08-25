# Diagnostic Commands — IAM Permission Troubleshooter

Ordered diagnostic CLI sequence and policy-simulator verification moved verbatim from SKILL.md. Loaded on demand.

## Step 9 — policy simulator verification (from SKILL.md § Step 9)

```bash
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/app-role \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::app-data-prod/file.txt \
  --eval-decision SHAPE \
  --output json \
  --profile <profile>
```

A return of `allowed` means the simulator confirms the principal can
perform the action. `explicitDeny` means a Deny statement still matches.
`implicitDeny` means no Allow matches. Add `--markers` or
`--detail-evaluation` to surface the matched statement.

**Simulator caveat.** The simulator tests individual actions in isolation.
It does NOT catch chained API flows (e.g., a Lambda function calling S3
under the function's role — the simulator tests `lambda:InvokeFunction`
and `s3:GetObject` separately but cannot detect that the Lambda runtime
needs the second permission on the function's role, not the caller's).
Always cross-reference simulator results with CloudTrail for chained flows.

## Diagnostic command reference (from SKILL.md § Diagnostic command reference)

Run these in order. Each command's output narrows the decision tree.

```bash
# 1. Confirm the caller identity. The ARN reveals assumed-role vs user
#    vs federated. Federation paths carry session policies.
aws sts get-caller-identity --profile <profile>

# 2. Pull the CloudTrail event. errorMessage disambiguates implicit vs
#    explicit deny. sourceIPAddress and requestParameters give the
#    condition-key context.
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=PutObject \
  --start-time $(date -d '-1 hour' +%s) \
  --end-time $(date +%s) \
  --profile <profile>

# 3. List every policy attached to the principal. Include inline.
aws iam list-attached-role-policies --role-name <role> --profile <profile>
aws iam list-role-policies --role-name <role> --profile <profile>
aws iam get-role-policy --role-name <role> --policy-name <inline> --profile <profile>
aws iam get-policy-version \
  --policy-arn arn:aws:iam::111111111111:policy/<managed> \
  --version-id v1 --profile <profile>

# 4. For assumed-role failures, read the target role's trust policy.
aws iam get-role --role-name <target-role> --query 'Role.AssumeRolePolicyDocument' --profile <profile>

# 5. For SCP-blocked calls, list the policies attached at every level
#    above the account (root, parent OUs, account itself).
aws organizations list-policies-for-target \
  --target-id <account-id> --filter SERVICE_CONTROL_POLICY --profile <profile>
aws organizations describe-policy --policy-id <policy-id> --profile <profile>

# 6. For permissions boundary, check the boundary ARN on the role.
aws iam get-role --role-name <role> --query 'Role.PermissionsBoundary' --profile <profile>

# 7. Simulate the principal against the exact action and resource.
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::111111111111:role/<role> \
  --action-names s3:GetObject \
  --resource-arns arn:aws:s3:::bucket/key \
  --eval-decision SHAPE \
  --output json --profile <profile>

# 8. For KMS-encrypted resources, read the key policy. The key policy
#    is the authoritative source — IAM grants on the caller do not
#    help if the key policy does not include them.
aws kms get-key-policy --key-id <key-id> --policy-name default --profile <profile>

# 9. For S3 access specifically, use the S3 access analyzer to surface
#    the bucket ACL and policy combined view.
aws accessanalyzer validate-policy-resource \
  --policy-arn arn:aws:s3:::bucket --profile <profile>
```
