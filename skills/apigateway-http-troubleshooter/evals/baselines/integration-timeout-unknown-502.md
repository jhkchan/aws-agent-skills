# Baseline (no-skill) response: integration-timeout-unknown-502

---

Your API Gateway is returning 502 intermittently on POST /webhook.
This is probably a Lambda error. Check the Lambda function logs to
see if it's throwing an exception on some requests. You should also
verify the response format — API Gateway needs the response to have
statusCode as a number and body as a string.

If it's not Lambda, it could be a timeout issue. API Gateway has a
29-second timeout limit. Make sure your backend isn't taking too long
on some requests.
