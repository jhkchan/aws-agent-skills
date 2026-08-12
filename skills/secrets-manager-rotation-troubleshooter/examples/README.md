# Example usage: secrets-manager-rotation-troubleshooter

A walkthrough showing the skill diagnosing a Secrets Manager rotation
failure where the rotation Lambda was never VPC-attached, mimicking a
"secret rotation is broken" page. Demonstrates the symptom-to-layer
triage, the LastRotatedDate-vs-schedule-expression health check, the
evidence-backed ROOT_CAUSE_IDENTIFIED verdict, and the
Lambda-VPC-config root cause.

## Input (user prompt)

> Our payments database secret `prod/db/payments-primary` has not
> rotated in 8 days. LastRotatedDate is `2026-07-30`. The rotation
> Lambda logs "Could not connect to database at host
> prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com port 5432"
> followed by "Task timed out after 15.00 seconds" on every rotation
> attempt. RotationEnabled is true. The RDS cluster is private in a
> VPC. Please find the actual root cause.

```text
SecretId: prod/db/payments-primary
RotationEnabled: true
RotationLambdaARN: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRotation-payments-primary
RotationRules: {ScheduleExpression: 'rate(1d)'}
LastRotatedDate: 2026-07-30T03:17:22Z
KmsKeyId: alias/aws/secretsmanager

Rotation Lambda configuration:
  Timeout: 15
  MemorySize: 256
  Runtime: python3.12
  Handler: lambda_function.lambda_handler
  VpcConfig: (none — VpcId is empty)
  Role: arn:aws:iam::111111111111:role/SecretsManagerRotation-payments-role
  Environment.Variables:
    SECRETS_MANAGER_SECRET_ID: prod/db/payments-primary
    SECRETS_MANAGER_MASTER_ID: prod/db/payments-primary-master

Database context:
  Engine: aurora-postgresql
  Cluster endpoint: prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com
  Port: 5432
  Subnet: subnet-private-a (10.0.10.0/24), route table local-only
  Security Group sg-db: ingress 5432 from sg-app (no sg-lambda-rotation)

Recent rotation Lambda log pattern:
  [INFO]  createSecret: staging new password as AWSPENDING v3
  [INFO]  setSecret: attempting connection to host
          prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com port 5432
  [ERROR] Could not connect to database at host
          prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com port 5432
  Task timed out after 15.00 seconds

Rotation role permissions (verified via simulate-principal-policy):
  secretsmanager:GetSecretValue on the secret: ALLOWED
  secretsmanager:PutSecretValue on the secret: ALLOWED
  kms:Decrypt on alias/aws/secretsmanager: not required (AWS-managed)
```

## Skill output

```text
TARGET: prod/db/payments-primary
VERDICT: ROOT_CAUSE_IDENTIFIED
REASON: The rotation Lambda SecretsManagerRotation-payments-primary has
  VpcConfig empty (the Lambda is NOT VPC-attached), but the target
  Aurora PostgreSQL cluster lives in subnet-private-a
  (10.0.10.0/24) with a local-only route table. The Lambda's outbound
  TCP to port 5432 on the cluster endpoint has no route; the Lambda
  blocks until the 15s timeout. LastRotatedDate is 2026-07-30 — eight
  daily schedule intervals have been missed because every invocation
  fails at the setSecret step.
LAYER: ROTATION_LAMBDA_VPC
EVIDENCE:
  - Symptom: LastRotatedDate is 2026-07-30T03:17:22Z; RotationRules
    is rate(1d); today is 2026-08-05 (eight missed rotations).
  - Probe: aws lambda get-function-configuration returns
    VpcConfig: null; SubnetIds and SecurityGroupIds are empty.
  - Probe: aws logs filter-log-events returns "Could not connect to
    database at host prod-db.cluster-cxyz.us-east-1.rds.amazonaws.com
    port 5432" followed by "Task timed out after 15.00 seconds" in
    eight rotation attempts in the last 8 days; the preceding log
    line in every case is the setSecret step attempting the DB
    connection.
  - Probe: aws ec2 describe-route-tables for subnet-private-a
    returns a local-only route table (no NAT, no peering route to
    the Lambda's VPC — the Lambda is in the Lambda-managed network,
    not in any customer VPC).
  - Passing: aws iam simulate-principal-policy returns allowed for
    secretsmanager:GetSecretValue, PutSecretValue, DescribeSecret on
    the secret AND the Master Secret ARN; kms:Decrypt is not
    required (the secret uses alias/aws/secretsmanager); the
    EventBridge rule SecretsManager-prod-db-payments-primary exists,
    is ENABLED, and its target is the rotation Lambda ARN (verified
    via events list-targets-by-rule); the rotation role's DB user
    (rotation_master) has the rds_superuser role (verified on the DB
    directly). The Lambda's Timeout of 15s is adequate for a
    reachable DB — raising the timeout will not fix this.
REMEDIATION:
  1. Attach the rotation Lambda to the database's private subnets
     and a security group that allows outbound to port 5432:
     aws lambda update-function-configuration \
       --function-name SecretsManagerRotation-payments-primary \
       --vpc-config SubnetIds=subnet-private-a,subnet-private-b,SecurityGroupIds=sg-lambda-rotation \
       --profile <p>
  2. Add an inbound rule to the DB security group sg-db allowing
     port 5432 from sg-lambda-rotation:
     aws ec2 authorize-security-group-ingress \
       --group-id sg-db --protocol tcp --port 5432 \
       --source-security-group-id sg-lambda-rotation --profile <p>
  3. Trigger an immediate rotation to verify:
     aws secretsmanager rotate-secret \
       --secret-id prod/db/payments-primary --profile <p>
  4. Verify LastRotatedDate advances within 5 minutes:
     aws secretsmanager describe-secret \
       --secret-id prod/db/payments-primary \
       --query LastRotatedDate --output text
CONFIRM: Before updating the Lambda VPC config and the DB SG, emit
  and await:
  "CONFIRM: About to attach SecretsManagerRotation-payments-primary
   to subnet-private-a, subnet-private-b with SG sg-lambda-rotation,
   and add an ingress rule to sg-db for port 5432 from
   sg-lambda-rotation. Proceed? (yes/no)"
  Do NOT run the CLI until the operator replies yes.
```

## What the skill caught that a generic assistant misses

1. **Distinguished ROTATION_LAMBDA_VPC from ROTATION_LAMBDA_TIMEOUT.**
   A generic assistant sees "Task timed out after 15 seconds" and
   recommends raising the timeout to 60s or 120s. The skill
   recognises that the timeout value (15s) is adequate for a
   reachable DB and the failure is the missing network path —
   raising the timeout would just delay each failure to 120s.

2. **Identified the failing step via the Lambda log line.** The
   skill reads the log stream immediately before each timeout and
   identifies the `setSecret` step attempting the DB connection.
   The step name routes the diagnosis to VPC/DB-endpoint layers,
   not to IAM or KMS.

3. **Ruled out IAM via positive evidence.** A common misdiagnosis on
   rotation failures is "fix the role permissions." The skill's
   `simulate-principal-policy` evidence shows all Secrets Manager
   and KMS permissions are ALLOWED — the role is not the issue.

4. **Ruled out the EventBridge schedule.** A common misdiagnosis on
   stale `LastRotatedDate` is "the schedule isn't firing." The
   skill verifies the rule exists, is ENABLED, and targets the
   correct Lambda — the schedule is healthy; the Lambda fails when
   invoked.

5. **Found the root cause in the Lambda's VpcConfig.** The skill
   cross-references `lambda get-function-configuration` (VpcConfig
   empty) with `ec2 describe-route-tables` for the DB subnet
   (local-only). The rotation Lambda was never attached to the
   database's VPC.

6. **Recommended the network-side fix, not a timeout increase.** The
   primary remediation is attaching the Lambda to the DB subnets
   and adding the SG ingress rule. Raising the Lambda timeout is
   not in the remediation at all — it would not address the root
   cause.

## Slash-command invocation

```
/aws:troubleshoot-secrets-manager-rotation
```

Or via the orchestrator:

```
/aws:pipeline
You: "diagnose why prod/db/payments-primary rotation has not run in 8 days"
```

The orchestrator emits
`[Phase: Troubleshoot | Skills routed: secrets-manager-rotation-troubleshooter]`
and hands off to this skill for the diagnostic block.

## Live-account follow-up (optional, requires AWS CLI)

After remediating, validate the rotation end-to-end:

```bash
# Confirm the Lambda is now VPC-attached
aws lambda get-function-configuration \
  --function-name SecretsManagerRotation-payments-primary \
  --query 'VpcConfig.{Subnets: SubnetIds, SGs: SecurityGroupIds}' \
  --profile default --output json

# Trigger an immediate rotation
aws secretsmanager rotate-secret \
  --secret-id prod/db/payments-primary --profile default

# Confirm LastRotatedDate advanced
aws secretsmanager describe-secret \
  --secret-id prod/db/payments-primary \
  --query 'LastRotatedDate' --output text --profile default

# Confirm no new Task timed out errors in the rotation Lambda logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/SecretsManagerRotation-payments-primary \
  --start-time $(date -u -v-15M +%s)000 \
  --filter-pattern '"Task timed out" OR "Could not connect"' \
  --profile default --output json
```

Then monitor the secret's `LastRotatedDate` for 1-2 days to confirm
the daily schedule continues to fire successfully.
