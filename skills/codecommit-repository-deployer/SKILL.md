---
name: codecommit-repository-deployer
description: >-
  Provisions AWS CodeCommit repositories with production defaults:
  repository creation (create-repository), default branch, KMS
  encryption with customer-managed key, approval rule templates and
  branch protection, notification rules, pull request templates,
  cross-account resource policy, repository triggers (Lambda/SNS),
  migration from external Git, IAM git credentials vs SSH keys vs
  git-remote-codecommit, and CodeBuild/CodePipeline connection. Emits
  a READY_TO_DEPLOY checklist with verification commands. Use when
  creating a CodeCommit repository, configuring approval rules, KMS
  encryption, cross-account access, or migrating from external Git.
  Triggers: create codecommit repository, codecommit approval rule,
  codecommit kms encryption, codecommit cross-account, codecommit
  trigger, git-remote-codecommit.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with codecommit,
  kms, iam, sns, and lambda access (and cross-account STS assume-role
  if cross-account repository access). Works with Terraform
  aws_codecommit_repository / aws_codecommit_approval_rule_template /
  aws_codecommit_trigger resources and CloudFormation
  AWS::CodeCommit::Repository templates.
keywords:
  - aws
  - codecommit
  - repository
  - git
  - cloudops
  - deploy
  - provisioning
  - approval rule template
  - branch protection
  - kms encryption
  - notification rule
  - pull request template
  - cross-account
  - git-remote-codecommit
  - codebuild
  - codepipeline
tags:
  - aws
  - codecommit
  - git
  - cloudops
  - deploy
  - dev-tools
  - provisioning
  - approval-rule
  - branch-protection
  - kms
  - notification
  - cross-account
  - codebuild
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: DevTools
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - codecommit
    - git
    - cloudops
    - deploy
    - dev-tools
    - provisioning
    - approval-rule
    - branch-protection
    - kms
    - notification
    - cross-account
    - codebuild
  dependencies:
    - aws-orchestrator
  keywords:
    - create codecommit repository
    - codecommit default branch
    - codecommit approval rule template
    - codecommit branch protection
    - codecommit kms encryption
    - codecommit notification rule
    - codecommit pull request template
    - codecommit cross-account
    - codecommit trigger
    - git-remote-codecommit
  when_to_use: >-
    Invoke when the user wants to create a CodeCommit repository,
    configure a default branch, set up an approval rule template for
    branch protection, enable KMS encryption with a customer-managed key,
    create notification rules for repository events, add a pull request
    template, configure cross-account access via resource policy, set up
    repository triggers (Lambda/SNS), migrate from an external Git
    provider, connect the repository to CodeBuild or CodePipeline, or
    choose between IAM git credentials, SSH keys, and git-remote-codecommit
    (GRC) for authentication. Do NOT invoke for auditing existing
    repositories (use codecommit-repository-auditor), GitHub repository
    management, or CodeBuild/CodePipeline pipeline configuration itself.
---

# CodeCommit Repository Deployer

An AWS CloudOps agent skill that provisions AWS CodeCommit repositories
with correct defaults. The skill walks the operator through repository
creation, default branch selection, KMS encryption with a customer-
managed key, approval rule templates for branch protection, notification
rules, pull request templates, cross-account access via resource policy,
repository triggers, authentication method selection (IAM git credentials
vs SSH vs git-remote-codecommit), and migration from external Git,
captures configuration decisions, explains why each default matters, and
emits a READY_TO_DEPLOY checklist with copy-pasteable verification
commands.

## Activation keywords

create CodeCommit repository, CodeCommit default branch, CodeCommit
approval rule template, CodeCommit branch protection, CodeCommit KMS
encryption, CodeCommit notification rule, CodeCommit pull request
template, CodeCommit cross-account access, CodeCommit trigger,
git-remote-codecommit, CodeCommit migration.

## STRICT output contract

When this skill is invoked with a CodeCommit-provisioning request
(create a repository, configure branch protection, set up approval rule
templates, enable KMS encryption, configure cross-account access,
migrate from external Git, or a partial configuration), the agent MUST
respond with the READY_TO_DEPLOY checklist defined in the "Output
format" section using the literal all-caps labels `CODECOMMIT_REPO:`,
`VERDICT:`, `CHECKLIST:`, and `VERIFICATION_COMMANDS:`. Do NOT preface
the checklist with prose, headings, or disclaimers — emit the block as
the first lines of the response. This contract is what assertion-based
evals and downstream provisioning pipelines rely on; deviating from the
literal labels breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

### FORBIDDEN output patterns

1. **NEVER emit `VERDICT: READY_TO_DEPLOY` when any CHECKLIST item is
   `[✗]`.** If even one prerequisite is unmet, the verdict MUST be
   `PREREQUISITES_MISSING`. A mixed-verdict block is a contract
   violation.

2. **NEVER show KMS encryption as configured without verifying the key
   policy grants `codecommit.amazonaws.com`.** The repository creates
   successfully without the key policy grant — push/pull fails silently
   with AccessDenied at encryption time. The CHECKLIST MUST state "key
   policy grants codecommit.amazonaws.com" explicitly.

3. **NEVER show cross-account access as configured without verifying
   BOTH the repository resource policy AND the KMS key policy.**
   Granting only one results in AccessDenied. If the repository is
   KMS-encrypted, the CHECKLIST MUST list both policy grants.

4. **NEVER list an approval rule template without confirming it is
   ASSOCIATED with the repository.** Creating a template alone does
   nothing — it must be explicitly associated via
   `associate-approval-rule-template-with-repository`. The CHECKLIST
   MUST state "associated" or the item is `[✗]`.

5. **NEVER confuse notification rules (CodeStar Notifications) with
   repository triggers (Lambda/SNS direct invocation) in the CHECKLIST.**
   These are separate mechanisms. The CHECKLIST MUST list them as
   distinct items, not collapse them into a single "notifications" line.

6. **NEVER omit the git-remote-codecommit (GRC) URL from the output.**
   The GRC clone URL (`codecommit://<region>@<repo-name>`) is the
   primary verification artifact for IAM-role-based authentication. The
   CHECKLIST MUST include the auth method and URL.

7. **NEVER substitute lowercase or camelCase labels.** The literal
   all-caps labels (`CODECOMMIT_REPO:`, `VERDICT:`, `CHECKLIST:`,
   `VERIFICATION_COMMANDS:`) are parsed by downstream automation.
   Markdown headings or bold variants break the parser silently.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Repository creation and default branch | Core creation |
| Step 2 — KMS encryption (customer-managed key) | Encryption config |
| Step 3 — Approval rule templates and branch protection | Governance |
| Step 4 — Notification rules (SNS/EventBridge) | Event routing |
| Step 5 — Pull request templates | PR standardization |
| Step 6 — Cross-account access via resource policy | Cross-account |
| Step 7 — Repository triggers (Lambda/SNS) | Automation hooks |
| Step 8 — Authentication: git credentials vs SSH vs GRC | Auth selection |
| Step 9 — Migration from external Git | Repository migration |
| Step 10 — CodeBuild/CodePipeline connection | CI/CD wiring |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/approval-rules-and-protection.md | Approval rule detail |
| references/auth-and-cross-account.md | Auth + cross-account detail |

## Mindset

**One-line takeaway:** A CodeCommit repository is a managed Git
repository. The default branch must be explicitly created on first
push (or via the console). KMS encryption with a customer-managed key
requires the key policy to grant CodeCommit (`kms:GenerateDataKey` and
`kms:Encrypt/Decrypt`). Approval rule templates enforce required
reviewers on pull requests BEFORE merge — branch protection prevents
direct pushes to protected branches.

Three misconceptions dominate CodeCommit misconfiguration at provisioning
time:

- **"Creating the repository is enough to push code."** It is not. The
  default branch (e.g., `main`) does NOT exist until the first commit is
  pushed. If branch protection or approval rules are configured before
  the initial commit, the operator must push via an unprotected path
  first.

- **"KMS encryption just needs the key ARN."** It does not. CodeCommit
  must be a principal in the KMS key policy with `kms:Encrypt`,
  `kms:Decrypt`, `kms:ReEncrypt*`, `kms:GenerateDataKey*`, and
  `kms:DescribeKey`. A missing key policy grant is a silent failure
  (repository creates, push/pull fails with AccessDenied).

- **"git-remote-codecommit (GRC) is the same as git credentials."** It
  is not. GRC uses the AWS signer to generate a session token from IAM
  credentials — no static credentials to rotate, no SSH keys to manage.
  GRC is the recommended auth method for federated/IAM-role-based
  environments.

## Configuration dependency graph (novel heuristic)

CodeCommit configurations are NOT independent. The repository must exist
before KMS encryption, approval rules, notification rules, triggers, and
resource policies can be attached. The default branch must exist (first
push) before branch-level protection is effective. KMS key policy must
grant CodeCommit before the repository can encrypt.

| Configuration | Hard dependencies | Silent failure | Enables downstream |
|---|---|---|---|
| Repository | AWS account in a supported region | `defaultBranchName` set at creation but branch does NOT exist until first push | the repository ARN |
| KMS encryption | KMS key exists; key policy grants CodeCommit | repo creates fine WITHOUT valid key grant; push/pull fails at encryption time | at-rest encryption |
| Default branch | repository exists; first commit pushed | branch does not exist until `git push` succeeds; approval rules have nothing to protect | branch-level protection |
| Approval rule template | repository exists; approver pool known | template must be ASSOCIATED via associate call — creating alone does nothing | required-reviewer enforcement |
| Notification rule | SNS topic exists; topic policy grants CodeStar | rule creates but no notifications fire if topic policy missing | event-driven notifications |
| Cross-account resource policy | repository exists; cross-account principal identified | resource policy grants GitPull/Push but KMS key policy must ALSO grant cross-account | cross-account Git access |
| Repository trigger | repository exists; Lambda/SNS target exists | trigger creates but never fires if target resource policy missing CodeCommit | push/PR event automation |

**The KMS-key-policy row is the one a baseline model misses.** Creating
the repository with a KMS key ID succeeds even if the key policy does
not grant CodeCommit. The failure surfaces only at push/pull time.

## Expert heuristic: git-remote-codecommit for IAM auth

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

## Expert heuristic: approval rule template scope

Approval rule templates enforce that specific principals (or a number of
approvals) must approve a pull request BEFORE merge. Templates are
SEPARATE from repositories and must be explicitly ASSOCIATED.

```text
Approval rule template lifecycle:
  1. Create template (define approvals needed + approver pool)
  2. Associate template to repository (separate API call)
     → After association, rule is applied to ALL pull requests
  3. Pull request creation → merge BLOCKED until approvals met
  4. Override → principal with OverridePullRequestApprovalRules can bypass
```

**Branch protection is separate from approval rules.** Approval rules
govern PR merges. Branch protection (IAM policy denying
`codecommit:GitPush` to specific branches) governs direct pushes. For
full protection, you need BOTH.

## Expert heuristic: KMS key policy cross-account grant

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

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Repository name available | Must be unique within the account+region | `aws codecommit get-repository --repository-name <name>` (should fail) |
| KMS key exists (if encryption) | Customer-managed key must exist | `aws kms describe-key --key-id <key-id>` |
| KMS key policy grants CodeCommit | Without it, push/pull fails silently | `aws kms get-key-policy --key-id <key-id>` |
| SNS topic exists (if notifications) | Notification rule target must exist | `aws sns get-topic-attributes --topic-arn <arn>` |
| SNS topic policy grants CodeStar | Without it, notifications never fire | Check topic attributes |
| Cross-account principal identified | Resource policy + KMS key policy need it | `aws sts get-caller-identity` in cross-account |
| Lambda function exists (if triggers) | Trigger target must exist | `aws lambda get-function --function-name <name>` |
| IAM auth method decided | GRC vs git credentials vs SSH | Confirm auth model |

## Step 1 — Repository creation and default branch

```bash
REPO_ARN=$(aws codecommit create-repository \
  --repository-name my-app-repo \
  --repository-description "Microservice repository for my-app" \
  --tags Environment=production,Team=platform \
  --query 'repositoryMetadata.Arn' --output text --region us-east-1)
```

**Default branch caveat:** `--default-branch main` sets the default
branch name in metadata, but the `main` branch does NOT exist until you
push the first commit. The repository is empty at creation.

```bash
git remote add origin codecommit://us-east-1@my-app-repo
echo "# my-app" > README.md
git add . && git commit -m "initial commit"
git push -u origin main
```

**Common mistake:** configuring approval rules or branch protection on
`main` before the first push. The protections have nothing to act on.

## Step 2 — KMS encryption (customer-managed key)

CodeCommit encrypts repositories at rest. By default, it uses an
AWS-managed key. For customer-managed key encryption, the key must have
a policy granting CodeCommit.

Required KMS key policy statement:

```json
{
  "Sid": "AllowCodeCommitServiceAccess",
  "Effect": "Allow",
  "Principal": { "Service": "codecommit.amazonaws.com" },
  "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*",
             "kms:GenerateDataKey*", "kms:DescribeKey"],
  "Resource": "*"
}
```

**Critical:** the KMS key policy grant to `codecommit.amazonaws.com` is
the most commonly forgotten configuration. Without it, the repository
creates successfully, but all push/pull operations fail with
AccessDenied. Use CloudFormation/Terraform for IaC to ensure the key
policy is correct.

## Step 3 — Approval rule templates and branch protection

```bash
# Create an approval rule template
aws codecommit create-approval-rule-template \
  --approval-rule-template-name "require-two-reviewers" \
  --approval-rule-template-content '{
    "Version": "2018-02-08",
    "Statements": [{
      "Type": "Approvers",
      "NumberOfApprovalsNeeded": 2,
      "ApprovalPoolMembers": [
        "arn:aws:iam::123456789012:user/alice",
        "arn:aws:iam::123456789012:user/bob"
      ]
    }]
  }' --region us-east-1

# Associate the template with the repository (CRITICAL — template alone does nothing)
aws codecommit associate-approval-rule-template-with-repository \
  --approval-rule-template-name "require-two-reviewers" \
  --repository-name "my-app-repo" --region us-east-1
```

**Branch protection via IAM policy (deny direct push to main):**

```json
{
  "Sid": "DenyDirectPushToMain",
  "Effect": "Deny",
  "Action": "codecommit:GitPush",
  "Resource": "arn:aws:codecommit:us-east-1:123456789012:my-app-repo",
  "Condition": {
    "StringEquals": { "codecommit:References": ["refs/heads/main"] }
  }
}
```

This IAM policy, attached to developers, forces them to use pull
requests (which are then governed by the approval rule template).

## Step 4 — Notification rules (SNS/EventBridge)

Notification rules route repository events to SNS topics. Notification
rules use AWS CodeStar Notifications — NOT EventBridge directly.

```bash
# Create SNS topic and set policy granting CodeStar Notifications
TOPIC_ARN=$(aws sns create-topic --name "codecommit-notifications" \
  --query 'TopicArn' --output text --region us-east-1)

aws sns set-topic-attributes --topic-arn "$TOPIC_ARN" \
  --attribute-name Policy \
  --attribute-value '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"codestar-notifications.amazonaws.com"},"Action":"sns:Publish","Resource":"'"$TOPIC_ARN"'"}]}'

# Create the notification rule
aws codestar-notifications create-notification-rule \
  --name "my-app-pr-notifications" \
  --resource "arn:aws:codecommit:us-east-1:123456789012:my-app-repo" \
  --event-type-ids pull-request-created pull-request-updated pull-request-merged \
  --targets '[{"Id":"'"$TOPIC_ARN"'"}]' --detail-type FULL --region us-east-1
```

**Critical:** the SNS topic policy grant to
`codestar-notifications.amazonaws.com` is the #1 forgotten configuration
for notification rules. Without it, the rule creates but no
notifications fire.

## Step 5 — Pull request templates

A pull request template is a markdown file committed to the repository.
When a developer creates a PR, the template pre-populates the
description. Commit the file to a standard path
(e.g., `.github/PULL_REQUEST_TEMPLATE.md`). The template appears on new
PRs after the file is committed.

## Step 6 — Cross-account access via resource policy

Cross-account access requires the repository resource policy to grant
the cross-account principal CodeCommit permissions. If the repository
is KMS-encrypted, the KMS key policy must ALSO grant the cross-account
principal.

```text
Repository resource policy:
  Principal: arn:aws:iam::999999999999:root
  Actions: codecommit:GitPull, codecommit:GitPush, GetRepository

KMS key policy (ALSO required):
  Principal: arn:aws:iam::999999999999:root
  Actions: kms:Decrypt, kms:Encrypt, kms:ReEncrypt*,
           kms:GenerateDataKey*, kms:DescribeKey
```

**Critical:** BOTH the repository resource policy AND the KMS key policy
must grant the cross-account principal. Granting only one results in
AccessDenied. This is the #1 cause of cross-account CodeCommit failures.

## Step 7 — Repository triggers (Lambda/SNS)

Repository triggers are a LEGACY mechanism that invokes Lambda or SNS
directly when repository events occur. Triggers are SEPARATE from
notification rules.

```bash
aws codecommit put-repository-triggers \
  --repository-name "my-app-repo" \
  --trigger-name "lambda-on-push" \
  --trigger-target-arn "arn:aws:lambda:us-east-1:123456789012:function:trigger-handler" \
  --branches "main" "develop" --events "all" --region us-east-1
```

**The Lambda resource policy must allow CodeCommit to invoke:**

```bash
aws lambda add-permission \
  --function-name "trigger-handler" \
  --statement-id "AllowCodeCommitInvoke" \
  --action "lambda:InvokeFunction" \
  --principal "codecommit.amazonaws.com" \
  --source-arn "arn:aws:codecommit:us-east-1:123456789012:my-app-repo" --region us-east-1
```

## Step 8 — Authentication: git credentials vs SSH vs GRC

| Method | Best for | Credential type | Rotation |
|---|---|---|---|
| git-remote-codecommit (GRC) | SSO/federated, IAM-role-based | Session token (auto) | Automatic |
| IAM git credentials | CI/CD pipelines with fixed identity | Static username + password | Manual |
| SSH keys | Developers preferring key-based auth | Per-IAM-user SSH key | Manual |

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

## Step 9 — Migration from external Git

To migrate from GitHub, GitLab, or Bitbucket to CodeCommit, mirror the
repository.

```bash
# 1. Create the target CodeCommit repository (empty)
# 2. Clone the source repository as a mirror
git clone --mirror https://github.com/org/source-repo.git
cd source-repo.git
# 3. Push the mirror to CodeCommit (using GRC)
git push codecommit://us-east-1@migrated-repo --all
git push codecommit://us-east-1@migrated-repo --tags
# 4. Verify all branches and tags are present
aws codecommit list-branches --repository-name "migrated-repo" --region us-east-1
```

**Migration checklist:** all branches mirrored; all tags pushed
explicitly (`--tags`); pull request history is NOT migrated (CodeCommit
does not import PRs from external providers); webhooks/CI must be
reconfigured; developer access must be reconfigured.

## Step 10 — CodeBuild/CodePipeline connection

The pipeline service role needs CodeCommit permissions:

```json
{
  "Effect": "Allow",
  "Action": ["codecommit:GetRepository", "codecommit:GitPull",
             "codecommit:UploadArchive", "codecommit:GetUploadArchiveStatus",
             "codecommit:CancelUploadArchive"],
  "Resource": "arn:aws:codecommit:us-east-1:123456789012:my-app-repo"
}
```

Pipeline source action: `SourceType: CODECOMMIT`,
`SourceLocation: https://codecommit.us-east-1.amazonaws.com/v1/repos/my-app-repo`,
`Branch: main`. If the repository is KMS-encrypted, the pipeline service
role also needs `kms:Decrypt` on the key.

## NEVER do these things

1. **NEVER assume the default branch exists at creation.** The
   `defaultBranchName` is metadata. The branch does NOT exist until the
   first commit is pushed.

2. **NEVER create a KMS-encrypted repository without verifying the key
   policy grants CodeCommit.** The repository creates successfully, but
   all push/pull operations fail with AccessDenied.

3. **NEVER grant cross-account access via only the repository resource
   policy.** If the repository is KMS-encrypted, the KMS key policy must
   ALSO grant the cross-account principal.

4. **NEVER confuse notification rules with repository triggers.**
   Notification rules use CodeStar Notifications. Repository triggers
   invoke Lambda/SNS directly. They are separate mechanisms.

5. **NEVER create a notification rule without verifying the SNS topic
   policy.** The SNS topic policy must grant
   `codestar-notifications.amazonaws.com` the `sns:Publish` action.

6. **NEVER create a repository trigger without verifying the target
   resource policy.** Lambda must grant `codecommit.amazonaws.com`
   `lambda:InvokeFunction`. SNS must grant CodeCommit `sns:Publish`.

7. **NEVER assume approval rule templates auto-apply to repositories.**
   Templates must be explicitly ASSOCIATED via
   `associate-approval-rule-template-with-repository`.

8. **NEVER rely on approval rules alone for branch protection.**
   Approval rules govern PR merges. Branch protection requires an IAM
   policy denying `codecommit:GitPush` to specific branches.

9. **NEVER use static git credentials for SSO/federated environments.**
   Use git-remote-codecommit (GRC) for federated/IAM-role-based auth.

10. **NEVER forget to migrate tags during external Git migration.**
    `git push --mirror` does NOT always carry tags. Run `git push --tags`
    explicitly.

## Output format

```text
CODECOMMIT_REPO: <repository-name> (<repository-arn>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Repository name: <name> (unique in account+region)
  [✓|✗] Default branch: <branch> (created at first push)
  [✓|✗] Description: <description>
  [✓|✗] KMS encryption: customer-managed key <key-id> (key policy grants CodeCommit) | AWS-managed
  [✓|✗] KMS key policy cross-account: granted to <cross-acct> | N/A
  [✓|✗] Approval rule template: <template-name> (associated, <N> approvals needed)
  [✓|✗] Branch protection: IAM policy denies direct push to <branch> | Not configured
  [✓|✗] Notification rule: <rule-name> → SNS <topic-arn> (topic policy grants CodeStar)
  [✓|✗] Pull request template: <path> (committed to repo)
  [✓|✗] Cross-account access: resource policy grants <cross-acct-principal>
  [✓|✗] Repository trigger: <trigger-name> → <target-arn> | None
  [✓|✗] Auth method: git-remote-codecommit (GRC) | IAM git credentials | SSH keys
  [✓|✗] CodePipeline/CodeBuild: service role has codecommit:GetRepository
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws codecommit get-repository --repository-name <name> --region <region>
  aws kms describe-key --key-id <key-id> --region <region>
  aws codecommit list-approval-rule-templates --region <region>
  aws codestar-notifications list-notification-rules --region <region>
```

### Worked example — repository with KMS encryption, approval rules, and cross-account resource policy

```text
CODECOMMIT_REPO: shared-platform-repo (arn:aws:codecommit:us-east-1:123456789012:shared-platform-repo)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Repository name: shared-platform-repo (unique in account 123456789012, us-east-1)
  [✓] Default branch: main (created at first push)
  [✓] Description: Cross-platform shared library repository
  [✓] KMS encryption: customer-managed key arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ef-1234-567890abcdef (key policy grants codecommit.amazonaws.com: kms:Encrypt, Decrypt, ReEncrypt*, GenerateDataKey*, DescribeKey)
  [✓] KMS key policy cross-account: granted to arn:aws:iam::999999999999:root (kms:Decrypt, Encrypt, ReEncrypt*, GenerateDataKey*, DescribeKey)
  [✓] Cross-account resource policy: grants arn:aws:iam::999999999999:root (codecommit:GitPull, GitPush, GetRepository, UploadArchive)
  [✓] Approval rule template: require-two-reviewers (associated, 2 approvals needed, pool: arn:aws:iam::123456789012:user/alice, arn:aws:iam::123456789012:user/bob)
  [✓] Branch protection: IAM policy DenyDirectPushToMain denies codecommit:GitPush on refs/heads/main
  [✓] Notification rule: platform-pr-notifications → SNS arn:aws:sns:us-east-1:123456789012:codecommit-notifications (topic policy grants codestar-notifications.amazonaws.com sns:Publish)
  [✓] Pull request template: .github/PULL_REQUEST_TEMPLATE.md (committed to repo)
  [✓] Repository trigger: lambda-on-push → arn:aws:lambda:us-east-1:123456789012:function:trigger-handler (Lambda policy grants codecommit.amazonaws.com lambda:InvokeFunction)
  [✓] Auth method: git-remote-codecommit (GRC) — clone URL: codecommit://us-east-1@shared-platform-repo
  [✓] CodePipeline/CodeBuild: service role has codecommit:GetRepository + GitPull on arn:aws:codecommit:us-east-1:123456789012:shared-platform-repo
  [✓] Tags: Environment=production, Team=platform, CrossAccount=true
VERIFICATION_COMMANDS:
  aws codecommit get-repository --repository-name shared-platform-repo --region us-east-1
  aws kms describe-key --key-id arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ef-1234-567890abcdef --region us-east-1
  aws kms get-key-policy --key-id arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4-5678-90ef-1234-567890abcdef --policy-name default --region us-east-1
  aws codecommit list-approval-rule-templates --region us-east-1
  aws codestar-notifications list-notification-rules --region us-east-1
  # Cross-account verification (run in account 999999999999):
  git clone codecommit://us-east-1@shared-platform-repo
```

### Worked example — PREREQUISITES_MISSING (KMS key policy not granted)

```text
CODECOMMIT_REPO: my-new-repo (arn:aws:codecommit:us-east-1:123456789012:my-new-repo)
VERDICT: PREREQUISITES_MISSING
CHECKLIST:
  [✓] Repository name: my-new-repo (unique in account 123456789012, us-east-1)
  [✓] Default branch: main (will be created at first push)
  [✗] KMS encryption: customer-managed key arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4 — KEY POLICY DOES NOT GRANT codecommit.amazonaws.com. Push/pull will fail with AccessDenied. Add kms:Encrypt, Decrypt, ReEncrypt*, GenerateDataKey*, DescribeKey to the key policy for principal codecommit.amazonaws.com before proceeding.
  [✗] KMS key policy cross-account: blocked by missing CodeCommit grant (fix above first)
  [✓] Approval rule template: require-two-reviewers (associated, 2 approvals needed)
  [✓] Branch protection: IAM policy DenyDirectPushToMain configured
  [✓] Auth method: git-remote-codecommit (GRC) — clone URL: codecommit://us-east-1@my-new-repo
VERIFICATION_COMMANDS:
  aws kms get-key-policy --key-id arn:aws:kms:us-east-1:123456789012:key/a1b2c3d4 --policy-name default --region us-east-1
  # Verify the key policy includes a statement with Principal codecommit.amazonaws.com before deploying
```

## Error handling

### Push/pull fails with AccessDenied despite correct IAM permissions
- The repository is KMS-encrypted and the KMS key policy does not grant
  the principal. Verify the key policy includes `kms:Decrypt`,
  `kms:Encrypt`, `kms:GenerateDataKey*`.

### Cross-account access fails with AccessDenied
- Repository resource policy OR KMS key policy is missing the
  cross-account principal. Verify BOTH policies.

### Notification rule created but no notifications fire
- SNS topic policy does not grant `codestar-notifications.amazonaws.com`
  `sns:Publish`. Apply the topic policy and re-test.

### Repository trigger created but Lambda never invoked
- Lambda resource policy does not grant `codecommit.amazonaws.com`
  `lambda:InvokeFunction`. Add the permission.

### Approval rule template created but not enforced on PRs
- Template was not ASSOCIATED with the repository. Run
  `associate-approval-rule-template-with-repository`.

## Domain

AWS CloudOps / AWS CodeCommit Repository Provisioning & Developer Tools
Configuration.

## AWS documentation

- **CodeCommit User Guide** — https://docs.aws.amazon.com/codecommit/latest/userguide/welcome.html
- **KMS encryption** — https://docs.aws.amazon.com/codecommit/latest/userguide/encryption.html
- **Approval rule templates** — https://docs.aws.amazon.com/codecommit/latest/userguide/approval-rule-templates.html
- **Notification rules** — https://docs.aws.amazon.com/dtconsole/latest/userguide/notifications.html
- **Repository triggers** — https://docs.aws.amazon.com/codecommit/latest/userguide/how-to-notify.html
- **git-remote-codecommit** — https://docs.aws.amazon.com/codecommit/latest/userguide/setting-up-git-remote-codecommit.html
- **Cross-account access** — https://docs.aws.amazon.com/codecommit/latest/userguide/cross-account.html
