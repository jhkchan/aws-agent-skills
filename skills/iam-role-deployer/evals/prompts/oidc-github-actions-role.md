# Eval prompt: oidc-github-actions-role

Design a deployment plan for an IAM role. Emit the standard VERDICT block
(ROLE_SPEC, VERDICT, TRUST_POLICY, PERMISSIONS, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- Role name: github-actions-deploy-role
- Principal type: Web Identity (OIDC) via
  `token.actions.githubusercontent.com`
- Owning account: 111111111111
- Scoped to: GitHub repo `my-org/my-repo`, branch `main` only
  (sub condition: `repo:my-org/my-repo:ref:refs/heads/main`)
- Permissions:
  - `s3:PutObject`, `s3:GetObject`, `s3:DeleteObject` on
    `arn:aws:s3:::prod-frontend/*`
  - `cloudformation:CreateChangeSet`, `cloudformation:ExecuteChangeSet`,
    `cloudformation:DescribeStacks` on
    `arn:aws:cloudformation:us-east-1:111111111111:stack/prod-web-*`
  - `iam:PassRole` on
    `arn:aws:iam::111111111111:role/cloudformation-execution-role` only
- Session duration: 3600 seconds (GitHub Actions jobs max ~1 hour)
- The OIDC provider
  `arn:aws:iam::111111111111:oidc-provider/token.actions.githubusercontent.com`
  already exists in the account — do NOT create it.

Additional context: the role should NOT be assumable from pull requests
or other branches — only the main branch.
