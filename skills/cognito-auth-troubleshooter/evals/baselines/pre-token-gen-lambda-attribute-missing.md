# Baseline (no-skill) response: pre-token-gen-lambda-attribute-missing

This file captures what a generic assistant produces WITHOUT the
cognito-auth-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, symptom-to-layer triage).

---

The UserLambdaValidationException means your Lambda trigger is failing.
Check the CloudWatch logs for your pre-token-generation Lambda function.
It looks like there's a JavaScript error in your code.

You should fix the TypeError in your Lambda handler — it's trying to
read a property from an undefined value. Make sure the user attributes
you're trying to access actually exist before using them.
