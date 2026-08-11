# Transfer Family Identity Providers, Storage, and Workflows Reference

Load this reference when planning custom identity provider wiring,
Directory Service integration, EFS storage backend, AS2 profiles, or
managed workflow configuration for a Transfer Family server.

## Identity provider decision tree

| Scenario | IdP type | Why |
|---|---|---|
| Small user count, SSH keys feasible | `SERVICE_MANAGED` | No IdP infrastructure to operate |
| External partners with own IdP (Okta, Auth0) | `API_GATEWAY` | Custom Lambda for user mapping, MFA, audit |
| Workforce users in Active Directory | `AWS_DIRECTORY_SERVICE` | DOMAIN\user + AD password, no SSH keys |
| AS2 B2B app-level exchange | Local + partner profiles | Mutual cert auth, MDN acks |

## API Gateway + Lambda custom IdP procedure

**Pre-checks:**
1. `InvocationRole` ARN resolves via `iam:get-role`.
2. Invocation role trusts `transfer.amazonaws.com` and has
   `apigateway:Invoke` on the REST API.
3. `Url` is HTTPS, REST API deployed to a stage.
4. Pre-flight test: POST a sample username/password to the API and
   verify the response shape (Role, HomeDirectory, optional Policy,
   optional PublicKeys).
5. Lambda resource-based policy allows the API Gateway principal to
   invoke the function.

**Invocation role policy:**
```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": "apigateway:Invoke",
    "Resource": "arn:aws:apigateway:us-east-1::/restapis/abc123/stages/prod/POST/"
  }]
}
```

**IdP Lambda response shape (mandatory fields):**
```json
{
  "Role": "arn:aws:iam::111111111111:role/TransferUserS3Role",
  "HomeDirectory": "/prod-sftp-inbox/alice",
  "HomeDirectoryType": "PATH",
  "Policy": "<session policy JSON string>",
  "PublicKeys": ["ssh-rsa AAAAB3..."]
}
```

Missing fields cause silent auth failures — Transfer Family returns a
generic "authentication failed" with no diagnostic about which field
was wrong.

**create-server with API_GATEWAY:**
```bash
aws transfer create-server \
  --description prod-sftp-vpc-custom-idp \
  --protocols SFTP FTPS \
  --endpoint-type VPC_ENDPOINT \
  --identity-provider-type API_GATEWAY \
  --identity-provider-details Url=https://abc123.execute-api.us-east-1.amazonaws.com/prod/,InvocationRole=arn:aws:iam::111111111111:role/TransferIdPInvocationRole \
  --certificate arn:aws:acm:us-east-1:111111111111:certificate/abc-123 \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-ssh sg-ftps \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole
```

## Directory Service (Managed Microsoft AD) procedure

**Pre-checks:**
1. Directory ID resolves via `ds:describe-directories`.
2. Directory status is ACTIVE.
3. Directory is in the SAME region and VPC as the server.
4. Simple AD is NOT supported — Managed Microsoft AD only.

**create-server with AWS_DIRECTORY_SERVICE:**
```bash
aws transfer create-server \
  --description prod-sftp-ad \
  --protocols SFTP \
  --endpoint-type VPC_ENDPOINT \
  --identity-provider-type AWS_DIRECTORY_SERVICE \
  --identity-provider-details DirectoryId=d-abc123 \
  --domain example.com \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa subnet-bbb \
  --security-group-ids sg-ssh \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole
```

Users sign in with `DOMAIN\username` and their AD password — no SSH
keys required. The Directory Service must be a Managed Microsoft AD in
the same VPC. Simple AD is not supported (deprecated 2025).

## FTPS (public endpoint, partner B2B)

**create-server with FTPS:**
```bash
aws transfer create-server \
  --description prod-ftps-partner \
  --protocols FTPS \
  --endpoint-type PUBLIC \
  --identity-provider-type SERVICE_MANAGED \
  --certificate arn:aws:acm:us-east-1:111111111111:certificate/ftps-cert \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole \
  --tags Key=Partner,Value=acme
```

## AS2 server (B2B app-level messaging)

**create-server with AS2:**
```bash
aws transfer create-server \
  --description prod-as2-b2b \
  --protocols AS2 \
  --endpoint-type VPC_ENDPOINT \
  --identity-provider-type SERVICE_MANAGED \
  --vpc-id vpc-abc123 \
  --subnet-ids subnet-aaa \
  --security-group-ids sg-as2 \
  --logging-role arn:aws:iam::111111111111:role/TransferLoggingRole
```

**Local and partner profiles:**
```bash
aws transfer create-profile \
  --as2-id "MYCORP" \
  --profile-type LOCAL \
  --certificate-ids cert-local \
  --tags Key=Environment,Value=prod

aws transfer create-profile \
  --as2-id "PARTNERACME" \
  --profile-type PARTNER \
  --certificate-ids cert-partner \
  --tags Key=Partner,Value=acme
```

AS2 uses mutual cert-based authentication (RFC 4130). Local profile
holds the private key (in Secrets Manager); partner profile holds the
partner's cert. MDN (Message Disposition Notification) is asynchronous
by default.

## Managed workflow procedure

**Pre-checks:**
1. Workflow ID resolves via `transfer:list-workflows`.
2. Workflow status is ACTIVE.
3. Every step's Lambda/function ARN resolves.
4. Workflow execution role trusts `transfer.amazonaws.com` and has
   `lambda:InvokeFunction` on each step's Lambda.

**Execution role:**
```bash
aws iam create-role --role-name TransferWorkflowExecutionRole \
  --assume-role-policy-document file://transfer-trust.json
aws iam put-role-policy --role-name TransferWorkflowExecutionRole \
  --policy-name InvokeSteps \
  --policy-document '{
    "Version": "2012-10-17",
    "Statement": [{
      "Effect": "Allow",
      "Action": "lambda:InvokeFunction",
      "Resource": "arn:aws:lambda:us-east-1:111111111111:function:process-inbound-file"
    }]
  }'
```

**Create workflow with COPY + TAG + CUSTOM steps:**
```bash
aws transfer create-workflow \
  --description "Process inbound SFTP file" \
  --steps '[
    {"Type":"COPY","CopyStepDetails":{"DestinationFileLocation":{"S3FileLocation":{"Bucket":"prod-processed","Key":"inbound"}},"OverwriteExisting":"TRUE","SourceFileLocation":"${originalFile}"}},
    {"Type":"TAG","TagStepDetails":{"Tags":[{"Key":"Status","Value":"processed"}]}},
    {"Type":"CUSTOM","CustomStepDetails":{"Target":"arn:aws:lambda:us-east-1:111111111111:function:process-inbound-file","TimeoutSeconds":60}}
  ]' \
  --on-exception-steps '[{"Type":"DELETE","DeleteStepDetails":{"SourceFileLocation":"${originalFile}"}}]' \
  --tags Key=Environment,Value=prod
# Returns: { "WorkflowId": "w-abc123" }
```

**Attach to server via OnUpload:**
```bash
aws transfer update-server \
  --server-id s-abc123def456 \
  --workflow-details '{"OnUpload":{"WorkflowId":"w-abc123","ExecutionRole":"arn:aws:iam::111111111111:role/TransferWorkflowExecutionRole"}}'
```

## EFS storage backend

**When to use:** users require POSIX file system semantics (locking,
permissions, large directory trees).

**create-user with EFS:**
```bash
aws transfer create-user \
  --server-id s-abc123def456 \
  --user-name alice \
  --role arn:aws:iam::111111111111:role/TransferUserEFSRole \
  --home-directory-type PATH \
  --home-directory /fs-abc123/alice \
  --posix-profile Uid=1000,Gid=1000
```

IAM role needs `elasticfilesystem:ClientMount`,
`elasticfilesystem:ClientWrite` on the EFS file system ARN. Optional
EFS access point for chroot-like isolation.

## Pre-flight verification commands

```bash
# API Gateway custom IdP deployed and reachable?
curl -X POST -d '{"username":"test","password":"test"}' \
  https://abc123.execute-api.us-east-1.amazonaws.com/prod/ | jq .

# Directory Service ACTIVE and in matching VPC?
aws ds describe-directories --directory-ids d-abc123 \
  --query 'DirectoryDescriptions[0].[Stage,VpcSettings.VpcId]'

# VPC security group inbound on protocol port?
aws ec2 describe-security-groups --group-ids sg-ssh \
  --query 'SecurityGroups[0].IpPermissions[*].[FromPort,ToPort]'

# Workflow status?
aws transfer list-workflows \
  --query 'Workflows[?WorkflowId==`w-abc123`].[WorkflowId,State]'

# Server state?
aws transfer describe-server --server-id s-abc123def456 \
  --query 'Server.[State,EndpointType,IdentityProviderType]'
```
