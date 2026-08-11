# End-to-End Example: Connect Instance Deployment

A walkthrough showing how to use the `connect-instance-deployer`
skill from invocation through verification. Mirrors the structured-
eval pattern of shipping a concrete worked example per skill.

---

## Scenario

You are provisioning an Amazon Connect instance (SAML identity) with
a Lambda-driven contact flow, Lex V2 IVR, skills-based routing, and
S3 recording storage. The deployment needs:

- Instance: inst-abc123 (my-connect-cc, SAML with Okta)
- Contact flow: inbound-main-flow (InvokeLambda lookup-customer +
  InvokeAmazonLex + branch on department)
- Lambda: lookup-customer
- Lex V2 bot: CustomerService, alias Prod
- Queues: sales-queue, support-queue, default-queue
- Routing profile: tier-1-sales-support (Sales proficiency ≥ 4,
  Support proficiency ≥ 4)
- Phone number: +18005551234 (toll-free, us-east-1)
- Recording storage: S3 connect-recordings-123456789012 with KMS

---

## Step 1 — Invoke the skill

### Option A: Slash command

```
/aws:deploy-connect-instance
```

Then paste the requirements.

### Option B: Natural language

```
You: "Create a Connect contact flow on instance inst-abc123 that
      invokes Lambda lookup-customer and Lex bot CustomerService
      for IVR. Branch on department to sales or support queue.
      SAML identity, Okta. Toll-free number +18005551234."
```

### Option C: CLI routing

```bash
node cli/bin/cli.js route "create a connect contact flow"
```

---

## Step 2 — Skill produces the READY_TO_DEPLOY checklist

```text
CONNECT_INSTANCE: inst-abc123 (my-connect-cc, SAML)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Instance: inst-abc123 (my-connect-cc)
  [✓] Identity mode: SAML (Okta IdP)
  [✓] Directory: N/A
  [✓] Contact flow: flow-def456 (inbound-main-flow, CONTACT_FLOW, all referenced resources verified)
  [✓] Lambda integration: arn:aws:lambda:us-east-1:123456789012:function:lookup-customer (resource policy grants connect.amazonaws.com)
  [✓] Queues: sales-queue-id, support-queue-id, default-queue-id
  [✓] Routing profile: rp-xyz789 (sales queue P1, support queue P2, VOICE concurrency 1)
  [✓] Skill requirements: Sales (proficiency ≥ 4), Support (proficiency ≥ 4)
  [✓] User hierarchy: Sales - North America
  [✓] Phone number: +18005551234 (toll-free, us-east-1)
  [✓] Lex bot: arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod (V2, published, en_US)
  [✓] Voice ID: domain-123 (consent disclosure in flow)
  [✓] Contact Lens: post-call (transcription, sentiment, redaction enabled)
  [✓] Channels: VOICE, CHAT, TASK
  [✓] Recording storage: S3 (connect-recordings-123456789012, KMS key-id abc-123)
  [✓] Tags: Environment=production, Project=sales-cc
VERIFICATION_COMMANDS:
  aws connect describe-instance --instance-id inst-abc123
  aws connect describe-contact-flow --instance-id inst-abc123 --contact-flow-id flow-def456
  aws connect describe-routing-profile --instance-id inst-abc123 --routing-profile-id rp-xyz789
  aws connect describe-phone-number --instance-id inst-abc123 --phone-number-id pn-456
  aws connect list-instance-storage-configs --instance-id inst-abc123
```

---

## Step 3 — Provisioning commands

```bash
# Step 1: Create the instance (SAML identity)
INSTANCE_ID=$(aws connect create-instance \
  --instance-name "my-connect-cc" \
  --IdentityManagementType SAML \
  --InboundCallsEnabled \
  --OutboundCallsEnabled \
  --ClientToken "unique-token-1" \
  --query 'Id' --output text)

# Step 2: Grant Lambda invoke permission to Connect
aws lambda add-permission \
  --function-name lookup-customer \
  --statement-id connect-invoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com \
  --source-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID"

# Step 3: Create queues
SALES_QUEUE_ID=$(aws connect create-queue \
  --instance-id "$INSTANCE_ID" \
  --name "sales-queue" \
  --hours-of-operation-id <hours-of-operation-id> \
  --query 'QueueId' --output text)

SUPPORT_QUEUE_ID=$(aws connect create-queue \
  --instance-id "$INSTANCE_ID" \
  --name "support-queue" \
  --hours-of-operation-id <hours-of-operation-id> \
  --query 'QueueId' --output text)

# Step 4: Create routing profile with skill requirements
ROUTING_PROFILE_ID=$(aws connect create-routing-profile \
  --instance-id "$INSTANCE_ID" \
  --name "tier-1-sales-support" \
  --default-outbound-queue-id "$SALES_QUEUE_ID" \
  --queue-configs "[
    {\"QueueReference\":{\"QueueId\":\"$SALES_QUEUE_ID\",\"Channel\":\"VOICE\"},\"Priority\":1,\"Delay\":0},
    {\"QueueReference\":{\"QueueId\":\"$SUPPORT_QUEUE_ID\",\"Channel\":\"VOICE\"},\"Priority\":2,\"Delay\":0}
  ]" \
  --media-concurrencies '[{"Channel":"VOICE","Concurrency":1}]' \
  --query 'RoutingProfileId' --output text)

# Step 5: Create contact flow with InvokeLambda + InvokeAmazonLex
FLOW_ID=$(aws connect create-contact-flow \
  --instance-id "$INSTANCE_ID" \
  --name "inbound-main-flow" \
  --type CONTACT_FLOW \
  --content "$(cat <<EOF
{
  "Version": "2024-07-30",
  "StartAction": "start",
  "Actions": [
    {"Identifier": "start", "Type": "Branch", "Transitions": {"NextAction": "lookup-customer"}},
    {"Identifier": "lookup-customer", "Type": "Action",
     "Parameters": {"FunctionARN": "arn:aws:lambda:us-east-1:123456789012:function:lookup-customer", "InvocationTimeLimitSeconds": "5"},
     "Transitions": {"NextAction": "lex-ivr",
       "Exceptions": [{"NextAction": "transfer-default", "Error": "Lambda.AccessDenied"},
                      {"NextAction": "transfer-default", "Error": "Lambda.Timeout"}]}},
    {"Identifier": "lex-ivr", "Type": "Action",
     "Parameters": {"BotAliasArn": "arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod", "Intent": "RouteCall", "Slots": {"department": null}},
     "Transitions": {"NextAction": "branch-on-department"}},
    {"Identifier": "branch-on-department", "Type": "Branch",
     "Parameters": {"ComparisonValue": "\$.Lex.slots.department"},
     "Transitions": {"Conditions": [
       {"NextAction": "transfer-sales", "Condition": {"Operator": "Equals", "Value": "Sales"}},
       {"NextAction": "transfer-support", "Condition": {"Operator": "Equals", "Value": "Support"}}]}},
    {"Identifier": "transfer-sales", "Type": "Transfer",
     "Parameters": {"QueueArn": "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID/queue/$SALES_QUEUE_ID"},
     "Transitions": {"NextAction": "end"}},
    {"Identifier": "transfer-support", "Type": "Transfer",
     "Parameters": {"QueueArn": "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID/queue/$SUPPORT_QUEUE_ID"},
     "Transitions": {"NextAction": "end"}},
    {"Identifier": "transfer-default", "Type": "Transfer",
     "Parameters": {"QueueArn": "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID/queue/default-queue-id"},
     "Transitions": {"NextAction": "end"}},
    {"Identifier": "end", "Type": "Terminal", "Parameters": {"Disconnect": true}}
  ]
}
EOF
)" \
  --query 'Id' --output text)

# Step 6: Claim the toll-free number
PHONE_NUMBER_ID=$(aws connect claim-phone-number \
  --instance-id "$INSTANCE_ID" \
  --target-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID" \
  --phone-number-description "Main inbound toll-free" \
  --phone-number-type TOLL_FREE \
  --phone-number +18005551234 \
  --query 'PhoneNumberId' --output text)

# Step 7: Associate S3 recording storage with KMS encryption
aws connect associate-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --resource-type CALL_RECORDINGS \
  --storage-config \
    "{\"S3Config\":{\"BucketName\":\"connect-recordings-123456789012\",\"BucketPrefix\":\"recordings\",\"EncryptionConfig\":{\"EncryptionType\":\"KMS\",\"KeyId\":\"arn:aws:kms:us-east-1:123456789012:key/abc-123\"}},\"StorageType\":\"S3\"}"
```

---

## Step 4 — Post-deployment verification

```bash
# Instance
aws connect describe-instance --instance-id "$INSTANCE_ID"

# Contact flow
aws connect describe-contact-flow \
  --instance-id "$INSTANCE_ID" \
  --contact-flow-id "$FLOW_ID"

# Lambda resource policy
aws lambda get-policy --function-name lookup-customer | grep connect.amazonaws.com

# Routing profile
aws connect describe-routing-profile \
  --instance-id "$INSTANCE_ID" \
  --routing-profile-id "$ROUTING_PROFILE_ID"

# Phone number
aws connect describe-phone-number \
  --instance-id "$INSTANCE_ID" \
  --phone-number-id "$PHONE_NUMBER_ID"

# Storage configs
aws connect list-instance-storage-configs --instance-id "$INSTANCE_ID"

# Lex bot alias (verify published)
aws lexv2-models describe-bot-alias \
  --bot-id <bot-id> \
  --bot-alias-id <alias-id>
```

---

## What the skill catches that a naive provisioning misses

| Configuration | Naive provisioning | Skill output | Why the skill is right |
|---|---|---|---|
| Lambda resource policy | Not configured | connect.amazonaws.com invoke permission | Without it, InvokeLambda returns AccessDenied at run time |
| Lambda exceptions | Not handled | AccessDenied, Timeout, GenericError | Without exceptions, contact is trapped on Lambda failure |
| Routing profile | Queue priority only | Skill requirements + proficiency | Without skills, routing degrades to queue-priority |
| Lex version | Lex V1 (deprecated) | Lex V2 via InvokeAmazonLex | V1 is on deprecation path; V2 is current |
| Lex alias | DRAFT | Published Prod alias | Connect invokes published aliases; DRAFT can break flow |
| Phone number region | Mismatch | Region matches instance | US toll-free does not work in EU instances |
| Recording storage | Plain S3 | S3 + KMS encryption | Without KMS, recordings are unencrypted at rest |

---

## Related artifacts

- **Skill definition:** `skills/connect-instance-deployer/SKILL.md`
- **Contact flow JSON and Lambda guide:** `skills/connect-instance-deployer/references/contact-flow-json-and-lambda.md`
- **Routing and Lex integration guide:** `skills/connect-instance-deployer/references/routing-and-lex-integration.md`
- **Slash command:** `commands/aws/deploy-connect-instance.md`
- **Eval suite:** `skills/connect-instance-deployer/evals/evals.json`
- **Legacy test cases:** `skills/connect-instance-deployer/eval/test-cases.yaml`
