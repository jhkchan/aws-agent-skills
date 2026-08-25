# Worked Examples — VPC Lattice Auth Auditor

Deep reference content moved verbatim from `vpc-lattice-auth-auditor/SKILL.md`. Loaded on demand;
see SKILL.md for the condensed core and its quick navigation.

## Worked example — partially malformed auth policy

```text
SERVICE NETWORK: sn-0malformed1
VERDICT: CONFIG_GAP
REASON: One statement is valid and grants cross-account Invoke (CONFIG_GAP);
two statements are malformed and cannot be classified (ERROR notes below).
FINDINGS:
  - [CONFIG_GAP] Statement "ExternalInvoke" grants vpc-lattice:Invoke to
    arn:aws:iam::222222222222:role/consumer (Rule 5c)
  - [ERROR] Statement "BrokenStmt1" is missing required field "Effect" —
    cannot classify
  - [ERROR] Statement "BrokenStmt2" is missing required field "Action" —
    cannot classify
REMEDIATION: Fix malformed statements by retrieving the canonical policy with
  aws vpc-lattice get-auth-policy --resource-arn <arn> --output json. Address
  the CONFIG_GAP finding by scoping or removing the cross-account principal.
```

Key rule: one malformed statement does NOT make the entire network ERROR.
Classify valid statements normally, emit ERROR notes for malformed ones, and
aggregate the worst valid finding as the verdict.

## Sample scoped auth policy (NO_AUTH_POLICY remediation)

2. Sample correct policy (same-account, SourceVpc-scoped):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"AWS": "arn:aws:iam::111111111111:role/app-service-role"},
      "Action": "vpc-lattice:Invoke",
      "Resource": "*",
      "Condition": {"StringEquals": {"aws:SourceVpc": "vpc-0eee6666bbbb"}}
    }
  ]
}
```

3. Verify the policy is effective (wait 10s for eventual consistency):
   `aws vpc-lattice get-auth-policy --resource-arn <sn-arn>`
4. If cross-account is required, add the consumer role ARN with
   `aws:SourceAccount` — but expect CONFIG_GAP verdict (external trust).
