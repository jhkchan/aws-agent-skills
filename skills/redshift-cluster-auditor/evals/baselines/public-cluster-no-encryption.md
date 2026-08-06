# Baseline (no-skill) response: public-cluster-no-encryption

This file captures what a generic assistant produces WITHOUT the
redshift-cluster-auditor skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, enumerated FINDINGS, specific
remediation, Redshift-specific reasoning about immutability, default-PG
behaviour, and EnhancedVPCRouting data-path privacy).

---

This Redshift cluster has several security issues:

1. **PubliclyAccessible is true** — the cluster is reachable from the
   internet. You should set this to false if the cluster does not need
   to be public.

2. **Encryption is off** — you should enable encryption at rest to
   protect the data.

3. **require_ssl is false** — clients can connect without TLS. You
   should enable this.

4. **Audit logging is disabled** — turn on logging to S3 for forensics.

5. **Enhanced VPC routing is off** — consider enabling it so COPY and
   UNLOAD traffic stays in your VPC.

6. **The security group allows 0.0.0.0/0 on port 5439** — this is too
   permissive. Restrict it to your corporate CIDR.

The cluster also uses the default parameter group, which you may want
to change.
