# Baseline (no-skill) response: timeout-step-functions-mismatch

---

The Step Functions execution is failing with States.Timeout. This means
the Lambda function took too long. Your Lambda timeout is 60 seconds
which is quite long — you should reduce it to under 30 seconds so it
fails faster.

Alternatively, look at the Lambda function to see if you can optimise
the ETL batch processing to complete in under 30 seconds.
