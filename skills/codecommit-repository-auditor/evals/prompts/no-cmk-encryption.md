# Eval prompt: no-cmk-encryption

Audit the following CodeCommit repository configuration for security and
config gaps. Emit the standard VERDICT block (REPO, VERDICT, REASON,
FINDINGS, REMEDIATION).

Repository name: no-cmk-encryption
Repository metadata:
  repositoryId: a1b2c3d4-0002-0002-0002-000000000002
  defaultBranch: main
  kmsEncryptionKeyId: aws/codecommit
  approvalRuleTemplates:
    - name: require-2-approvals
      content:
        Version: "2018-02-08"
        Statements:
          - Type: Approvers
            NumberOfApprovalsNeeded: 2
  notificationRules: []
  branchProtectionIamPolicies:
    - effect: Deny
      action: codecommit:DeleteBranch
      condition: codecommit:References = refs/heads/main
  tags: {}
