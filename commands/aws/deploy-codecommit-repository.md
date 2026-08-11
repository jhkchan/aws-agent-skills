---
description: Provision an AWS CodeCommit repository with production-grade defaults (KMS encryption, approval rule templates, branch protection, notification rules, pull request templates, cross-account access, repository triggers, git-remote-codecommit auth). Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create codecommit repository"
  - "deploy codecommit repository"
  - "codecommit default branch"
  - "codecommit approval rule template"
  - "codecommit branch protection"
  - "codecommit kms encryption"
  - "codecommit notification rule"
  - "codecommit pull request template"
  - "codecommit cross-account"
  - "codecommit trigger"
  - "git-remote-codecommit"
  - "codecommit migration"
  - "codecommit codebuild connection"
routes_to: codecommit-repository-deployer
---

# /aws:deploy-codecommit-repository

Activate the `codecommit-repository-deployer` skill and provision an
AWS CodeCommit repository with production-grade defaults.

## What it does

The skill walks the provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Repository creation and default branch (first-push requirement)
2. KMS encryption with customer-managed key (key policy grants CodeCommit)
3. Approval rule templates and branch protection (IAM deny-push)
4. Notification rules via CodeStar Notifications (SNS topic policy)
5. Pull request templates (file committed to repo)
6. Cross-account access via resource policy + KMS key policy
7. Repository triggers (Lambda/SNS target policy)
8. Authentication: git-remote-codecommit vs git credentials vs SSH
9. Migration from external Git (mirror push)
10. CodeBuild/CodePipeline connection (service role permissions)
11. Recent features (maintenance mode, GRC maturity)

## When to use

- You need to create a CodeCommit repository.
- You need to configure KMS encryption with a customer-managed key.
- You need to set up approval rule templates for branch protection.
- You need notification rules for repository events.
- You need cross-account access to a CodeCommit repository.
- You need to choose between GRC, git credentials, and SSH auth.
- You need to migrate a repository from GitHub/GitLab/Bitbucket.
- You need to connect a repository to CodeBuild or CodePipeline.

## When NOT to use

- **Auditing existing repositories** — use CodeCommit audit skills.
- **GitHub/GitLab repository management** — different services.
- **CodeBuild/CodePipeline pipeline configuration itself** — use
  pipeline-specific skills for build/deploy stages.

## How to invoke

### Slash command

```
/aws:deploy-codecommit-repository
```

Then provide: repository name, default branch, KMS key ID (if
encryption), approval rule template name and approver pool, branch
protection requirements, SNS topic ARN (if notifications), cross-account
principal (if cross-account), auth method preference, tags.

### Natural language

Any of these routes to the same skill:

- "create a codecommit repository with kms encryption"
- "set up approval rule templates for my codecommit repo"
- "configure cross-account codecommit access"
- "migrate my github repo to codecommit"
- "set up git-remote-codecommit for my developers"

### CLI routing

```bash
node cli/bin/cli.js route "create a codecommit repository"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create or
configure CodeCommit repositories. The output checklist feeds into
verification pipelines and downstream audit skills.

## Example

```
You: /aws:deploy-codecommit-repository

     Create a CodeCommit repository named my-app-repo with
     KMS encryption (key abcd-1234), approval rule template
     requiring 2 reviewers, branch protection on main, and
     notification rules for PR events.

Skill:
  CODECOMMIT_REPO: my-app-repo
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] KMS encryption: key abcd-1234 (policy grants codecommit.amazonaws.com)
    [✓] Approval rule template: require-two-reviewers (associated)
    [✓] Branch protection: IAM denies direct push to main
    [✓] Notification rule: PR events → SNS (topic policy grants CodeStar)
  VERIFICATION_COMMANDS:
    aws codecommit get-repository --repository-name my-app-repo --region us-east-1
    aws kms describe-key --key-id abcd-1234 --region us-east-1
```

## References

- Skill definition: `skills/codecommit-repository-deployer/SKILL.md`
- Approval rules and protection guide: `skills/codecommit-repository-deployer/references/approval-rules-and-protection.md`
- Auth and cross-account guide: `skills/codecommit-repository-deployer/references/auth-and-cross-account.md`
- Eval suite: `skills/codecommit-repository-deployer/evals/evals.json`
