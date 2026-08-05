# Eval prompt: config-gap-no-notifications

Audit the following CodeCommit repository configuration for security and
config gaps. Emit the standard VERDICT block (REPO, VERDICT, REASON,
FINDINGS, REMEDIATION).

Repository name: config-gap-no-notifications
Repository metadata:
  repositoryId: a1b2c3d4-0003-0003-0003-000000000003
  defaultBranch: main
  kmsEncryptionKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-repo-key-003
  approvalRuleTemplates:
    - name: require-1-approval
      content:
        Version: "2018-02-08"
        Statements:
          - Type: Approvers
            NumberOfApprovalsNeeded: 1
  notificationRules: []
  branchProtectionIamPolicies:
    - effect: Deny
      action: codecommit:DeleteBranch
      condition: codecommit:References = refs/heads/main
  tags: {}
