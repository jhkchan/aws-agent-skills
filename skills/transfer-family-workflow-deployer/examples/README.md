# End-to-End Example: Transfer Family Workflow Deployment

A walkthrough showing how to use the `transfer-family-workflow-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a private SFTP server with custom Lambda
authentication, VPC_ENDPOINT for private connectivity, and a managed
workflow for automated file processing. The server needs:

- Protocol: SFTP
- Endpoint type: VPC_ENDPOINT (PrivateLink)
- VPC: vpc-aaa11122 (subnets: subnet-aaa, subnet-bbb)
- Security group: sg-sftp-internal
- Identity provider: custom Lambda (transfer-idp-auth)
- S3 bucket: file-landing-zone
- IAM role: TransferFamilyS3Access
- Session policy: per-user scoped to /file-landing-zone/home/<user>/*
- Managed workflow: COPY to data lake, TAG processed, virus scan
- Structured JSON logging to CloudWatch

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-transfer-family-workflow
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Transfer Family SFTP server with VPC_ENDPOINT in
      vpc-aaa11122. Custom Lambda identity provider. Per-user
      session policy. Managed workflow for file processing."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create transfer family sftp server"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
TRANSFER_FAMILY: s-abc123 (SFTP) — VPC_ENDPOINT
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Server: s-abc123 (SFTP)
  [✓] Endpoint type: VPC_ENDPOINT (PrivateLink)
  [✓] Identity provider: Custom Lambda (transfer-idp-auth)
  [✓] VPC: vpc-aaa11122 (subnets: subnet-aaa, subnet-bbb)
  [✓] Security groups: sg-sftp-internal
  [✓] S3 bucket: file-landing-zone
  [✓] IAM role: TransferFamilyS3Access (trust: transfer.amazonaws.com)
  [✓] Session policy: attached per-user (scoped to /home/<user>/*)
  [✓] Server host key: custom (RSA 4096)
  [✓] Managed workflow: w-def456 (COPY to data lake, TAG, virus scan)
  [✓] Structured logging: CloudWatch /aws/transfer/sftp
  [✓] Tags: Environment=production, App=file-landing-zone
VERIFICATION_COMMANDS:
  aws transfer describe-server --server-id s-abc123
  aws transfer list-users --server-id s-abc123
  aws transfer describe-workflow --workflow-id w-def456
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the IAM role for Transfer Family users
aws iam create-role \
  --role-name TransferFamilyS3Access \
  --assume-role-policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": {"Service": "transfer.amazonaws.com"},
      "Action": "sts:AssumeRole"
    }]
  }'

# Step 2: Attach S3 permissions to the role
aws iam put-role-policy \
  --role-name TransferFamilyS3Access \
  --policy-name S3Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": ["s3:ListBucket", "s3:GetObject", "s3:PutObject"],
      "Resource": [
        "arn:aws:s3:::file-landing-zone",
        "arn:aws:s3:::file-landing-zone/*"
      ]
    }]
  }'

# Step 3: Create the managed workflow
WORKFLOW_ID=$(aws transfer create-workflow \
  --description "File landing zone pipeline" \
  --steps file://workflow-steps.json \
  --on-exception-steps file://exception-steps.json \
  --query 'WorkflowId' --output text)

# Step 4: Create the SFTP server
SERVER_ID=$(aws transfer create-server \
  --protocols SFTP \
  --endpoint-type VPC_ENDPOINT \
  --endpoint-details VpcId=vpc-aaa11122,SubnetIds=subnet-aaa,subnet-bbb,SecurityGroupIds=sg-sftp-internal \
  --identity-provider-type LAMBDA \
  --function arn:aws:lambda:us-east-1:123456789012:function:transfer-idp-auth \
  --logging-role arn:aws:iam::123456789012:role/TransferFamilyLogging \
  --workflow-id "$WORKFLOW_ID" \
  --structured-log-destinations arn:aws:logs:us-east-1:123456789012:log-group:/aws/transfer/sftp \
  --query 'ServerId' --output text)

echo "Server ID: $SERVER_ID"
echo "Workflow ID: $WORKFLOW_ID"
```

---

## Step 4 — Post-deployment verification

```bash
# Server status — should be ONLINE
aws transfer describe-server \
  --server-id s-abc123 \
  --query 'Server.{State:State,EndpointType:EndpointType,Protocols:Protocols}'

# List users
aws transfer list-users \
  --server-id s-abc123

# Workflow status
aws transfer describe-workflow \
  --workflow-id w-def456 \
  --query 'Workflow.{Status:Status,Description:Description}'

# Test SFTP connectivity (from within the VPC)
sftp -i ~/.ssh/id_rsa alice@s-abc123.server.transfer.us-east-1.amazonaws.com
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Session policy | Not configured | Attached per-user | Without it, users inherit full IAM role permissions |
| Endpoint type | PUBLIC by default | VPC_ENDPOINT for internal | PUBLIC exposes SFTP to the internet |
| IAM role trust | Missing transfer.amazonaws.com | Correct trust policy | Without it, role cannot be assumed |
| Managed workflow | Not attached | COPY + TAG + CUSTOM | Without workflow, files sit in S3 unprocessed |
| On-exception steps | Not defined | TAG Status=Failed + SNS | Without it, failed files are left in indeterminate state |
| Structured logging | Not enabled | CloudWatch JSON logs | Without it, no audit trail of transfers |

---

## Related artifacts

- **Skill definition:** `skills/transfer-family-workflow-deployer/SKILL.md`
- **Identity providers and endpoints guide:** `skills/transfer-family-workflow-deployer/references/identity-providers-and-endpoints.md`
- **Managed workflows and AS2 guide:** `skills/transfer-family-workflow-deployer/references/managed-workflows-and-as2.md`
- **Slash command:** `commands/aws/deploy-transfer-family-workflow.md`
- **Eval suite:** `skills/transfer-family-workflow-deployer/evals/evals.json`
- **Legacy test cases:** `skills/transfer-family-workflow-deployer/eval/test-cases.yaml`
