# Eval prompt: lambda-service-role-scoped

Design a deployment plan for an IAM role. Emit the standard VERDICT block
(ROLE_SPEC, VERDICT, TRUST_POLICY, PERMISSIONS, CHECKLIST, FINDINGS,
DEPLOY_COMMANDS).

Requirements:

- Role name: my-app-lambda-role
- Principal type: AWS service (lambda.amazonaws.com)
- Scoped to: functions matching
  `arn:aws:lambda:us-east-1:111111111111:function:my-app-*`
- Owning account: 111111111111
- Permissions:
  - CloudWatch Logs via AWSLambdaBasicExecutionRole managed policy
  - s3:GetObject on `arn:aws:s3:::prod-data/*`
  - dynamodb:PutItem on
    `arn:aws:dynamodb:us-east-1:111111111111:table/prod-table`
- Session duration: default (1 hour, auto-renewed by Lambda service)
- MFA: not required (service role — Lambda does not present MFA)

Additional context: the account has 15 other Lambda functions. The role
must ONLY be assumable by functions in the `my-app-*` family, not the
other 15 functions.
