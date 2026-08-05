# End-to-end usage scenario: codecommit-repository-auditor

A walkthrough showing the skill auditing a CodeCommit repository that has
no approval rule template (NO_APPROVAL_RULE), an AWS-managed KMS key
(NO_ENCRYPTION), no notification rules (CONFIG_GAP), and no branch
protection — demonstrating worst-finding aggregation and the always-present
deprecation risk finding.

## Input (user prompt)

> Audit this CodeCommit repository before we onboard the team. It hosts
> our shared infrastructure-as-code templates.

```
Repository name: iac-templates-repo
Repository metadata:
  repositoryId: a1b2c3d4-9999-9999-9999-000000000001
  defaultBranch: main
  kmsEncryptionKeyId: aws/codecommit
  approvalRuleTemplates: []
  notificationRules: []
  branchProtectionIamPolicies: []
  tags: {}
```

## Skill output

```text
REPO: iac-templates-repo
VERDICT: NO_APPROVAL_RULE
REASON: No approval rule template is linked to this repository — pull
requests can be merged with zero code review (Step 2). The repository also
uses the AWS-managed KMS key, has no notification rules, and no IAM branch
protection on the default branch.
FINDINGS:
  - [NO_APPROVAL_RULE] No approval rule template linked — PRs mergeable
    with 0 approvals (Step 2). Unreviewed infrastructure-as-code changes
    are a direct integrity risk.
  - [NO_ENCRYPTION] kmsEncryptionKeyId is aws/codecommit (AWS-managed) —
    no customer key control (Step 3). KMS key is immutable post-creation.
  - [CONFIG_GAP] No IAM Deny policy on codecommit:DeleteBranch for
    refs/heads/main — default branch is unprotected from deletion (Step 4)
  - [CONFIG_GAP] No notification rules via CodeStar Notifications — no
    alerting on PR creation, merge, or branch deletion events (Step 5)
  - [DEPRECATION_RISK] CodeCommit is in maintenance/deprecation mode —
    evaluate migration to GitHub/GitLab (Step 1, ALWAYS)
REMEDIATION:
  1. Create and link an approval rule template:
     aws codecommit create-approval-rule-template \
       --approval-rule-template-name require-1-approval \
       --approval-rule-template-content '{"Version":"2018-02-08","Statements":[{"Type":"Approvers","NumberOfApprovalsNeeded":1}]}'
     aws codecommit batch-associate-approval-rule-template-with-repositories \
       --approval-rule-template-name require-1-approval \
       --repository-names iac-templates-repo
  2. KMS key cannot be changed post-creation — plan repo migration to a
     CMK-backed repository (or evaluate GitHub/GitLab migration instead).
  3. Add IAM Deny policy for branch protection:
     Deny codecommit:DeleteBranch on refs/heads/main for developer roles.
  4. Create notification rules via CodeStar Notifications:
     aws codestar-notifications create-notification-rule \
       --name iac-pr-alerts \
       --resource arn:aws:codecommit:us-east-1:111111111111:iac-templates-repo \
       --event-type-ids codecommit-pull-request-created codecommit-pull-request-merged \
       --target Type=SNS,TargetArn=<sns-topic-arn>
  5. Evaluate migration to GitHub/GitLab — CodeCommit is deprecated.
```

## Key takeaways demonstrated

1. **Worst-finding aggregation**: Four config dimensions fail
   (NO_APPROVAL_RULE, NO_ENCRYPTION, CONFIG_GAP x2), but the verdict is
   NO_APPROVAL_RULE — the highest-priority finding.

2. **Always-present deprecation finding**: DEPRECATION_RISK appears in
   FINDINGS regardless of the verdict. Even a clean repo would carry it.

3. **Immutability of KMS key**: The NO_ENCRYPTION finding notes that the
   key cannot be changed post-creation — remediation requires repo
   recreation, not a config update.

4. **IAM-based branch protection**: The CONFIG_GAP for branch protection
   references IAM Deny policies, not a CodeCommit-native setting — because
   CodeCommit has no native branch-protection API.

5. **CodeStar Notifications separation**: Notification rules are managed
   via `aws codestar-notifications`, not `aws codecommit` — the remediation
   CLI uses the correct service.
