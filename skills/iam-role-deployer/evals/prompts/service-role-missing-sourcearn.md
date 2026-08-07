# Eval prompt: service-role-missing-sourcearn

Design a deployment plan for an IAM role. Emit the standard VERDICT block
(ROLE_SPEC, VERDICT, TRUST_POLICY, PERMISSIONS, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- Role name: shared-lambda-role
- Principal type: AWS service (lambda.amazonaws.com)
- Trust policy: `Principal: {"Service": "lambda.amazonaws.com"}` with
  NO condition keys (the caller did not specify SourceArn or SourceAccount)
- Permissions:
  - `s3:GetObject` on `arn:aws:s3:::sensitive-data/*`
  - `dynamodb:Scan` on all tables in account 111111111111
- Intended for ONE specific Lambda function:
  `arn:aws:lambda:us-east-1:111111111111:function:my-app-processor`
- MFA: not required (service role)

Additional context: the account has 15 Lambda functions across multiple
applications. The role is intended ONLY for `my-app-processor` but the
caller has not added any conditions to the trust policy.
