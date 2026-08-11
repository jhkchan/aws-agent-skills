# Eval prompt: oam-sink-policy-missing-source-principal

Diagnose why `oam create-link` from a source account fails because
the sink policy omits the source account principal. Walk the
pre-flight checks and emit the standard VERDICT block.

## Scenario

An operator tries to attach source account `444455556666` to sink
`arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink`.
The source account IAM role `OAMLinkRole` has `oam:CreateLink` on
the sink ARN. However, the sink policy currently lists only the
monitoring account `111122223333` as principal — it does NOT
include `444455556666`. The operator runs `oam create-link` and
expects it to succeed.

## Known facts

- **Sink ARN:** `arn:aws:oam:us-east-1:111122223333:sink/ProdObservabilitySink`.
- **Sink policy:** only lists `arn:aws:iam::111122223333:root`.
- **Source account:** `444455556666`.
- **Source IAM:** `OAMLinkRole` with `oam:CreateLink` on the
  sink ARN (correctly scoped).
- **Application Signals:** enabled in the source for the checkout
  ECS workload.

## Symptom

`oam create-link` from the source account returns
`AccessDenied`. The operator needs to know what is missing and
how to fix the sink policy.
