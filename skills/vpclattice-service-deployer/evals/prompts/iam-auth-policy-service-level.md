# Eval: iam-auth-policy-service-level

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — IAM auth policy attaches to the SERVICE not individual rules; covers ALL paths including /api/* and /admin/*

## Prompt

Apply IAM auth policy to Lattice service payments-svc (svc-bbb222)
in us-east-1. Allow role arn:aws:iam::123456789012:role/PaymentsCaller
to invoke the service. The service has listener rules for /api/*
and /admin/* paths. Auth should apply to ALL paths on the service.
