# Eval prompt: deploy-custom-lambda-rule-ready

Plan the following AWS Config rule creation and emit the standard
VERDICT block (RULE, VERDICT, TARGET, PRE_CHECKS, STEPS,
POST_VERIFY, EVALUATION, COMPLIANCE, REMEDIATION, NOTES).

Operation: create
Rule name: ec2-required-tags
Type: custom
LambdaFunction: arn:aws:lambda:us-east-1:111111111111:function:config-rule-required-tags
Scope: AWS::EC2::Instance
InputParameters: {"requiredTags": "Environment,Owner,CostCenter"}
EvaluationMode: configuration-change
Region: us-east-1
Account: 111111111111

```json
{
  "RecorderChecks": {
    "describe-configuration-recorders": {
      "recorder": "default",
      "recording": true,
      "allSupported": true
    },
    "describe-delivery-channels": {
      "channel": "default",
      "s3BucketName": "config-bucket-111111111111",
      "bucketExists": true
    }
  },
  "LambdaChecks": {
    "get-function.config-rule-required-tags": {
      "status": "OK",
      "runtime": "python3.12",
      "timeout": 30,
      "role": "arn:aws:iam::111111111111:role/config-rule-lambda-role"
    },
    "get-policy.config-rule-required-tags": {
      "hasConfigPermission": true,
      "statementId": "AllowConfigToInvoke",
      "principal": "config.amazonaws.com",
      "sourceAccount": "111111111111"
    },
    "iam-role.config-rule-lambda-role.hasPutEvaluations": true
  },
  "RuleChecks": {
    "describe-config-rules.count": 13
  },
  "ExistingRule": null
}
```
