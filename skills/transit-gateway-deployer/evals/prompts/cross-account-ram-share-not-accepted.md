# Eval prompt: cross-account-ram-share-not-accepted

Design a deployment plan for a cross-account Transit Gateway
topology. Emit the standard VERDICT block.

Requirements:

- TGW owner: account 111111111111, TGW prod-tgw-shared (ASN 64512,
  us-east-1, ACTIVE)
- AutoAcceptSharedAttachments: disable (production posture)
- Consumer account: 222222222222 with VPC vpc-0consumer (subnets
  subnet-0c1, subnet-0c2, subnet-0c3, all available in
  us-east-1a/b/c)
- The consumer expects to create the VPC attachment today

Existing-account context: the TGW owner account has run
`aws ram create-resource-share` to share the TGW with the consumer
account. `aws ram get-resource-shares` returns the share in state
`PENDING` — the consumer account 222222222222 has NOT yet called
`accept-resource-share-invitation`. The consumer account principal
is ready to create the attachment as soon as the share is ACTIVE.

The user assumes they can proceed today.
