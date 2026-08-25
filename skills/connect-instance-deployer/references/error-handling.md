# Error Handling (load on demand) — Connect Instance Deployer

Error-handling deep dives and failure remedies moved verbatim from SKILL.md. Loaded on demand.

---

## Error handling (moved from SKILL.md)

- **Flow fails at run time despite creating:** referenced resource
  (queue/Lambda/Lex) does not exist or ARN is wrong. Pre-flight
  check every referenced resource.
- **Lambda invocations return AccessDenied:** Lambda lacks a
  resource policy granting `connect.amazonaws.com`. Add via
  `aws lambda add-permission --principal connect.amazonaws.com
  --source-arn <instance-arn>`.
- **Contacts route to wrong agents:** routing profile lacks skill
  requirements → routing is pure queue-priority.
- **Phone number claim fails:** different region from instance, or
  not available in AWS pool.
- **Lex bot invocations time out:** alias is DRAFT (not published),
  or locale does not match instance language.
- **Voice ID enrollment fails:** caller did not provide consent
  (consent disclosure prompt missing in flow).
- **Recordings not in S3:** KMS key policy or S3 bucket policy
  blocks Connect. Verify both grant `connect.amazonaws.com`.
- **Real-time metrics missing:** instance created before the
  feature was enabled, or stream not configured.
