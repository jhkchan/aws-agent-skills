# Baseline (no-skill) — internal-reports-finance

> This is the response a model produces **without** the skill definition.
> It misclassifies the VPCe-restricted wildcard as PUBLIC (or SAFE) because
> it lacks the condition-strength matrix and Rule 4 classification.

---

This bucket has a policy that allows `s3:GetObject` to `Principal: "*"`
on `arn:aws:s3:::internal-reports-finance/*`. There's a condition that
restricts access to a VPC endpoint (`aws:sourceVpce: vpce-1a2b3c4d5e6f7g8h9`).

Since the principal is `"*"`, this bucket is technically public, but the
VPC endpoint condition limits access to traffic coming through that specific
endpoint. So it's restricted to your VPC.

I'd classify this as public but restricted. If someone can access your VPC
endpoint, they can read the objects.

BPA is off, so nothing is blocking this.

Remediation: Enable Block Public Access. The VPC endpoint condition provides
some protection but you should add more restrictions. Consider removing the
wildcard principal.

Actually, since the VPC endpoint restricts access, maybe this is safe enough.
It depends on your threat model.
