# Baseline (no-skill) response: master-secret-arn-misconfigured

This file captures what a generic assistant produces WITHOUT the
secrets-manager-rotation-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, symptom-to-layer triage).

---

The Lambda is throwing ResourceNotFoundException because it can't
find the Master Secret. The error message shows the ARN
`arn:aws:secretsmanager:us-east-1:111111111111:secret:prod/auth/missing-master-6fXq2L`.

You should check the IAM permissions on the rotation role — it
probably needs `secretsmanager:GetSecretValue` on that secret ARN.
Add a policy statement allowing that action and try the rotation
again. If the secret truly doesn't exist, you may need to recreate
the Master Secret or update the Lambda's environment variable to
point at the correct one.
