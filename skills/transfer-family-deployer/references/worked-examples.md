# Worked examples — transfer-family-deployer

Moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Common server patterns (boilerplate)

### Service Managed SFTP — S3 backend (public endpoint)

```bash
# Trust policy for the Transfer user execution role
cat > transfer-user-trust.json <<'EOF'
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {"Service": "transfer.amazonaws.com"},
    "Action": "sts:AssumeRole",
    "Condition": {"StringEquals": {"aws:SourceAccount": "111111111111"}}
  }]
}
EOF

aws iam create-role \
  --role-name TransferUserS3Role \
  --assume-role-policy-document file://transfer-user-trust.json

# Inline policy: maximum scope (session policy narrows per-user)
aws iam put-role-policy \
  --role-name TransferUserS3Role \
  --policy-name S3Access \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::prod-sftp-inbox"},
      {"Effect": "Allow", "Action": ["s3:GetObject", "s3:PutObject", "s3:DeleteObject"], "Resource": "arn:aws:s3:::prod-sftp-inbox/*"}
    ]
  }'

# Logging role
aws iam create-role --role-name TransferLoggingRole \
  --assume-role-policy-document file://transfer-user-trust.json
aws iam attach-role-policy --role-name TransferLoggingRole \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSTransferLoggingAccess

# Create the server (Service Managed SFTP, public endpoint)
aws transfer create-server \
  --description "prod-sftp-inbox" \
  --protocols SFTP \
  --endpoint-type PUBLIC \
  --identity-provider-type SERVICE_MANAGED \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole \
  --tags Key=Environment,Value=prod Key=Name,Value=prod-sftp-inbox

# Returns: { "ServerId": "s-abc123def456" }

# Add a user with a session policy scoping them to home/alice/
aws transfer create-user \
  --server-id s-abc123def456 \
  --user-name alice \
  --role arn:aws:iam::111111111111:role/TransferUserS3Role \
  --home-directory "/prod-sftp-inbox/alice" \
  --home-directory-type PATH \
  --ssh-public-key-body "ssh-rsa AAAAB3...alice@laptop" \
  --policy '{
    "Version": "2012-10-17",
    "Statement": [
      {"Effect": "Allow", "Action": ["s3:ListBucket"], "Resource": "arn:aws:s3:::prod-sftp-inbox", "Condition": {"StringLike": {"s3:prefix": ["alice/*","alice"]}}},
      {"Effect": "Allow", "Action": ["s3:GetObject","s3:PutObject","s3:DeleteObject"], "Resource": "arn:aws:s3:::prod-sftp-inbox/alice/*"}
    ]
  }'
```

### Custom IdP via API Gateway + Lambda (VPC endpoint)

```bash
# Invocation role for Transfer Family to call the API Gateway
aws iam create-role \
  --role-name TransferIdPInvocationRole \
  --assume-role-policy-document file://transfer-user-trust.json
aws iam put-role-policy \
  --role-name TransferIdPInvocationRole \
  --policy-name InvokeIdP \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "apigateway:Invoke",
      "Resource": "arn:aws:apigateway:us-east-1::/restapis/abc123/stages/prod/POST/"
    }]
  }'

aws transfer create-server \
  --description "prod-sftp-vpc-custom-idp" \
  --protocols SFTP FTPS \
  --endpoint-type VPC \
  --identity-provider-type API_GATEWAY \
  --identity-provider-details '{
    "Url": "https://abc123.execute-api.us-east-1.amazonaws.com/prod/",
    "InvocationRole": "arn:aws:iam::111111111111:role/TransferIdPInvocationRole"
  }' \
  --certificate arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --address-allocation-id allocation-id-elastic-ip \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-ssh sg-ftps \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole \
  --tags Key=Environment,Value=prod
```

### Directory Service (Managed AD), FTPS, AS2 — short forms

Directory Service SFTP uses `--identity-provider-type AWS_DIRECTORY_SERVICE --identity-provider-details '{"DirectoryId":"d-abc123"}'` with `--endpoint-type VPC_ENDPOINT`. FTPS requires `--certificate <acm-arn>` in the same region. AS2 uses `--protocols AS2 --endpoint-type VPC_ENDPOINT` followed by `create-profile` for local and partner profiles. Full CLI sequences in `references/identity-providers-and-storage.md`.

### Managed workflow (OnUpload — process inbound file)

```bash
# Execution role trusts transfer.amazonaws.com with lambda:InvokeFunction on the step Lambda
aws transfer create-workflow \
  --description "Process inbound SFTP file" \
  --steps '[{"Type":"COPY","CopyStepDetails":{"DestinationFileLocation":{"S3FileLocation":{"Bucket":"prod-processed","Key":"inbound"}},"SourceFileLocation":"${originalFile}"}},{"Type":"CUSTOM","CustomStepDetails":{"Target":"arn:aws:lambda:us-east-1:111111111111:function:process-inbound-file"}}]' \
  --on-exception-steps '[{"Type":"DELETE","DeleteStepDetails":{"SourceFileLocation":"${originalFile}"}}]'

# Reference the workflow on the server via update-server --workflow-details '{"OnUpload":{"WorkflowId":"w-abc123","ExecutionRole":"arn:aws:iam::111111111111:role/TransferWorkflowExecutionRole"}}'
```

Full managed-workflow CLI sequence with execution role setup is in `references/identity-providers-and-storage.md`.
