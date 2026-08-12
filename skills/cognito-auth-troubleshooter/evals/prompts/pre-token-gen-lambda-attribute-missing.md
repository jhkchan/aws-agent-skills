# Eval prompt: pre-token-gen-lambda-attribute-missing

Diagnose the Cognito authentication failure for the following User Pool.
Walk the symptom-driven diagnostic tree and emit the standard diagnostic
block (TARGET, VERDICT, REASON, LAYER, EVIDENCE, REMEDIATION).

Symptom: no user can sign in. All return
`UserLambdaValidationException`. The error message contains
`TypeError: Cannot read property 'department' of undefined`.

```text
UserPoolId: us-east-1_PrQsTu456
AppClientId: 2bc3de4fg5hi6jk7lmn8opq9st
LambdaConfig:
  PreTokenGeneration: arn:aws:lambda:us-east-1:111111111111:
    function:pre-token-gen-fn:live

CloudWatch logs (/aws/lambda/pre-token-gen-fn, last 30 min):
  ERROR  TypeError: Cannot read property 'department'
    of undefined
    at exports.handler (/var/task/index.js:12:38)
  (repeated 200 times in the last hour)

Lambda handler code (relevant lines):
  const dept = event.request.userAttributes['custom:department'];
  const claims = { 'custom:dept': dept.value };

User attributes (admin-get-user for test user):
  custom:department: (attribute not present)
```

The pre-token-generation Lambda reads `custom:department` from the
user attributes and calls `.value` on it. When the attribute is absent,
`dept` is `undefined` and `.value` throws `TypeError`. This blocks the
entire auth flow for any user missing the attribute.
