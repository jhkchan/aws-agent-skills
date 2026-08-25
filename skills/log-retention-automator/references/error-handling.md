# Error handling — log-retention-automator

API error tables and failure-mode fixes moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Step 3: common errors and fixes

Common errors and fixes:

| Error | Cause | Fix |
|---|---|---|
| `InvalidParameterException` | retentionInDays not in allowed set | Round to nearest allowed tier (Appendix A) |
| `ThrottlingException` | Too many put-retention-policy calls | Add 0.2s sleep between calls; batch in groups of 50 |
| `ResourceNotFoundException` | Log group deleted between describe and put | Skip; log as "already gone" |
| `AccessDeniedException` | IAM role missing `logs:PutRetentionPolicy` | Add policy with `logs:PutRetentionPolicy` on `arn:aws:logs:*:*:log-group:*` |
