# Baseline (no-skill) response: public-service-network-wildcard

This file captures what a generic assistant produces WITHOUT the
vpc-lattice-auth-auditor skill loaded.

---

The auth policy grants vpc-lattice:* to Principal "*" which means everyone
can access the services. This is very permissive and should be tightened.

You should replace the wildcard principal with specific account or role
ARNs. The target groups and VPC configuration look standard.
