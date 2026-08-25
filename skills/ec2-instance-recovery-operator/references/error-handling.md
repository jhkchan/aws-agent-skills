# EC2 Instance Recovery - Error Handling

Malformed-input protocol moved verbatim from SKILL.md.

**Malformed input:** if the input JSON is invalid or missing required
fields, emit `VERDICT: ERROR` with `REASON: Instance/operation
configuration is not valid JSON or is missing required fields — cannot
plan.` and `REMEDIATION: Re-fetch with aws ec2 describe-instance-status
--instance-ids <id> --include-all-instances --output json and re-plan.`
