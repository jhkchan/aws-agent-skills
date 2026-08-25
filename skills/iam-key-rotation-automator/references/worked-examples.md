# Worked Examples — IAM Key Rotation Automator

Secondary worked example (REVIEW_REQUIRED) and the Appendix C CloudFormation skeleton moved verbatim from SKILL.md. Loaded on demand.

## Worked example — REVIEW_REQUIRED

```text
ROTATION: break-glass-key
USER: break-glass-admin
KEY: AKIABREAK789
CLASSIFICATION:
  - Age: 365 days
  - Last used: 45 days ago (during incident)
  - Status: Active
  - Exception: Yes
DETECTION:
  - Credential report: generated today
  - Access advisor: last used 45 days ago (STS, IAM)
  - EventBridge scan: flagged but skipped (exception)
ROTATION_FLOW:
  - N/A — break-glass exception
OVERLAP: N/A
NOTIFICATION:
  - SNS: exception review notice sent to security-team
EXCEPTIONS:
  - Break-glass list: /iam-key-rotation/exceptions
  - User excepted: Yes (Emergency access, owner: security-team)
AUDIT:
  - CloudTrail: iam.amazonaws.com tracking
VERDICT: REVIEW_REQUIRED
GAP: Break-glass account on exception list. Key is 365 days old but exempted. Required: (1) Manual review by security-team; (2) evaluate STS assume-role with MFA instead of permanent key; (3) if permanent key still required, manually rotate and update break-glass procedure; (4) set review date.
TEMPLATE: (manual rotation — break-glass accounts require human approval)
```

## Appendix C — CloudFormation skeleton

```yaml
AWSTemplateFormatVersion: '2010-09-09'
Description: 'IAM Access Key Rotation Automation Pipeline'
Resources:
  KeyRotationTopic:
    Type: AWS::SNS::Topic
    Properties: {TopicName: key-rotation-alerts}
  RotationRole:
    Type: AWS::IAM::Role
    Properties:
      AssumeRolePolicyDocument:
        Version: '2012-10-17'
        Statement: [{Effect: Allow, Principal: {Service: lambda.amazonaws.com}, Action: sts:AssumeRole}]
      ManagedPolicyArns: [arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole]
      Policies:
        - PolicyName: IAMKeyMgmt
          PolicyDocument:
            Version: '2012-10-17'
            Statement:
              - {Effect: Allow, Action: [iam:ListAccessKeys, iam:CreateAccessKey, iam:UpdateAccessKey, iam:DeleteAccessKey, iam:GetAccessKeyLastUsed, iam:ListUsers, iam:GetUser], Resource: '*'}
              - {Effect: Allow, Action: [secretsmanager:PutSecretValue, secretsmanager:GetSecretValue], Resource: '*'}
              - {Effect: Allow, Action: [ssm:GetParameter], Resource: '*'}
              - {Effect: Allow, Action: [sns:Publish], Resource: !Ref KeyRotationTopic}
              - {Effect: Allow, Action: sts:GetCallerIdentity, Resource: '*'}
  RotationFunction:
    Type: AWS::Lambda::Function
    Properties:
      FunctionName: iam-key-rotation
      Runtime: python3.12
      Handler: index.lambda_handler
      Role: !GetAtt RotationRole.Arn
      Timeout: 300
      Environment: {Variables: {SNS_TOPIC_ARN: !Ref KeyRotationTopic, ROTATION_AGE_DAYS: '90', OVERLAP_DAYS: '7', EXCEPTION_PARAM: '/iam-key-rotation/exceptions'}}
      Code: {ZipFile: 'import boto3,os,json,datetime\niam=boto3.client("iam")\nsns=boto3.client("sns")\nssm=boto3.client("ssm")\ndef lambda_handler(e,c):\n  try:\n    exc=json.loads(ssm.get_parameter(Name=os.environ["EXCEPTION_PARAM"])["Parameter"]["Value"])\n  except: exc={}\n  for u in iam.list_users()["Users"]:\n    if u["UserName"] in exc: continue\n    for k in iam.list_access_keys(UserName=u["UserName"])["AccessKeyMetadata"]:\n      age=(datetime.datetime.now(datetime.timezone.utc)-k["CreateDate"]).days\n      if age>=int(os.environ["ROTATION_AGE_DAYS"]) and k["Status"]=="Active":\n        sns.publish(TopicArn=os.environ["SNS_TOPIC_ARN"],Subject=f"Key rotation: {u[\"UserName\"]}",Message=f"Key {k[\"AccessKeyId\"]} is {age} days old")'}
  DailyRule:
    Type: AWS::Events::Rule
    Properties:
      ScheduleExpression: rate(1 day)
      State: ENABLED
      Targets: [{Id: key-rotation, Arn: !GetAtt RotationFunction.Arn, DeadLetterConfig: {Arn: !GetAtt RotationDLQ.Arn}}]
  RotationDLQ:
    Type: AWS::SQS::Queue
    Properties: {QueueName: key-rotation-dlq}
  InvokePermission:
    Type: AWS::Lambda::Permission
    Properties:
      FunctionName: !Ref RotationFunction
      Action: lambda:InvokeFunction
      Principal: events.amazonaws.com
      SourceArn: !GetAtt DailyRule.Arn
```
