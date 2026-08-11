# Baseline (no-skill) response: rest-to-http-api-migration

This file captures what a generic assistant produces WITHOUT the
apigateway-throttle-optimizer skill loaded — the contrast that proves the
skill adds structure (deterministic VERDICT, REST-only feature check,
dollar savings estimate, CONFIRM gate, migration safety steps).

---

Your REST API is using Lambda proxy integration without any mapping
templates or request validation. You could save money by switching to
HTTP API, which is cheaper per request.

REST API costs $3.50 per million requests while HTTP API costs only
$1.00 per million. At 200 million requests per month, that is $700/month
on REST vs $200/month on HTTP — a savings of $500/month.

To migrate, you will need to create a new HTTP API and move your routes
over. The Lambda proxy integration is supported on both.

```
aws apigatewayv2 create-api --name api-http --protocol-type HTTP --target <lambda-arn>
```

Make sure Cognito JWT authorizers are configured on the new HTTP API
before cutting over.
