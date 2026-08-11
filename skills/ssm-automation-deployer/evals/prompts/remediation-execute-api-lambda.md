# Eval: remediation-execute-api-lambda

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — remediation runbook with aws:executeAwsApi, aws:changeInstanceState, aws:invokeLambdaFunction, resource group targets, rate control, SNS notifications

## Prompt

Create an SSM Automation document "RemediateEC2" that:
1) Uses aws:executeAwsApi to call ec2:DescribeInstances for a
given InstanceId parameter. 2) Uses aws:changeInstanceState to
stop the instance if running. 3) Uses aws:invokeLambdaFunction
to invoke "remediation-handler" with the instance ID. Targets
via resource group "rg-prod-ec2". Rate control: MaxConcurrency
10, MaxErrors 3. Execution role: SSMAutomationRole (trust
ssm.amazonaws.com). SNS notification on Success and Failed to
arn:aws:sns:us-east-1:123456789012:ssm-alerts. Schema version
0.3. Region us-east-1.
