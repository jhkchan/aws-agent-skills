# Eval: missing-execution-role-trust

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — execution role MyEC2Role does not have ssm.amazonaws.com in trust policy

## Prompt

Create an SSM Automation document "RemediateEC2" with steps
using aws:executeAwsApi and aws:changeInstanceState. Execution
role: MyEC2Role (this is an EC2 instance profile role, NOT an
automation assume role — it does not have ssm.amazonaws.com in
its trust policy). Targets via resource group rg-prod-ec2.
Schema 0.3. Region us-east-1.
