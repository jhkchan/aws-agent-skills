# Error handling — transfer-family-workflow-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling

- **User authenticates but cannot read/write files:** check IAM role
  S3 permissions AND session policy (effective = intersection).
- **Connection timeout on VPC_ENDPOINT:** verify security group allows
  TCP 22 from client subnet. Check VPC DNS resolution.
- **Managed workflow not triggering:** verify workflow attached via
  `describe-server`. Check Step Functions execution history.
- **AS2 delivery failure:** verify partner certificate validity and
  connector URL. Check MDN status.
- **Custom Lambda auth failure:** check Lambda CloudWatch Logs. Verify
  response format (home directory, IAM role, session policy).
