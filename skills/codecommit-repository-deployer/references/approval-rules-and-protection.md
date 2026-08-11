# Approval Rules and Branch Protection — CodeCommit Repository Deployer

Deep reference on approval rule template lifecycle (create, associate,
override), branch protection via IAM policy (deny direct GitPush),
pull request template configuration, and the distinction between
approval rules (govern PR merges) and branch protection (governs
direct pushes). Loaded on demand by the skill — kept out of the main
SKILL.md body so the provisioning procedure stays scannable.

## Approval rule template lifecycle

### Create the template

An approval rule template is a server-side configuration that defines
how many approvals are required and who can approve. The template
exists independently of any repository.

```bash
aws codecommit create-approval-rule-template \
  --approval-rule-template-name "require-two-reviewers" \
  --approval-rule-template-content '{
    "Version": "2018-02-08",
    "Statements": [{
      "Type": "Approvers",
      "NumberOfApprovalsNeeded": 2,
      "ApprovalPoolMembers": [
        "arn:aws:iam::123456789012:user/alice",
        "arn:aws:iam::123456789012:user/bob",
        "arn:aws:iam::123456789012:role/developer-role"
      ]
    }]
  }'
```

### Associate the template with a repository

Creating the template does NOTHING until it is associated with a
repository. After association, the rule is automatically applied to
ALL pull requests in that repository.

```bash
aws codecommit associate-approval-rule-template-with-repository \
  --approval-rule-template-name "require-two-reviewers" \
  --repository-name "my-app-repo"
```

### Override (grant sparingly)

An IAM principal with `codecommit:OverridePullRequestApprovalRules`
can bypass the approval requirement. Grant this permission to a
break-glass role, not to all developers.

```json
{
  "Effect": "Allow",
  "Action": "codecommit:OverridePullRequestApprovalRules",
  "Resource": "arn:aws:codecommit:us-east-1:123456789012:my-app-repo"
}
```

## Branch protection via IAM policy

Approval rules govern pull request merges. Branch protection —
preventing direct pushes to a branch — requires a SEPARATE IAM policy.

### Deny direct push to main

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DenyDirectPushToMain",
      "Effect": "Deny",
      "Action": "codecommit:GitPush",
      "Resource": "arn:aws:codecommit:us-east-1:123456789012:my-app-repo",
      "Condition": {
        "StringEquals": {
          "codecommit:References": ["refs/heads/main"]
        }
      }
    }
  ]
}
```

Attach this policy to developer IAM roles/groups. This forces them to
create a branch, open a pull request, and go through the approval rule
template before merging to main.

### Full protection = approval rules + branch protection

| Layer | What it protects | Mechanism |
|---|---|---|
| Approval rule template | PR merge without required approvals | Server-side rule on pull requests |
| Branch protection IAM policy | Direct push to protected branch | IAM Deny on codecommit:GitPush |
| Both together | Full enforcement of PR-based workflow | Approval rules + branch protection |

## Pull request templates

A pull request template is a markdown file committed to the repository.
When a developer creates a PR, the template content pre-populates the
description field.

### Standard template path

The conventional paths are:
- `.github/PULL_REQUEST_TEMPLATE.md`
- `PULL_REQUEST_TEMPLATE.md` (root)
- `.CODEBUILD/pull_request_template.md`

### Register the template path

The template path is registered in repository metadata. After
committing the file:

```bash
# The template path can be configured via the console or via
# update-approval-rule-template-content (not directly on the repo).
# In practice, committing the file to .github/PULL_REQUEST_TEMPLATE.md
# is sufficient for CodeCommit to surface it on new PRs.
```

## Common governance pitfalls

### Pitfall 1: Template created but not associated

The #1 approval-rule mistake. The template exists but was never
associated with the repository. PRs can be merged without approvals.

**Fix:** Verify association:

```bash
aws codecommit list-approval-rule-templates-for-repository \
  --repository-name "my-app-repo"
```

### Pitfall 2: Branch protection without approval rules

Branch protection prevents direct pushes but does NOT enforce approvals
on PRs. Developers can open a PR and self-merge without review.

**Fix:** Configure BOTH branch protection AND approval rule templates.

### Pitfall 3: Override permission too broad

Granting `codecommit:OverridePullRequestApprovalRules` to all
developers defeats the purpose of approval rules.

**Fix:** Restrict the override permission to a break-glass role.

## Terraform examples

```hcl
# Approval rule template
resource "aws_codecommit_approval_rule_template" "two_reviewers" {
  name = "require-two-reviewers"
  content = jsonencode({
    Version = "2018-02-08"
    Statements = [{
      Type = "Approvers"
      NumberOfApprovalsNeeded = 2
      ApprovalPoolMembers = [
        "arn:aws:iam::123456789012:user/alice",
        "arn:aws:iam::123456789012:user/bob"
      ]
    }]
  })
}

# Associate with repository
resource "aws_codecommit_approval_rule_template_association" "repo" {
  approval_rule_template_name = aws_codecommit_approval_rule_template.two_reviewers.name
  repository_name             = aws_codecommit_repository.repo.repository_name
}

# Branch protection via IAM policy
resource "aws_iam_policy" "deny_push_main" {
  name = "deny-direct-push-main"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Deny"
      Action = "codecommit:GitPush"
      Resource = aws_codecommit_repository.repo.arn
      Condition = {
        StringEquals = {
          "codecommit:References" = ["refs/heads/main"]
        }
      }
    }]
  })
}
```
