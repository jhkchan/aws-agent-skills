# Baseline (no-skill) — sftp-custom-lambda-vpc

> This is the response a model produces **without** the skill
> definition. It lists CLI commands but misses the VPC_ENDPOINT
> PrivateLink semantics (vs VPC NLB), the Lambda response format
> requirement (home directory, IAM role, session policy in the
> response), the security group configuration for the VPC endpoint,
> and the READY_TO_DEPLOY checklist format. Generated for
> with-skill-vs-baseline comparison.

---

Create the SFTP server with a Lambda identity provider:

```bash
aws transfer create-server \
  --protocols SFTP \
  --identity-provider-type LAMBDA \
  --endpoint-type VPC
```

Point it to your Lambda function and it should authenticate users.
