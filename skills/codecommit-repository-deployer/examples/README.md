# End-to-End Example: CodeCommit Repository Deployment

A walkthrough showing how to use the `codecommit-repository-deployer`
skill from invocation through verification. Mirrors the structured-eval
pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning a CodeCommit repository for a microservice with
KMS encryption, an approval rule template for branch protection,
notification rules, and git-remote-codecommit (GRC) for developer
authentication. The repository needs:

- Repository name: my-app-repo
- Default branch: main
- KMS encryption: customer-managed key (abcd-1234)
- Approval rule template: require-two-reviewers (2 approvals)
- Branch protection: deny direct push to main
- Notification rule: PR events to SNS
- Auth: GRC for developers, IAM git credentials for CI
- Region: us-east-1
- Account: 123456789012

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-codecommit-repository
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a CodeCommit repository named my-app-repo with
      KMS encryption, approval rules requiring 2 reviewers,
      branch protection on main, and notification rules for
      PR events."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a codecommit repository"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CODECOMMIT_REPO: my-app-repo (arn:aws:codecommit:us-east-1:123456789012:my-app-repo)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Repository name: my-app-repo (unique in account 123456789012 us-east-1)
  [✓] Default branch: main (created at first push)
  [✓] Description: Microservice repository for my-app
  [✓] KMS encryption: customer-managed key abcd-1234 (policy grants codecommit.amazonaws.com)
  [✓] Approval rule template: require-two-reviewers (associated, 2 approvals from pool)
  [✓] Branch protection: IAM policy denies direct push to main
  [✓] Notification rule: PR events → SNS arn:aws:sns:us-east-1:123456789012:codecommit-notifications (topic policy grants codestar-notifications.amazonaws.com)
  [✓] Pull request template: .github/PULL_REQUEST_TEMPLATE.md (committed to repo)
  [✓] Auth method: git-remote-codecommit (GRC) for developers, IAM git credentials for CI
  [✓] Tags: Environment=production, Team=platform
VERIFICATION_COMMANDS:
  aws codecommit get-repository --repository-name my-app-repo --region us-east-1
  aws kms describe-key --key-id abcd-1234 --region us-east-1
  aws codecommit list-approval-rule-templates --region us-east-1
  aws codestar-notifications list-notification-rules --region us-east-1
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the repository
REPO_ARN=$(aws codecommit create-repository \
  --repository-name my-app-repo \
  --repository-description "Microservice repository for my-app" \
  --tags Environment=production,Team=platform \
  --query 'repositoryMetadata.Arn' --output text \
  --region us-east-1)

# Step 2: Verify the KMS key policy grants CodeCommit
aws kms get-key-policy --key-id abcd-1234 \
  --policy-name default --region us-east-1

# Step 3: Create and associate the approval rule template
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

aws codecommit associate-approval-rule-template-with-repository \
  --approval-rule-template-name "require-two-reviewers" \
  --repository-name "my-app-repo" --region us-east-1

# Step 4: Create the SNS topic and set its policy for CodeStar Notifications
TOPIC_ARN=$(aws sns create-topic \
  --name "codecommit-notifications" \
  --query 'TopicArn' --output text --region us-east-1)

aws sns set-topic-attributes \
  --topic-arn "$TOPIC_ARN" \
  --attribute-name Policy \
  --attribute-value '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Principal": { "Service": "codestar-notifications.amazonaws.com" },
      "Action": "sns:Publish",
      "Resource": "'"$TOPIC_ARN"'"
    }]
  }'

# Step 5: Create the notification rule
aws codestar-notifications create-notification-rule \
  --name "my-app-pr-notifications" \
  --resource "$REPO_ARN" \
  --event-type-ids pull-request-created pull-request-updated pull-request-merged \
  --targets '[{"Id":"'"$TOPIC_ARN"'"}]' \
  --detail-type FULL --region us-east-1

# Step 6: Push the initial commit (GRC)
pip install git-remote-codecommit
git init && git remote add origin codecommit://us-east-1@my-app-repo
echo "# my-app" > README.md
git add . && git commit -m "initial commit"
git push -u origin main
```

---

## Step 4 — Post-deployment verification

```bash
# Repository exists and is configured
aws codecommit get-repository \
  --repository-name my-app-repo --region us-east-1

# KMS key policy includes CodeCommit service principal
aws kms get-key-policy --key-id abcd-1234 \
  --policy-name default --region us-east-1 \
  --query 'Policy' --output text | jq '.Statement[] | select(.Principal.Service=="codecommit.amazonaws.com")'

# Approval rule template is associated
aws codecommit list-approval-rule-templates-for-repository \
  --repository-name my-app-repo --region us-east-1

# Notification rule exists
aws codestar-notifications list-notification-rules \
  --region us-east-1
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| KMS key policy | Not verified | Verifies codecommit.amazonaws.com grant | Without it, push/pull fails with AccessDenied |
| Approval rule template | Created but not associated | Explicitly associates with repository | Template alone does nothing; must be linked |
| Branch protection | Not configured | IAM deny-push policy on main | Forces PR workflow; prevents direct pushes |
| Notification SNS policy | Not set | Topic policy grants codestar-notifications | Without it, notifications never fire |
| Auth method | Defaults to static credentials | GRC for SSO, static for CI | GRC eliminates credential rotation for federated users |
| Default branch | Assumed to exist | Notes first-push requirement | Branch does not exist until first commit |

---

## Related artifacts

- **Skill definition:** `skills/codecommit-repository-deployer/SKILL.md`
- **Approval rules and protection guide:** `skills/codecommit-repository-deployer/references/approval-rules-and-protection.md`
- **Auth and cross-account guide:** `skills/codecommit-repository-deployer/references/auth-and-cross-account.md`
- **Slash command:** `commands/aws/deploy-codecommit-repository.md`
- **Eval suite:** `skills/codecommit-repository-deployer/evals/evals.json`
- **Legacy test cases:** `skills/codecommit-repository-deployer/eval/test-cases.yaml`
