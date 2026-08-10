# Baseline (no-skill) response: 502-lambda-proxy-malformed-response

This file captures what a generic assistant produces WITHOUT the
apigateway-5xx-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

You're getting a 502 from API Gateway. This usually means the backend is
returning an error or the response format is wrong. Check your Lambda
function logs in CloudWatch to see if there are any errors. If the
function is running fine, the issue might be the response format — Lambda
proxy integrations need a specific format with statusCode and body.

Try testing the Lambda function directly with a test event to see what
it returns. If it returns a plain object, you need to wrap it in the
correct proxy response format.
