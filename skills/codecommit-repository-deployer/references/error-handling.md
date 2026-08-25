# Error Handling — CodeCommit Repository Deployer

Load-on-demand error-handling detail moved verbatim from SKILL.md.

## Provisioning failure symptoms

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
