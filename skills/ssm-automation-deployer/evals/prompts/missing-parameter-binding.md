# Eval: missing-parameter-binding

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — step references {{ UndefinedParam }} which is not declared in parameters

## Prompt

Create an SSM Automation document "BadRunbook" that: 1) Uses
aws:executeAwsApi to call ec2:DescribeInstances with parameter
{{ UndefinedParam }}. The parameter UndefinedParam is not
declared in the parameters section. 2) Uses aws:changeInstanceState.
Execution role: SSMAutomationRole. Schema 0.3. Region us-east-1.
