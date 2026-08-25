# Error Handling (load on demand) — CodeBuild Project Auditor

Error-handling and remediation detail moved verbatim from SKILL.md. Load on demand.

---

## Remediation guidance per verdict (moved from SKILL.md)

### For PRIVILEGED — privilegedMode enabled on non-Docker build

1. Verify the buildspec does not run Docker: check `source.buildspec`
   for `docker`, `buildctl`, `docker-compose`.
2. Re-fetch the full current environment block (the update is a
   full-replace, not a patch):
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].environment' --output json > /tmp/<n>-env.json`.
3. Edit `/tmp/<n>-env.json` to set `"privilegedMode": false`.
4. Apply the full environment JSON:
   `aws codebuild update-project --name <n> --environment file:///tmp/<n>-env.json`.
5. Confirm by re-fetching:
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].environment.privilegedMode'`.
6. If the build actually needs Docker, leave privilegedMode on and add
   a NOTE: "privilegedMode required for Docker-in-Docker build — no
   remediation."

### For SECRET_LEAK — plaintext secret in environment variables

1. Identify the leaked variable(s). Each must move to a secure channel.
2. Create a Secrets Manager secret (if not already):
   `aws secretsmanager create-secret --name <project>/<var> --secret-string <value>`.
3. Re-fetch the full environment block (full-replace update):
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].environment' --output json > /tmp/<n>-env.json`.
4. In `/tmp/<n>-env.json`: (a) remove the leaked entry from
   `environmentVariables`, (b) add a `secretsManager` array entry
   `{"secretsManagerArn":"arn:aws:secretsmanager:...","name":"<var>","type":"SECRETS_MANAGER"}`
   if not already present.
5. Apply: `aws codebuild update-project --name <n> --environment file:///tmp/<n>-env.json`.
6. **Rotate the leaked credential.** The plaintext value was visible in
   CloudTrail, the API, and the console for the lifetime of the
   project config. Treat it as compromised.
7. Audit CloudTrail for `BatchGetProjects` API calls during the exposure
   window — any principal with `codebuild:BatchGetProjects` read the
   plaintext secret.

### For NO_ENCRYPTION — S3 logs or artifacts without SSE-KMS

1. Create or identify a customer-managed KMS key:
   `aws kms create-key --description "CodeBuild <project> SSE-KMS key"`.
2. Update the key policy to grant the CodeBuild service role
   `kms:GenerateDataKey*` and `kms:Decrypt` on the key.
3. For S3 logs: re-fetch the full logs-config block:
   `aws codebuild batch-get-projects --names <n> --query 'projects[0].logsConfig' --output json > /tmp/<n>-logs.json`,
   then edit `s3Logs.encryptionDisabled` to `false` and set
   `s3Logs.kmsKeyArn` to the key ARN. Apply with
   `aws codebuild update-project --name <n> --logs-config file:///tmp/<n>-logs.json`.
4. For artifacts: re-fetch `projects[0].artifacts` to a file, edit
   `encryptionDisabled` to `false`, and apply with
   `aws codebuild update-project --name <n> --artifacts file:///tmp/<n>-artifacts.json`.
   The top-level artifact-encryption key is also settable via
   `--encryption-key <key-arn>`.
5. For legacy cross-account artifacts, migrate to a customer-managed KMS
   key with a key policy granting the cross-account principal
   `kms:Decrypt`. Do NOT flip `encryptionDisabled` to false without the
   key policy in place — the cross-account build will fail.

### For OVERPERMISSIVE_ROLE — service role blast radius

1. Snapshot the current role policy (see Pre-flight).
2. Replace wildcard actions with named actions derived from CloudTrail
   `AssumedRole` events for the role (90-day window minimum).
3. Replace `Resource: "*"` with the specific ARNs the build actually
   accesses (S3 buckets, ECR repos, KMS keys, Secrets Manager secrets).
4. For `iam:PassRole`: scope to the specific role ARN(s) the build
   passes, and add `iam:PassedToService` condition to constrain which
   service receives the role.
5. For the trust policy: add
   `Condition: {StringEquals: {"aws:SourceArn": "arn:aws:codebuild:<region>:<account>:project/<name>"}}`
   to scope assumption to this project only.
6. Validate with `aws iam simulate-principal-policy --policy-source-arn <role-arn> --action-names <list>`.

### For CONFIG_GAP — VPC / badge / forensics / cache

- **VPC missing (Step 5a):** create a VPC with private subnets, NAT
  gateway, and restrictive security groups. Re-fetch any existing
  vpcConfig block first, then apply the full JSON:
  `aws codebuild update-project --name <n> --vpc-config '{"vpcId":"vpc-aaa","subnets":["subnet-private-1"],"securityGroupIds":["sg-build-egress-only"]}'`.
- **Public subnets (Step 5b):** move the build to private subnets. Update
  route tables or change the subnet list (full-replace via `--vpc-config`).
- **Badge enabled (Step 6):** disable with the toggle flag:
  `aws codebuild update-project --name <n> --no-badge-enabled`.
- **No logs (Step 7a):** enable at least CloudWatch Logs by passing the
  full logs-config JSON:
  `aws codebuild update-project --name <n> --logs-config '{"cloudWatchLogs":{"status":"ENABLED"},"s3Logs":{"status":"DISABLED"}}'`.
- **CloudWatch no KMS (Step 7b):** associate a key:
  `aws logs associate-kms-key --log-group-name <group> --kms-key-id <key-id>`.
- **Cache bucket exposed (Step 7d):** enable S3 Block Public Access on
  the cache bucket:
  `aws s3api put-public-access-block --bucket <b> --public-access-block-configuration BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true`.

### For OK

1. No remediation required.
2. Recommend enabling CloudWatch Logs with SSE-KMS as defense-in-depth.
3. Recommend scoping the service-role trust policy to the project ARN if
   not already scoped.

