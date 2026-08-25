# Error Handling — s3-replication-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Malformed input handling

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Source/operation
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws s3api get-bucket-replication
--bucket <source> --output json and re-plan.`

---

## Replication failure-mode table (diagnose-not-replicating)

| Symptom | Root cause | Fix |
|---|---|---|
| `Status: Enabled` but zero objects in destination, source has new PUTs | Versioning OFF on source OR destination | `put-bucket-versioning --versioning-configuration Status=Enabled` on both |
| Rule `Status: Disabled` | Operator paused the rule | Update rule with `Status: Enabled` |
| Filter prefix does not match the object key | Object is outside the rule's scope | Update the prefix or add a Tag filter that matches |
| IAM role missing `s3:ReplicateObject` on destination | Identity-based policy gap | Attach a policy granting `s3:ReplicateObject` on `arn:aws:s3:::<dest>/*` |
| IAM role missing `kms:Decrypt` on source key | Source KMS key policy gap | Add `kms:Decrypt` grant for the role on the source key |
| IAM role missing `kms:Encrypt` on destination key | Destination KMS key policy gap | Add `kms:Encrypt` grant on the destination key |
| Cross-account: destination bucket policy missing `s3:x-amz-source-account` condition | Resource-based policy gap | Add a Statement with the source account condition |
| Cross-account: `AccessDenied` in CloudTrail on destination | Destination bucket policy or KMS key policy | Inspect both; the role's identity-based policy is necessary but not sufficient |
| `PendingReplication` rising, never drains | IAM, KMS, or destination policy bottleneck | Sequence through pre-checks; check CloudTrail `Replication` events |
| Delete markers in source but not destination | `DeleteMarkerReplication.Status: Disabled` | Update rule to enable delete-marker replication |
| Tag updates in source but not destination | `ReplicaModifications.Status` missing or `Disabled` | Add `SourceSelectionCriteria.ReplicaModifications.Status: Enabled` |
| Object Lock source object rejected by destination | Destination bucket does NOT have Object Lock enabled | Enable Object Lock on destination BEFORE retrying |
| Replication only works for some prefixes | Multiple rules with overlapping filters; lower-Priority rule is masked | Disambiguate filters or raise Priority of the intended rule |
