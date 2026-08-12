# Baseline (no-skill) — iam-auth-policy-service-level

> This is the response a model produces **without** the skill
> definition. It attaches an auth policy but may attempt to scope it per
> listener rule (impossible in VPC Lattice — auth policy is at the
> SERVICE level), misses that the policy covers ALL paths on the
> service, and does not emit the READY_TO_DEPLOY checklist format.
> Generated for with-skill-vs-baseline comparison.

---

Attach an IAM policy to the service. For the /admin/* path, require
auth; for /api/* maybe leave it open. Put the policy on the rules.
