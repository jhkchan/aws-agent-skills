# Baseline (no-skill) response: 504-timeout-mismatch-lambda-too-high

This file captures what a generic assistant produces WITHOUT the
apigateway-5xx-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, error-code-driven probe order).

---

The 504 timeout means your backend is taking too long to respond. API
Gateway has a 29 second timeout for REST APIs, so if your Lambda function
takes longer than that, you'll get a 504.

Your Lambda function is configured with a 60 second timeout, but API
Gateway will timeout at 29 seconds regardless. You should optimize your
database query to run faster, or consider increasing the Lambda memory to
give it more CPU. If the query genuinely needs more than 29 seconds, you
might need to redesign the API to be asynchronous.
