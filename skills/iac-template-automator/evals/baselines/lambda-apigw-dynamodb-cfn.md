# Baseline (no-skill) response: lambda-apigw-dynamodb-cfn

This file captures what a generic assistant produces WITHOUT the
iac-template-automator skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, security baseline, validation
toolchain, expert IaC reasoning).

---

Here's a CloudFormation template for your serverless app:

```yaml
Transform: AWS::Serverless-2016-10-31
Resources:
  MyFunction:
    Type: AWS::Serverless::Function
    Properties:
      CodeUri: ./src
      Handler: app.handler
      Runtime: python3.12
      Events:
        Api:
          Type: Api
          Properties:
            Path: /items
            Method: ANY
  MyTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: items-table
      AttributeDefinitions:
        - AttributeName: pk
          AttributeType: S
      KeySchema:
        - AttributeName: pk
          KeyType: HASH
      BillingMode: PAY_PER_REQUEST
```

This creates a Lambda function with an API Gateway and a DynamoDB table.
You may want to add IAM permissions for the Lambda to access DynamoDB.
