# Worked Examples — CodeCommit Repository Deployer

Load-on-demand worked examples moved verbatim from SKILL.md.

## Worked example — PREREQUISITES_MISSING (KMS key policy not granted)

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
