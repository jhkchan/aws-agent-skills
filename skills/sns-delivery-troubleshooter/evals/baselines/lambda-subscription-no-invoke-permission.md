# Baseline (no-skill) response: lambda-subscription-no-invoke-permission

---

Your Lambda function isn't being invoked by SNS. Check that the
subscription is set up correctly and the function name is right. Also
look at the Lambda function's CloudWatch Logs to see if there are any
errors.

Make sure the SNS topic has permission to invoke the Lambda. If you
created the subscription via the console it should be set up
automatically, but if you used Terraform or CloudFormation you might
need to add the permission manually.
