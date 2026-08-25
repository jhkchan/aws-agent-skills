# Diagnostic Commands — OpenSearch Serverless Deployer
Diagnostic and pre-flight command listings, moved verbatim from SKILL.md.

## Verification commands (run after deployment)
```bash
# Verify collection is ACTIVE
aws opensearchserverless batch-get-collection --ids <id> --query 'collections[0].status'
# Verify encryption policy
aws opensearchserverless get-security-policy --name prod-encryption --type encryption
# Verify network policy
aws opensearchserverless get-security-policy --name prod-network --type network
# Verify VPC endpoint
aws opensearchserverless list-vpc-endpoints --vpc-endpoint-id vpce-xyz123 --query 'vpcEndpointSummaries[0].status'
# Verify KMS symmetric
aws kms describe-key --key-id abc-123 --query 'KeyMetadata.KeySpec'
```
