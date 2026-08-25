# Authentication and Cross-Account Access — CodeCommit Repository Deployer

Deep reference on CodeCommit authentication methods (git-remote-codecommit,
IAM git credentials, SSH keys), cross-account access configuration
(repository resource policy + KMS key policy), notification rule SNS
topic policy requirements, and repository trigger target policies. Loaded
on demand by the skill — kept out of the main SKILL.md body so the
provisioning procedure stays scannable.

## Authentication methods

### git-remote-codecommit (GRC) — recommended for IAM-role environments

GRC uses the AWS SigV4 signer to generate a session token from the
caller's IAM credentials. No static credentials to manage or rotate.

```bash
# Install GRC
pip install git-remote-codecommit

# Clone using the GRC helper
git clone codecommit://us-east-1@my-app-repo

# Or add as a remote
git remote add origin codecommit://us-east-1@my-app-repo
```

**Works with:** AWS SSO, assumed IAM roles, EC2 instance profiles,
ECS task roles, access keys. Any environment where AWS credentials are
available to the AWS CLI.

**Does NOT work with:** environments where the AWS CLI is not
configured or where Python/pip is not available.

### IAM git credentials (service-specific credentials)

Per-IAM-user static username and HTTPS password. Generated via IAM
console or CLI.

```bash
aws iam create-service-specific-credential \
  --user-name "ci-codecommit-user" \
  --service-name "codecommit.amazonaws.com"
# → Returns ServiceUserName and ServicePassword
```

The Git URL uses the generated credentials:

```text
https://<ServiceUserName>:<ServicePassword>@git-codecommit.us-east-1.amazonaws.com/v1/repos/my-app-repo
```

**Works with:** any Git client. Best for CI/CD pipelines that need a
fixed identity.

**Rotation:** manual. Each IAM user can have up to 2 sets of
credentials (for rotation without downtime).

### SSH keys

Per-IAM-user public SSH key uploaded to IAM.

```bash
# Upload a public key to IAM
aws iam upload-ssh-public-key \
  --user-name "developer-alice" \
  --ssh-public-key-body "file://~/.ssh/id_rsa.pub"
# → Returns SSHPublicKeyId

# Configure ~/.ssh/config
Host git-codecommit.*.amazonaws.com
  User APKXXXXXXXXXXXXXXXXXX  # The SSHPublicKeyId
  IdentityFile ~/.ssh/id_rsa
```

**Works with:** developers who prefer SSH-based auth.

**Rotation:** manual. Upload a new key and remove the old one.

## Cross-account access

Cross-account access requires grants at TWO levels:

### Level 1: Repository resource policy

The repository resource policy grants the cross-account principal
CodeCommit permissions.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "AWS": "arn:aws:iam::999999999999:root" },
    "Action": [
      "codecommit:GitPull",
      "codecommit:GitPush",
      "codecommit:GetRepository",
      "codecommit:CreatePullRequest"
    ],
    "Resource": "arn:aws:codecommit:us-east-1:123456789012:my-app-repo"
  }]
}
```

### Level 2: KMS key policy (if repository is KMS-encrypted)

If the repository uses a customer-managed KMS key, the key policy must
ALSO grant the cross-account principal.

```json
{
  "Sid": "AllowCrossAccountAccess",
  "Effect": "Allow",
  "Principal": { "AWS": "arn:aws:iam::999999999999:root" },
  "Action": [
    "kms:Decrypt", "kms:Encrypt", "kms:ReEncrypt*",
    "kms:GenerateDataKey*", "kms:DescribeKey"
  ],
  "Resource": "*"
}
```

### Level 3: Cross-account IAM policy

The cross-account principal's IAM policy must Allow the CodeCommit
actions (the resource policy is a resource-level grant; the principal
still needs an identity-level Allow).

**MISSING ANY OF THE THREE = AccessDenied.** The #1 cause of
cross-account CodeCommit failures is a missing KMS key policy grant.

## Notification rule SNS topic policy

Notification rules use AWS CodeStar Notifications, NOT EventBridge
directly. The SNS topic policy must grant the CodeStar Notifications
service principal.

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": { "Service": "codestar-notifications.amazonaws.com" },
    "Action": "sns:Publish",
    "Resource": "arn:aws:sns:us-east-1:123456789012:codecommit-notifications"
  }]
}
```

Without this grant, the notification rule creates successfully but no
notifications ever fire.

## Repository trigger target policy

Repository triggers (legacy mechanism) invoke Lambda or SNS directly.
The target resource policy must grant CodeCommit permission to invoke.

### Lambda target

```bash
aws lambda add-permission \
  --function-name "trigger-handler" \
  --statement-id "AllowCodeCommitInvoke" \
  --action "lambda:InvokeFunction" \
  --principal "codecommit.amazonaws.com" \
  --source-arn "arn:aws:codecommit:us-east-1:123456789012:my-app-repo"
```

### SNS target

The SNS topic policy must grant `codecommit.amazonaws.com` the
`sns:Publish` action.

## Common authentication pitfalls

### Pitfall 1: SSO user tries static git credentials

SSO users cannot generate service-specific credentials directly. They
must use GRC, which derives a session token from the SSO role.

**Fix:** Install GRC and use the `codecommit://` URL scheme.

### Pitfall 2: Cross-account access fails despite resource policy

The KMS key policy was not updated to grant the cross-account principal.

**Fix:** Add the cross-account principal to the KMS key policy with
`kms:Decrypt`, `kms:Encrypt`, `kms:GenerateDataKey*`.

### Pitfall 3: SSH key uploaded but Git fails

The SSH key was uploaded to GitHub but not to IAM. CodeCommit SSH keys
are managed in IAM, not in the repository settings.

**Fix:** Upload the public key via `aws iam upload-ssh-public-key` and
use the returned `SSHPublicKeyId` as the SSH user.

## Terraform examples

```hcl
# Cross-account repository resource policy
resource "aws_codecommit_repository" "repo" {
  repository_name = "my-app-repo"
  # ...
}

# KMS key with cross-account policy
resource "aws_kms_key" "codecommit" {
  description = "CodeCommit encryption key"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Enable IAM User Permissions"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::123456789012:root" }
        Action   = "kms:*"
        Resource = "*"
      },
      {
        Sid    = "AllowCodeCommitServiceAccess"
        Effect = "Allow"
        Principal = { Service = "codecommit.amazonaws.com" }
        Action = [
          "kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
          "kms:GenerateDataKey*", "kms:DescribeKey"
        ]
        Resource = "*"
      },
      {
        Sid    = "AllowCrossAccountAccess"
        Effect = "Allow"
        Principal = { AWS = "arn:aws:iam::999999999999:root" }
        Action = [
          "kms:Decrypt", "kms:Encrypt", "kms:ReEncrypt*",
          "kms:GenerateDataKey*", "kms:DescribeKey"
        ]
        Resource = "*"
      }
    ]
  })
}
```

---

## Expert heuristic — git-remote-codecommit for IAM auth

A baseline model says "generate git credentials in the IAM console." The
correct heuristic recognizes three auth methods with different
operational profiles, and GRC is preferred for IAM-role-based
environments.

```text
CodeCommit authentication methods:
  ├── git-remote-codecommit (GRC) — RECOMMENDED for IAM-role environments
  │     AWS signer generates SigV4 session token from IAM credentials.
  │     URL: codecommit://<region>@<repo-name>
  │     Install: pip install git-remote-codecommit
  │     Pros: no static credentials; works with SSO, assumed roles, EC2.
  │
  ├── IAM git credentials (service-specific credentials)
  │     Per-IAM-user static username + HTTPS password.
  │     URL: https://git-codecommit.<region>.amazonaws.com/...
  │     Pros: works with any Git client. Cons: static; manual rotation.
  │
  └── SSH keys
        Per-IAM-user public SSH key uploaded to IAM.
        URL: ssh://git-codecommit.<region>.amazonaws.com/...
        Pros: familiar. Cons: per-IAM-user; key rotation manual.
```

## Expert heuristic — KMS key policy cross-account grant

For cross-account repository access, the repository resource policy
grants the cross-account principal `codecommit:GitPull/GitPush`. But if
the repository is encrypted with a customer-managed KMS key, the key
policy must ALSO grant the cross-account principal.

```text
Cross-account CodeCommit access (encrypted repository):
  Repository resource policy:
    Principal: arn:aws:iam::<cross-acct>:root
    Actions: codecommit:GitPull, codecommit:GitPush

  KMS key policy (ALSO required):
    Principal: arn:aws:iam::<cross-acct>:root
    Actions: kms:Decrypt, kms:Encrypt, kms:ReEncrypt*,
             kms:GenerateDataKey*, kms:DescribeKey

  MISSING EITHER = AccessDenied on push/pull.
```

## Step 8 setup — GRC and IAM git credentials

**GRC setup for developers:**

```bash
pip install git-remote-codecommit
git clone codecommit://us-east-1@my-app-repo
```

**IAM git credentials setup (for CI):**

```bash
aws iam create-service-specific-credential \
  --user-name "ci-codecommit-user" \
  --service-name "codecommit.amazonaws.com" --region us-east-1
```
