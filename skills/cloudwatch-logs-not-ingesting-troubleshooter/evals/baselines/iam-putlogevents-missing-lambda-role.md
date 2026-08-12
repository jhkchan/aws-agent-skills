# Baseline (no-skill) response: iam-putlogevents-missing-lambda-role

---

Your Lambda function is running but no logs are showing up. This is
likely because the execution role doesn't have permission to write to
CloudWatch Logs. Make sure the role has the
`AWSLambdaBasicExecutionRole` managed policy attached, which includes
`logs:CreateLogGroup`, `logs:CreateLogStream`, and `logs:PutLogEvents`.

```
aws iam attach-role-policy --role-name fn-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

Re-invoke the function and the log group should be created
automatically.
