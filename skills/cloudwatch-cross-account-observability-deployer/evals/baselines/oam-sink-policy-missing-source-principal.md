# Baseline (no-skill) response: oam-sink-policy-missing-source-principal

This file captures what a generic assistant produces WITHOUT the
cloudwatch-cross-account-observability-deployer skill loaded.

---

The AccessDenied error means you probably need more permissions.
Try adding administrator access to the role, or check that the
source account has the right IAM policy. You might also need to
add the source account to the sink policy — run
`aws oam put-sink-policy` with an Allow principal for the source
account root.
