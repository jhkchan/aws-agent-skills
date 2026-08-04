# Baseline (no-skill) response: unused-role-legacy-etl

This file captures what a generic assistant produces WITHOUT the
accessanalyzer-finding-triage skill loaded — the contrast that proves the skill
adds structure (deterministic VERDICT, RISK level, specific remediation).

---

The role `legacy-etl-role` hasn't been used in over 90 days (last accessed
October 15, 2024). Since it has access to production data buckets with
s3:GetObject and s3:PutObject, this could be a security risk if someone gains
access to the role credentials.

You should check if this role is still needed. If not, you can delete it. If
it is still used occasionally (maybe for quarterly jobs), you might want to
keep it but add some restrictions.

To check if it's really unused, look at CloudTrail for any AssumeRole events
in the last few months.
