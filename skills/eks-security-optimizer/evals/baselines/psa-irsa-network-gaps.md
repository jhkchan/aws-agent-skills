# Baseline (no-skill) response: psa-irsa-network-gaps

This file captures what a generic assistant produces WITHOUT the
eks-security-optimizer skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, severity scoring, eight-dimension
coverage, IRSA-specific remediation, CONFIRM gate).

---

Your EKS cluster has several security issues that should be addressed.

First, you don't have Pod Security Admission configured. You should
enable PSS labels on your namespaces to enforce pod security standards.
Start with baseline mode and work up to restricted.

Second, 12 of your 15 namespaces are using the node IAM role instead of
IRSA. This means every pod in those namespaces has the node's AWS
permissions, which is way too broad. You should set up IAM Roles for
Service Accounts for each namespace.

Third, you have no network policies, which means any pod can reach any
other pod. You should install Calico or Cilium and set up default-deny
policies.

Also, you're not using KMS for secrets encryption. You should enable
that via the update-cluster-config command.

I'd also recommend setting up mTLS with a service mesh, but that's
lower priority.

The good news is you already have ECR scanning, GuardDuty, and
Gatekeeper deployed, so those are fine.
