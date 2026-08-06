# Baseline (no-skill) response: policy-not-ready

This file captures what a generic assistant produces WITHOUT the
firewall-manager-compliance-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, silent-failure detection).

---

This Firewall Manager policy is for a WAFv2 configuration covering CloudFront,
API Gateway, and ALB resources in one OU. The policy state is NOT_READY which
means it's not fully deployed yet.

Since ProtectedResourceCount and NonCompliantResourceCount are both 0, the
policy hasn't started enforcing. You should check back later once it transitions
to READY. Remediation is enabled so once it's ready it will start applying the
WebACL.

The scope looks reasonable — CloudFront, API Gateway, and ALBs are the typical
WAF attachment points.
