# Eval: kms-encryption-custom-key

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — domain created with CMK ARN, encryption immutability noted (cannot change after creation)

## Prompt

Create a CodeArtifact domain secure-domain in us-east-1,
account 123456789012. Use a customer-managed KMS key
arn:aws:kms:us-east-1:123456789012:key/abcd1234-ef56-7890-abcd-ef1234567890
for encryption. Create a nuget repository dotnet-packages.
Tags: Environment=production, Compliance=required.
