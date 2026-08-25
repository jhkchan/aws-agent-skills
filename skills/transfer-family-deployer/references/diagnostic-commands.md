# Diagnostic commands — transfer-family-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

**Live-account pre-flight (skip if offline plan audit):**

1. `aws transfer list-servers` — confirm the server name does not
   collide (note: Transfer Family uses server-id, not names; tags hold
   the human-readable name).
2. `aws transfer describe-server --server-id <id>` — capture the full
   server config for snapshot/diff.
3. `aws s3api head-bucket --bucket <bucket>` — verify S3 backend exists
   in the same region.
4. `aws s3api get-bucket-policy --bucket <bucket>` — verify the bucket
   policy grants the IAM role.
5. `aws iam get-role --role-name <TransferUserRole>` — verify the
   execution role exists and trusts `transfer.amazonaws.com`.
6. `aws iam get-role-policy --role-name <role> --policy-name <policy>`
   or `aws iam list-attached-role-policies` — verify the role has S3
   permissions.
7. `aws acm describe-certificate --certificate-arn <arn>` — for FTPS,
   verify cert is ISSUED in the same region.
8. `aws ec2 describe-security-groups --group-ids <sg-ids>` — for VPC
   endpoints, verify the SGs exist and inbound rules match protocols.
9. `aws ds describe-directories --directory-ids <id>` — for
   AWS_DIRECTORY_SERVICE, verify the directory exists and is ACTIVE.
10. `aws apigateway get-rest-api --rest-api-id <id>` — for
    `API_GATEWAY` IdP, verify the API exists and the stage is deployed.
11. `aws lambda get-policy --function-name <idp-lambda>` — for custom
    IdP, verify the API Gateway principal can invoke the Lambda.
12. `aws transfer list-workflows` — for managed workflow reference,
    verify the workflow exists and is ACTIVE.
