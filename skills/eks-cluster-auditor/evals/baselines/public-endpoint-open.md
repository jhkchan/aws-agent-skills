# Baseline (no-skill) response: public-endpoint-open

This file captures what a generic assistant produces WITHOUT the
eks-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, priority-ordered classification).

---

This EKS cluster has its API endpoint set to public access with
0.0.0.0/0 as the allowed CIDR, which means the Kubernetes API server
is reachable from the internet. You should restrict this to known IP
ranges or disable public access entirely.

The cluster also has control-plane logging disabled, so you won't have
audit logs for Kubernetes API calls. The security group on the worker
nodes allows inbound traffic on port 10250 from anywhere, which exposes
the kubelet API.

I'd recommend enabling private endpoint access, turning on logging, and
restricting the security group rules.
