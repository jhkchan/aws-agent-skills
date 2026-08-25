# Error Handling — ssm-association-operator

Moved verbatim from SKILL.md (progressive disclosure; load on demand). Sections keep their original headings.

## Error handling

- **Zero targets processed:** no instances match the target filter, or
  matching instances are not managed by SSM. Verify with
  `describe-instance-information` using the same filter. Check that
  target instances have `AmazonSSMManagedInstanceCore`.
- **Association stuck in Pending:** created without `--apply-at-
  creation` and not yet reached scheduled tick. Trigger with
  `start-associations-once`.
- **Output not delivered to S3:** bucket policy missing
  `s3:PutObject` for `ssm.amazonaws.com`, or KMS key policy missing
  `kms:GenerateDataKey`. SSM silently drops output. Check CloudTrail
  for `AccessDenied` from `ssm.amazonaws.com`.
- **Association status Failed:** inspect per-instance output in S3 at
  `s3://<bucket>/<prefix>/<assoc-id>/<exec-id>/<instance-id>/`. Common
  causes: invalid parameters, missing dependencies, script errors.
- **NON_COMPLIANT after successful run:** document has a compliance
  check step that detected drift. Re-run the association or trigger
  remediation.
- **Rate control stopped the run early:** `max-errors` threshold
  reached. Inspect failed instances, fix root cause, re-run.
