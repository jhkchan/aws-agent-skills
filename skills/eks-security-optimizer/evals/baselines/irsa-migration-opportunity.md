# Baseline (no-skill) response: irsa-migration-opportunity

This file captures what a generic assistant produces WITHOUT the
eks-security-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, per-namespace IRSA migration plan,
audit-first PSA guidance, CONFIRM gate).

---

Your cluster is in pretty good shape security-wise. You have Pod Security
Admission configured, Calico network policies with default-deny, KMS
encryption, ECR scanning, GuardDuty, Kyverno, and Istio mTLS. That's a
strong security posture.

The main issue is that 16 of your 20 namespaces are still using the node
IAM role instead of IRSA. This is a significant risk because every pod
in those namespaces inherits the node role's permissions, which probably
includes broad access to AWS resources.

You should migrate those namespaces to IRSA. For each namespace:

1. Identify what AWS permissions the workloads in that namespace need
2. Create an IAM role with those permissions and a trust policy for your
   OIDC provider
3. Annotate the service account with the role ARN
4. Restart the pods so they pick up the new credentials

This is going to take some time for 16 namespaces, but it's important
for least-privilege access.

Once that's done, your cluster will be in very good shape.
