# Baseline (no-skill) response: rotation-lambda-vpc-timeout

This file captures what a generic assistant produces WITHOUT the
secrets-manager-rotation-troubleshooter skill loaded — the contrast
that proves the skill adds structure (deterministic VERDICT, layer
identification, evidence-backed root cause, symptom-to-layer triage).

---

Your secret rotation is failing because the Lambda can't connect to
the database. The error says "Could not connect to database" and then
"Task timed out after 15 seconds". You should raise the Lambda timeout
to 60 seconds or 120 seconds so it has more time to connect. Also
check the database security group — port 5432 should be open to the
Lambda.

If that doesn't help, verify the RDS endpoint URL in the secret value
matches the actual cluster endpoint. Aurora PostgreSQL sometimes
resolves to a reader instance if you use the wrong endpoint.
