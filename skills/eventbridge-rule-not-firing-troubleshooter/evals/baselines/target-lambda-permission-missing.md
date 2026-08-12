# Baseline (no-skill) response: target-lambda-permission-missing

---

Your EventBridge rule is trying to invoke the Lambda but getting
AccessDenied. The Lambda's resource-based policy only has a statement
for API Gateway, not EventBridge. You need to add a permission for
EventBridge. You can do this with `aws lambda add-permission` with the
principal set to `events.amazonaws.com`. Also make sure the rule has
the right IAM role if it's cross-account.
