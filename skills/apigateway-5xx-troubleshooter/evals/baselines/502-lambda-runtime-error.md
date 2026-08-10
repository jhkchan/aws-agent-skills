# Baseline (no-skill) response: 502-lambda-runtime-error

This file captures what a generic assistant produces WITHOUT the
apigateway-5xx-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

You're getting a 502 from API Gateway, which means your Lambda function
is failing. Check the CloudWatch logs for the function — you'll probably
see an error there. Once you fix the error in the Lambda code, the 502
should go away.

Make sure all the environment variables the function needs are set
correctly in the Lambda configuration. After updating the code, test it
with a sample event to confirm it works before deploying.
