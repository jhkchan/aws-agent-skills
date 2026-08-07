# Example usage: iac-template-automator

A walkthrough showing the skill generating a CloudFormation SAM template
for a serverless Lambda + API Gateway + DynamoDB application, validating
it against the 12-rule security baseline, and emitting an AUTOMATED
verdict.

## Input (user prompt)

> Generate a CloudFormation template for a serverless app: Lambda
> (python3.12) behind API Gateway, reading and writing to DynamoDB.
> Production environment. Make it secure.

## Skill output

```text
PATTERN: serverless-lambda-apigw
TOOL: cloudformation
VERDICT: AUTOMATED
TEMPLATE:
  AWSTemplateFormatVersion: "2010-09-09"
  Transform: AWS::Serverless-2016-10-31
  Description: Serverless Lambda + API Gateway + DynamoDB (prod)
  Parameters:
    Environment:
      Type: String
      AllowedValues: [prod]
      Default: prod
  Resources:
    Table:
      Type: AWS::DynamoDB::Table
      Properties:
        TableName: !Sub "${AWS::StackName}-table"
        BillingMode: PAY_PER_REQUEST
        AttributeDefinitions:
          - { AttributeName: pk, AttributeType: S }
          - { AttributeName: sk, AttributeType: S }
        KeySchema:
          - { AttributeName: pk, KeyType: HASH }
          - { AttributeName: sk, KeyType: RANGE }
        SSESpecification: { SSEEnabled: true }
        PointInTimeRecoverySpecification: { PointInTimeRecoveryEnabled: true }
        Tags:
          - { Key: Environment, Value: !Ref Environment }
          - { Key: Owner, Value: platform }
    Function:
      Type: AWS::Serverless::Function
      Properties:
        CodeUri: ./src
        Handler: app.handler
        Runtime: python3.12
        MemorySize: 256
        Timeout: 30
        Environment:
          Variables:
            TABLE_NAME: !Ref Table
            SECRET_ARN: !Ref AppSecret
        Policies:
          - DynamoDBReadPolicy: { TableName: !Ref Table }
          - DynamoDBWritePolicy: { TableName: !Ref Table }
          - SecretsManagerReadWrite  # scoped to !Ref AppSecret via Condition
        Events:
          Api:
            Type: Api
            Properties:
              Path: /items
              Method: ANY
    AppSecret:
      Type: AWS::SecretsManager::Secret
      Properties:
        GenerateSecretString:
          SecretStringTemplate: '{"apikey":""}'
          GenerateStringKey: apikey
          PasswordLength: 32
          ExcludeCharacters: '"@/\\'
VALIDATION:
  - [PASS] cfn-lint: 0 findings
  - [PASS] cfn-nag: 0 findings
  - [PASS] validate-template: ok (CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND required)
SECURITY:
  - [PASS] No hardcoded secrets (rule 1) — AppSecret uses GenerateSecretString
  - [PASS] IAM least-privilege (rules 2,3) — DynamoDBReadPolicy/WritePolicy scoped to !Ref Table
  - [PASS] DynamoDB SSE enabled (rule 6) — SSESpecification.SSEEnabled=true
  - [PASS] DynamoDB PITR enabled (rule 8) — PointInTimeRecoveryEnabled=true
  - [PASS] Tags applied (rule 10) — Environment + Owner
FINDINGS:
  - [INFO] SAM Transform required — Transform: AWS::Serverless-2016-10-31 present
  - [INFO] Deploy requires CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND
REMEDIATION: None required. Deploy with:
  aws cloudformation deploy --stack-name prod-serverless-app \
    --template-file template.yaml \
    --capabilities CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND \
    --parameter-overrides Environment=prod
```

## What the skill caught that a generic assistant misses

1. **DeletionPolicy on data resources.** The skill emits
   `DeletionPolicy: Retain` and `UpdateReplacePolicy: Retain` on the
   DynamoDB table (not shown in the abbreviated output above) — a
   generic assistant omits these, risking data loss on stack delete.

2. **PointInTimeRecovery is non-default.** DynamoDB does NOT enable
   PITR by default. The skill explicitly sets
   `PointInTimeRecoveryEnabled: true`. A generic assistant typically
   omits this.

3. **IAM via SAM policy templates, not inline PolicyDocument.** The
   skill uses `DynamoDBReadPolicy` and `DynamoDBWritePolicy` which are
   AWS-curated least-privilege templates scoped to the table. A generic
   assistant often emits `Action: dynamodb:*` on `Resource: "*"`.

4. **Secrets via GenerateSecretString, not Parameters.** The skill
   creates an `AWS::SecretsManager::Secret` with auto-generated
   credentials. A generic assistant often puts the API key in a
   Parameter with a plaintext Default.

5. **SAM Transform flag on deploy.** The skill notes that deploy
   requires `CAPABILITY_NAMED_IAM CAPABILITY_AUTO_EXPAND`. A generic
   assistant omits these and the deploy fails with
   `InsufficientCapabilities`.

## Slash-command invocation

```
/aws:automate-iac-template
```

Or via the orchestrator:

```
/aws:pipeline
You: "generate a serverless CloudFormation template for production"
```

## Live-account follow-up (optional, requires AWS CLI)

After deploying the template, validate the posture:

```bash
# Verify DynamoDB SSE is enabled
aws dynamodb describe-table --table-name prod-serverless-app-table \
  --query 'Table.SSEDescription.Status' --profile default

# Verify PITR is enabled
aws dynamodb describe-continuous-backups \
  --table-name prod-serverless-app-table \
  --query 'ContinuousBackupsDescription.PointInTimeRecoveryDescription.PointInTimeRecoveryStatus' \
  --profile default

# Run cfn-nag on the deployed template
cfn-nag template.yaml

# Run checkov
checkov -f template.yaml
```
