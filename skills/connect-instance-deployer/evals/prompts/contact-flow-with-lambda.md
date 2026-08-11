# Eval: contact-flow-with-lambda

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — InvokeLambda block with FunctionARN for lookup-customer, Lambda.AccessDenied and Lambda.Timeout exceptions handled via transfer to default queue, Lambda resource policy granting connect.amazonaws.com invoke permission explicitly cited

## Prompt

Create an Amazon Connect contact flow on instance inst-abc123
named "inbound-main-flow". The flow should invoke Lambda
function lookup-customer
(arn:aws:lambda:us-east-1:123456789012:function:lookup-customer)
and branch on the returned "department" attribute. Handle
Lambda.AccessDenied and Lambda.Timeout exceptions by
transferring to the default queue. Instance ARN
arn:aws:connect:us-east-1:123456789012:instance/inst-abc123.
