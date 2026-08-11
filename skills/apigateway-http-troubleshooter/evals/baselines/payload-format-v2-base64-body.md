# Baseline (no-skill) response: payload-format-v2-base64-body

This file captures what a generic assistant produces WITHOUT the
apigateway-http-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, payload-format-version awareness).

---

Your API Gateway is returning 502 Bad Gateway. This usually means the
Lambda function is throwing an error. Look at the Lambda logs — you'll
see "SyntaxError: Unexpected token in JSON" which means your function
is trying to parse the request body as JSON but the body is not valid
JSON.

Try logging the event object to see what API Gateway is actually
sending to your function. You might need to fix how your function
reads the request body. Also check if the Lambda function is returning
the response in the correct format — API Gateway expects a specific
JSON structure with statusCode, body, and headers.
