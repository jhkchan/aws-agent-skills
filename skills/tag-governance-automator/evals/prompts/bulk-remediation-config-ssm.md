# Eval prompt: bulk-remediation-config-ssm

Design an automated remediation flow: Config required-tags rule
detects EC2 instances missing required tags, a custom SSM Automation
runbook adds placeholder tags, Config re-evaluates and the resource
flips COMPLIANT. Emit the standard GOVERNANCE block (SCOPE, STRATEGY,
POLICY, AUTOMATION, COMPLIANCE, VERDICT, GAP, TEMPLATE).

Design reference: bulk-remediation-config-ssm
Account: 111111111111
Region: us-east-1

Config rule name: required-tags-core
Target resource type: AWS::EC2::Instance
Required tag keys: Environment, Owner, Project, CostCenter.
Custom SSM Automation document: Custom-AddRequiredTagsEC2
Placeholder values: Environment=unknown, Owner=platform-team,
Project=unassigned, CostCenter=cc-9999.
SSM service role ARN:
  arn:aws:iam::111111111111:role/aws-service-role/AmazonSSMAutomationRole/AWS-SSM-AutomationExecutionRole

Config recorder is enabled and includes AWS::EC2::Instance.
Pre-prod validation: completed (3 instances tested, all flipped to
COMPLIANT after remediation).

Include the Config rule CLI, the custom SSM document YAML, and the
put-remediation-configurations CLI. Flag the placeholder-value
caveat.
