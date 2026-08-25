# RDS Connectivity Troubleshooter — worked examples (moved from SKILL.md)

Loaded on demand — content moved verbatim from SKILL.md (progressive disclosure; nothing deleted).

### Worked example — INSUFFICIENT_DATA (moved from SKILL.md)

```text
TARGET: unknown
VERDICT: INSUFFICIENT_DATA
ROOT_CAUSE: UNKNOWN
REASON: Input is "RDS is down" with no instance identifier, no
  endpoint, and no specific error string; the category cannot be
  determined.
EVIDENCE:
  - Missing: DB instance or cluster identifier
  - Missing: specific error string (timeout vs refused vs auth)
  - Missing: client context (EC2 / ECS / Lambda, subnet, SG)
REMEDIATION:
  1. Run aws rds describe-db-instances --output json and share the
     instance identifier.
  2. Share the exact error string the application logs.
  3. Share the client's VPC, subnet, and security group.
```

