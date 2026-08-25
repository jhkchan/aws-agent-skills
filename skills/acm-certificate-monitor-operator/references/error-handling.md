# Error Handling — ACM Certificate Monitor Operator

Load-on-demand error-handling detail moved verbatim from SKILL.md.

## Error handling

### DaysToExpiry metric reporting -1
- The certificate is not eligible for DaysToExpiry monitoring. Check
  certificate status (must be ISSUED). Imported certificates may not
  report DaysToExpiry correctly.

### Renewal status shows FAILED
- Check (in order): CAA records, DNS validation records, service
  attachment, domain ownership. The most common cause is a CAA record
  conflict, followed by missing DNS validation records.

### Certificate status is PENDING_VALIDATION for an extended period
- DNS validation CNAME may be missing or incorrect. Verify the CNAME
  record matches exactly what ACM specifies. Check for trailing dots
  in the DNS record name.

### Alarm stays in INSUFFICIENT_DATA
- The metric is not reporting. The certificate may be in a non-ISSUED
  state, or the alarm dimensions may not match the certificate ARN
  exactly. Verify with `describe-alarms` and `get-metric-statistics`.

### Multi-account audit fails for a member account
- The monitoring role may not exist in the member account, or the
  audit account does not have permission to assume it. Verify the
  trust policy on the member account's monitoring role.
