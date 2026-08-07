# Eval prompt: enable-rotation-rds-postgres-ready

Plan the following Secrets Manager rotation enable operation and emit the
standard VERDICT block (OPERATION, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, NOTES).

Operation: enable-rotation
Secret: prod/payments-db-credentials
Target rotation Lambda: arn:aws:lambda:us-east-1:111111111111:function:SecretsManagerRDSPostgreSQLRotation
Schedule: AutomaticallyAfterDays=30
Rotate immediately on enable: yes

```json
{
  "SecretMetadata": {
    "Name": "prod/payments-db-credentials",
    "RotationEnabled": false,
    "KmsKeyId": "arn:aws:kms:us-east-1:111111111111:key/payments-cmk",
    "OwningService": "rds",
    "PrimaryRegion": null,
    "DeletedDate": null
  },
  "LambdaMetadata": {
    "FunctionName": "SecretsManagerRDSPostgreSQLRotation",
    "State": "Active",
    "Runtime": "python3.12",
    "Timeout": 30,
    "Role": "arn:aws:iam::111111111111:role/service-role/SecretsManagerRDSPostgreSQLRotationRole",
    "ReservedConcurrentExecutions": 5,
    "VpcConfig": {
      "SubnetIds": ["subnet-aaa", "subnet-bbb"],
      "SecurityGroupIds": ["sg-lambda-rotation"]
    }
  },
  "LambdaResourcePolicy": {
    "Allows": "Principal: secretsmanager.amazonaws.com, Action: lambda:InvokeFunction, SourceArn: arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/payments-db-credentials-??????"
  },
  "IamRolePolicies": [
    "SecretsManagerRotation",
    "AWSLambdaVPCAccessExecutionRole",
    "rds-db:connect on arn:aws:rds-db:us-east-1:111111111111:dbuser:db-ABCDEFGHIJKLMNOP/postgres",
    "kms:Decrypt on arn:aws:kms:us-east-1:111111111111:key/payments-cmk"
  ],
  "NetworkChecks": {
    "DbSgIngress": "sg-rds-prod allows sg-lambda-rotation on port 5432",
    "Routing": "Lambda subnets route to DB subnets via VPC route table"
  }
}
```
