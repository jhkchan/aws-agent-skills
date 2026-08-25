# Error Handling — cloudtrail-org-trail-auditor

## Malformed trail configuration (ERROR block)

If the trail configuration is malformed (missing `Name`, no `S3BucketName`,
or unparseable JSON), output:

```text
TRAIL: <name-or-unknown>
VERDICT: ERROR
REASON: Trail configuration is incomplete or unparseable — cannot classify.
REMEDIATION: Retrieve the canonical config with `aws cloudtrail describe-trails --trail-name-list <name> --output json` and re-audit.
```
