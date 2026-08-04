# Baseline (no-skill) response: public-pull-wildcard-no-condition

This file captures what a generic assistant produces WITHOUT the
ecr-repository-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, supply-chain reasoning).

---

This ECR repository policy grants `ecr:BatchGetImage` and
`ecr:GetDownloadUrlForLayer` to `Principal: "*"`, which means any AWS
account can pull images from this repository.

You should restrict the principal to specific accounts or roles. Also,
the scanning configuration looks good with scanOnPush enabled.
