# Baseline (no-skill) response: dangling-alias-deleted-elb

This file captures what a generic assistant produces WITHOUT the
route53-record-auditor skill loaded.

---

This record points to an ELB that has been deleted. The DNS name no
longer resolves, so users trying to reach legacy.app.example.com will get
an error. You should delete this record or update it to point to a
valid resource.

The zone has DNSSEC enabled which is good.
