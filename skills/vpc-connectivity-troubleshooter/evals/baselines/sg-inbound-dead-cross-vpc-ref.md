# Baseline (no-skill) response: sg-inbound-dead-cross-vpc-ref

This file captures what a generic assistant produces WITHOUT the
vpc-connectivity-troubleshooter skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, layer identification,
evidence-backed root cause, OSI-aligned probe order).

---

Your EC2 instance can't reach the database in the other VPC. The
peering is Active, which is good. Check the security group on the
database instance — it needs to allow port 5432 from your application's
IP range (10.0.0.0/16).

Also verify the route tables have the peering routes both ways, and
that the NACLs are not blocking anything. The default NACL should be
fine.
