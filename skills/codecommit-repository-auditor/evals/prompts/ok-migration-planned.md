# Eval prompt: ok-migration-planned

Audit the following CodeCommit repository configuration for security and
config gaps. Emit the standard VERDICT block (REPO, VERDICT, REASON,
FINDINGS, REMEDIATION).

Repository name: ok-migration-planned
Repository metadata:
  repositoryId: a1b2c3d4-0005-0005-0005-000000000005
  defaultBranch: main
  kmsEncryptionKeyId: arn:aws:kms:us-east-1:111111111111:key/cmk-repo-key-005
  approvalRuleTemplates:
    - name: require-1-approval
      content:
        Version: "2018-02-08"
        Statements:
          - Type: Approvers
            NumberOfApprovalsNeeded: 1
  notificationRules:
    - name: pr-alerts
      target: arn:aws:sns:us-east-1:111111111111:codecommit-alerts
      eventTypes: [codecommit-pull-request-created, codecommit-pull-request-merged]
  branchProtectionIamPolicies:
    - effect: Deny
      action: codecommit:DeleteBranch
      condition: codecommit:References = refs/heads/main
  tags:
    migration-plan: active
    migration-target: github
