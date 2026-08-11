---
name: connect-instance-deployer
description: >-
  Provisions Amazon Connect instances, contact flows, queues, routing
  profiles, phone numbers, and integrations with production defaults.
  Instance creation with three identity-management modes (SAML-based
  federation, Amazon Connect directory, existing AWS Directory Service
  directory). Contact flows authored as JSON specs (drag-and-drop in
  the console, programmatic via AWS CLI / CloudFormation) with AWS
  Lambda function invoke blocks (InvokeLambda), SetAttributes,
  branching (CheckHoursOfOperation, CheckPhoneNumber,
  CheckStoredCustomerInput, Compare), queue transfers
  (TransferToQueue, TransferToFlow), and Lex bot integration
  (InvokeAmazonLex). Queues with quick-connect lists, hold-flow
  configuration, and outbound caller ID. Routing profiles with skill
  requirements (skill name + proficiency level), queue associations,
  and agent hierarchy. Phone number claim (toll-free, DID,
  toll-free-DID) and DID porting. Real-time and historical metrics
  (real-time: ContactFlow, RoutingProfile, Queue, Agent; historical:
  ContactTraceRecord, AgentPerformance, ContactSummary). Amazon
  Connect Voice ID (speaker enrollment, fraud risk). Contact Lens for
  Connect (real-time sentiment, post-call transcription, post-call
  summary, sensitive-data redaction). Chat and voice channels, task
  management (CreateTask, UpdateTask), S3 recording storage with KMS
  encryption, Amazon Lex bot integration for IVR (intent elicitation,
  slot filling). Emits a READY_TO_DEPLOY checklist with verification
  commands. Use when creating a Connect instance, authoring a contact
  flow with Lambda invoke blocks, configuring routing profile skill
  requirements, claiming a phone number, integrating a Lex bot for
  IVR, enabling Voice ID, configuring Contact Lens, setting up S3
  recording storage, or wiring real-time metrics. Triggers: create
  Connect instance, SAML identity, contact flow JSON, Lambda invoke
  block, queue, routing profile skill, claim phone number toll-free,
  DID porting, Lex bot IVR, Voice ID enrollment, Contact Lens
  sentiment, Connect task, S3 recording KMS.
version: 0.1.0
author: Jacky Chan — AWS Community Builder
license: Apache-2.0
compatibility: >-
  Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf,
  Codex, Gemini). For live deployment: AWS CLI v2 with connect access
  (and connect-contact-lens for Contact Lens, lexv2-runtime for Lex
  bot testing, s3 for recording storage verification, kms for key
  policy). Works with Terraform aws_connect_instance,
  aws_connect_contact_flow, aws_connect_queue, aws_connect_routing_profile,
  aws_connect_phone_number, aws_connect_user, aws_connect_user_hierarchy_group
  resources and CloudFormation AWS::Connect::* templates.
keywords:
  - aws
  - connect
  - amazon connect
  - contact center
  - contact flow
  - lambda invoke
  - queue
  - routing profile
  - skill requirement
  - phone number
  - toll-free
  - did
  - saml
  - directory
  - voice id
  - contact lens
  - sentiment
  - transcription
  - chat
  - voice
  - task
  - lex bot
  - ivr
  - recording
  - s3
  - kms
  - real-time metrics
  - historical metrics
tags:
  - aws
  - connect
  - appintegration
  - deploy
  - contact-center
  - contact-flow
  - routing
  - voice
dependencies:
  - aws-orchestrator
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: true
  phase: 1
  supports_pipeline: true
  entry_point: false
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: "READY_TO_DEPLOY | PREREQUISITES_MISSING"
  version: 0.1.0
  author: "Jacky Chan — AWS Community Builder"
  tags:
    - aws
    - connect
    - appintegration
    - deploy
    - contact-center
    - contact-flow
    - routing
    - voice
  dependencies:
    - aws-orchestrator
  keywords:
    - create connect instance
    - saml identity
    - contact flow json
    - lambda invoke block
    - queue and routing profile
    - routing profile skill
    - claim phone number toll-free
    - did porting
    - lex bot ivr
    - voice id enrollment
    - contact lens sentiment
    - connect task
    - s3 recording kms
  when_to_use: >-
    Invoke when the user wants to create an Amazon Connect instance
    (with SAML, Connect directory, or existing AWS Directory Service
    directory identity mode), author a contact flow with Lambda invoke
    blocks or Lex integration, configure a routing profile with skill
    requirements (skill name + proficiency), claim a phone number
    (toll-free, DID, toll-free-DID), set up queues with quick-connect
    lists, integrate Amazon Lex V2 for IVR (intent elicitation, slot
    filling), enable Voice ID speaker enrollment, enable Contact Lens
    for sentiment / transcription / redaction, configure chat and
    voice channels, manage tasks, set up S3 recording storage with KMS
    encryption, or wire real-time and historical metrics. Do NOT
    invoke for Amazon Chime SDK (use chime skills), Amazon WorkSpaces
    (use workspaces skills), or standalone Amazon Lex bot deployment
    (use lex skills).
---

# Connect Instance Deployer

An AWS CloudOps agent skill that provisions Amazon Connect instances,
contact flows, queues, routing profiles, phone numbers, and channel
integrations with contact-center-best-practice defaults. The skill
walks the operator through identity-mode selection (SAML, Connect
directory, existing AWS Directory Service directory), contact-flow
authoring (JSON spec with Lambda invoke blocks, branching, queue
transfers, Lex IVR), routing-profile skill requirements (skill name +
proficiency level), phone number claim (toll-free, DID, toll-free-
DID), Voice ID enrollment, Contact Lens configuration, S3 recording
storage with KMS, and metrics. The skill captures topology and
routing decisions, explains why each default matters, surfaces the
three expert heuristics (contact flow JSON with Lambda invoke blocks,
routing profile skill requirements, Lex bot integration for IVR),
and emits a READY_TO_DEPLOY checklist with copy-pasteable
verification commands.

## Activation keywords

create Connect instance, SAML identity, contact flow JSON, Lambda
invoke block, queue and routing profile, routing profile skill,
claim phone number toll-free, DID porting, Lex bot IVR, Voice ID
enrollment, Contact Lens sentiment, Connect task, S3 recording KMS,
quick-connect, agent hierarchy, real-time metrics.

## STRICT output contract

When this skill is invoked with a Connect-provisioning request
(create an instance, author a contact flow, configure a routing
profile, claim a phone number, integrate a Lex bot, enable Voice
ID, configure Contact Lens, set up S3 recording, or a partial
configuration), the agent MUST respond with the READY_TO_DEPLOY
checklist defined in the "Output format" section using the literal
all-caps labels `CONNECT_INSTANCE:`, `VERDICT:`, `CHECKLIST:`, and
`VERIFICATION_COMMANDS:`. Do NOT preface the checklist with prose,
headings, or disclaimers — emit the block as the first lines of the
response. This contract is what assertion-based evals and downstream
provisioning pipelines rely on; deviating from the literal labels
breaks automation silently.

If any prerequisite is missing, the verdict is `PREREQUISITES_MISSING`
with a specific gap citation in the checklist (marked `[✗]`), and
`READY_TO_DEPLOY` MUST NOT also appear.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Instance creation (SAML, Connect directory, existing dir) | Identity mode |
| Step 2 — Contact flow JSON (drag-and-drop, programmatic) | Authoring flows |
| Step 3 — Lambda function integration (InvokeLambda block) | Dynamic IVR logic |
| Step 4 — Queues and quick-connect lists | Routing targets |
| Step 5 — Routing profiles (skills, proficiency, queue associations) | Agent routing |
| Step 6 — Agent hierarchy | Org structure |
| Step 7 — Phone number claim (toll-free, DID) | Inbound numbers |
| Step 8 — Skills-based routing | Skill matching |
| Step 9 — Amazon Lex bot integration (IVR) | Conversational IVR |
| Step 10 — Voice ID (speaker enrollment, fraud) | Caller authentication |
| Step 11 — Contact Lens (sentiment, transcription, redaction) | Quality analytics |
| Step 12 — Chat, voice, task channels | Channel coverage |
| Step 13 — S3 recording storage (KMS encryption) | Call recordings |
| Step 14 — Real-time and historical metrics | Operations |
| Step 15 — Recent features | Latest |
| NEVER do these things | Review before signing off |
| Output format | The literal checklist template |
| references/contact-flow-json-and-lambda.md | Contact flow + Lambda detail |
| references/routing-and-lex-integration.md | Routing profile + Lex detail |

## Mindset

**One-line takeaway:** An Amazon Connect instance is a contact-flow-
centric contact center. Every inbound contact traverses a contact
flow (a JSON spec DAG of Action / Branch / Terminal blocks). Lambda
functions invoked from the flow provide dynamic IVR logic (looking
up the caller, deciding routing). Routing profiles match agents to
contacts via skills (skill name + proficiency level). Lex bots
handle conversational IVR (intent elicitation, slot filling) inside
the flow.

Three misconceptions dominate Connect misdesign at provisioning time:

- **"A contact flow is just an IVR menu."** It is not. A contact
  flow is a JSON spec DAG of typed blocks: Action (PlayPrompt,
  InvokeLambda, TransferToQueue, InvokeAmazonLex), Branch
  (CheckHoursOfOperation, Compare, EvaluateAttribute), and Terminal
  (Disconnect, TransferToQueue, TransferToFlow). The drag-and-drop
  console edits this JSON; programmatic deployments (CLI,
  CloudFormation, Terraform) author the JSON directly. Treating it
  as a flat menu misses Lambda-driven dynamic routing and Lex-driven
  conversational IVR.

- **"A routing profile is just a queue assignment."** It is not. A
  routing profile associates an agent with multiple queues AND
  specifies the SKILL REQUIREMENTS (skill name + proficiency level)
  that determine which contacts the agent handles. Without skills,
  routing is pure queue-and-priority. With skills, contacts route to
  the agent with the highest proficiency matching the contact's
  required skill. Misdesigning skill requirements produces "the
  contact routed to the wrong agent" tickets.

- **"IVR means pressing 1 or 2."** Modern IVR is conversational via
  Amazon Lex V2. The InvokeAmazonLex block in the contact flow
  invokes a Lex bot to elicit an intent and fill slots through
  natural-language conversation. The Lex bot returns an intent and
  slots to the flow, which branches on those values. Treating IVR as
  touch-tone only misses the conversational IVR pattern.

## Configuration dependency graph (novel heuristic)

Connect configurations are NOT independent. The instance must exist
before flows; flows reference queues and Lambda functions; routing
profiles reference queues and skills; phone numbers are claimed at
the instance level. Use this graph to sequence provisioning.

| Configuration | Hard dependencies (silent failure without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Instance | Identity mode selected (SAML, Connect dir, existing dir) | instance Alias is immutable; identity mode is set at creation | contact flows, queues, routing profiles, phone numbers, users |
| Contact flow | Instance exists; flow JSON valid; referenced queues/Lambda exist | flow JSON with dangling block references creates at API but fails at run time | inbound contact handling |
| Lambda function | Function deployed in same region; resource policy grants Connect invoke permission | Connect calls Lambda via `connect.amazonaws.com`; without resource policy, Lambda invocations fail with AccessDenied | dynamic IVR logic |
| Queue | Instance exists; HoursOfOperation defined; quick-connect list optional | queue with no agents assigned via routing profile holds contacts indefinitely | contact routing target |
| Routing profile | Instance exists; queues defined; skills defined (if used) | agent without routing profile cannot log in to CCP | agent routing |
| Skill | Instance exists; skill name unique per instance | skill proficiency is set on the agent, not the skill | skills-based routing |
| User (agent) | Instance exists; routing profile assigned; security profile assigned; user hierarchy group optional | SAML users are managed in the IdP; Connect-directory users are managed via CreateUser API | login to CCP, handle contacts |
| Phone number | Instance exists; claimed via ClaimedPhoneNumber or via porting | phone number is per-region; toll-free vs DID affects inbound calling line | inbound voice channel |
| Lex bot (V2) | Dialect ID set on bot; bot published; Connect integrated via LexBotAssociation block in flow | Lex V2 integration via `InvokeAmazonLex` block in flow (Lex V1 is deprecated path) | conversational IVR |
| Voice ID | Instance exists; Voice ID domain created; consent disclosure in flow | Voice ID enrollment requires caller consent at first call | caller authentication, fraud detection |
| Contact Lens | Instance exists; language model selected; sentiment / redaction settings | post-call analytics vs real-time (different feature sets) | sentiment, transcription, redaction |
| Recording (S3 + KMS) | S3 bucket with KMS encryption; KMS key policy grants Connect; instance-associated | recordings are encrypted at rest with KMS; without key policy Connect cannot write | call recording storage |
| Real-time metrics | Instance exists; metric stream configured (optional) | real-time metrics are instance-built-in; custom metrics via Kinesis | contact center operations |
| Historical metrics | Instance exists; ContactTraceRecord (CTR) export configured | CTRs available for 24 months; longer retention requires S3 export | historical analytics |

**The contact-flow-block-references row is the one a baseline model
misses.** A model that authors a contact flow JSON without
verifying that referenced queues, Lambda functions, and Lex bots
exist will produce a flow that creates at the API but fails at run
time when a contact hits the dangling reference. The procedure below
forces an explicit pre-flight check on every referenced resource.

**Cross-dependency gotchas:**
- A contact flow referencing a non-existent queue (or wrong queue
  ARN) will create successfully but every contact will fail at the
  TransferToQueue block.
- A Lambda function without a resource policy granting
  `connect.amazonaws.com` invoke permission will return
  AccessDenied when the flow runs.
- A routing profile without skill requirements produces pure queue-
  priority routing (no skills-based matching).
- Phone numbers are per-region. A US toll-free number does not work
  in EU instances.
- Amazon Lex V1 is on a deprecation path; use Lex V2 via the
  `InvokeAmazonLex` block (Lex V1 used a different block name).

## Expert heuristic: contact flow JSON with Lambda invoke blocks

A baseline model treats the contact flow as a touch-tone IVR. The
correct heuristic recognizes that the flow is a DAG of typed blocks
and the InvokeLambda block is the integration point for dynamic IVR
logic.

```text
Sample flow JSON structure (DAG):
  Start → CheckHoursOfOperation
                     ├── (Open) → InvokeLambda(lookup_customer)
                     │             ├── Return → PlayPrompt(greeting) → InvokeAmazonLex(intent=route_call)
                     │             │                              ├── intent=Sales → TransferToQueue(Sales)
                     │             │                              └── intent=Support → TransferToQueue(Support)
                     │             └── Error → TransferToQueue(Default)
                     └── (Closed) → PlayPrompt(closed) → Disconnect

InvokeLambda block JSON:
  {
    "Identifier": "lookup_customer",
    "Type": "Action",
    "Parameters": {
      "FunctionARN": "arn:aws:lambda:us-east-1:123456789012:function:lookup-customer",
      "InvocationTimeLimitSeconds": "5"
    },
    "Transitions": {
      "NextAction": "play-greeting",
      "Exceptions": [
        {"NextAction": "transfer-default", "Error": "Lambda.AccessDenied"},
        {"NextAction": "transfer-default", "Error": "Lambda.Timeout"}
      ]
    }
  }
```

**Key implication:** Lambda invocations from Connect flows MUST have
exceptions handled (AccessDenied, Timeout, GenericError). Without
exceptions, a Lambda failure traps the contact in the flow with no
graceful fallback. Also: the Lambda resource policy MUST grant
`connect.amazonaws.com` invoke permission with the instance ARN as
the source.

## Expert heuristic: routing profile skill requirements

A baseline model treats routing profiles as queue priorities. The
correct heuristic recognizes that skill requirements (skill name +
proficiency level) determine which contacts route to which agents.

```text
Routing profile with skill requirements:
  Queues:
    ├── Sales queue (priority 1, delay 0)
    └── Support queue (priority 2, delay 0)

  Agent A:
    Skills:
      ├── "Sales"     → proficiency 5
      └── "Support"   → proficiency 3
  Agent B:
    Skills:
      └── "Support"   → proficiency 5

Contact X (required skill: Sales, proficiency ≥ 4):
  → Routes to Agent A (Sales proficiency 5 ≥ 4)
  → Agent B is ineligible (no Sales skill)

Contact Y (required skill: Support, proficiency ≥ 4):
  → Routes to Agent B (Support proficiency 5 ≥ 4)
  → Agent A is eligible as backup (Support proficiency 3 < 4 — NOT eligible for this contact)
```

**Key implication:** skills are defined at the instance level,
proficiency is set on each agent per skill, and contacts specify the
required skill + proficiency via the contact flow (SetAttributes or
TransferToQueue with the skill). Without all three, skills-based
routing silently degrades to queue-priority routing.

## Expert heuristic: Lex bot integration for IVR

A baseline model treats IVR as touch-tone menus. The correct
heuristic recognizes that the InvokeAmazonLex block in the contact
flow invokes a Lex V2 bot for conversational IVR.

```text
Contact flow with Lex IVR:
  Start → PlayPrompt("How can I help you?")
       → InvokeAmazonLex(bot=CustomerService, intent=RouteCall)
            ├── Slots: { "department": null }
            ├── Lex elicits slots via conversation:
            │     "Are you calling about Sales or Support?"
            │     → Caller: "Sales"
            │     → Slot filled: { "department": "Sales" }
            └── Lex returns intent=RouteCall, slots={department: Sales}
       → Branch on slot value:
            ├── department == "Sales" → TransferToQueue(Sales)
            └── department == "Support" → TransferToQueue(Support)
            └── department == unknown → PlayPrompt("Sorry, didn't get that") → Loop back to InvokeAmazonLex
```

**Key implication:** the Lex bot must be a published version (not
DRAFT) and the bot's locale must match the Connect instance language.
The InvokeAmazonLex block uses the bot alias (not the bot ID alone).
Bot responses can be slow on cold paths; set the Lex session
timeout and consider Lambda fallbacks for timeout scenarios.

## Prerequisites (verify before provisioning)

Before emitting provisioning commands, verify these prerequisites. If
any are missing, the verdict is **PREREQUISITES_MISSING**.

| Prerequisite | Why it matters | How to verify |
|---|---|---|
| Instance alias unique | Alias is immutable once set | `aws connect list-instances` (no name collision) |
| Identity mode decided (SAML, Connect dir, existing dir) | Identity mode is set at instance creation | Confirm via planning conversation |
| SAML metadata (if SAML) | SAML federation needs IdP metadata | Verify metadata document from IdP |
| AWS Directory Service directory ID (if existing dir) | Existing-dir mode needs a directory ID | `aws ds describe-directories` |
| Service-linked role for Connect | Connect needs service-linked role (auto-created on first use) | `aws iam get-role --role-name AWSServiceRoleForAmazonConnect` |
| Lambda functions deployed (if referenced by flows) | Flow with dangling Lambda reference fails at run time | `aws lambda get-function --function-name <name>` |
| Lambda resource policy grants Connect invoke | Without it, Lambda invocations from flows fail | `aws lambda get-policy --function-name <name>` (look for `connect.amazonaws.com` principal) |
| Lex V2 bot published (if used for IVR) | Connect invokes published bot alias | `aws lexv2-models describe-bot-alias --bot-id <id> --bot-alias-id <id>` |
| S3 bucket for recordings exists with KMS encryption | Recording storage requires S3 + KMS | `aws s3api get-bucket-encryption` and `aws kms describe-key` |
| KMS key policy grants Connect | Without key policy, recordings cannot be encrypted | Verify policy via `aws kms get-key-policy` |
| IAM permissions | Operator needs connect:CreateInstance, CreateContactFlow, etc. | `aws iam get-role-policy` or check attached policies |
| Phone number quota | Each instance has a phone number quota (soft limit) | `aws service-quotas get-service-quota --service-code connect --quota-code L-...` |

If any prerequisite is missing, output `VERDICT: PREREQUISITES_MISSING`
and cite the specific gap.

## Step 1 — Instance creation (SAML, Connect directory, existing directory)

Amazon Connect supports three identity-management modes:

| Mode | Identity source | Use case |
|---|---|---|
| `SAML` | External IdP via SAML 2.0 (Okta, Azure AD, etc.) | Enterprise SSO |
| `CONNECT_MANAGED` | Amazon Connect directory (built-in user pool) | Standalone; small teams |
| `EXISTING_DIRECTORY` | Existing AWS Directory Service directory | AD-integrated enterprises |

**Create instance (SAML):**

```bash
INSTANCE_ID=$(aws connect create-instance \
  --instanceName "my-connect-cc" \
  --IdentityManagementType SAML \
  --InboundCallsEnabled \
  --OutboundCallsEnabled \
  --ClientToken "unique-token-1" \
  --query 'Id' --output text)
```

**Create instance (Connect directory):**

```bash
INSTANCE_ID=$(aws connect create-instance \
  --InstanceName "my-connect-cc" \
  --IdentityManagementType CONNECT_MANAGED \
  --DirectoryId "" \
  --InboundCallsEnabled \
  --OutboundCallsEnabled \
  --ClientToken "unique-token-2" \
  --query 'Id' --output text)
```

**Create instance (existing directory):**

```bash
INSTANCE_ID=$(aws connect create-instance \
  --InstanceName "my-connect-cc" \
  --IdentityManagementType EXISTING_DIRECTORY \
  --DirectoryId d-1234567890 \
  --InboundCallsEnabled \
  --OutboundCallsEnabled \
  --ClientToken "unique-token-3" \
  --query 'Id' --output text)
```

**Verify:**

```bash
aws connect describe-instance --instance-id "$INSTANCE_ID"
```

## Step 2 — Contact flow JSON (drag-and-drop, programmatic)

Contact flows are JSON specs. The drag-and-drop console edits this
JSON; programmatic deployments author it directly via
`create-contact-flow` with a flow `Content` (stringified JSON).

**Block types:**

| Category | Block types | Purpose |
|---|---|---|
| Action | PlayPrompt, InvokeLambda, InvokeAmazonLex, TransferToQueue, TransferToFlow, SetAttributes, SetRecordingBehavior, StartMediaStreaming | Perform an action |
| Branch | CheckHoursOfOperation, CheckPhoneNumber, CheckStoredCustomerInput, Compare, EvaluateAttribute, GetCustomerInput, Loop | Conditional logic |
| Transfer | TransferToQueue, TransferToFlow, TransferToAgent | Hand-off |
| Terminal | Disconnect | End call |

**Sample contact flow (Lambda lookup + Lex IVR + queue transfer):**

```bash
aws connect create-contact-flow \
  --instance-id "$INSTANCE_ID" \
  --name "inbound-main-flow" \
  --type CONTACT_FLOW \
  --description "Main inbound flow with Lambda lookup and Lex IVR" \
  --content "$(cat <<'EOF'
{
  "Version": "2024-07-30",
  "StartAction": "start",
  "Actions": [
    {"Identifier": "start", "Type": "Branch", "Parameters": {}, "Transitions": {"NextAction": "lookup-customer"}},
    {"Identifier": "lookup-customer",
     "Type": "Action",
     "Parameters": {
       "FunctionARN": "arn:aws:lambda:us-east-1:123456789012:function:lookup-customer",
       "InvocationTimeLimitSeconds": "5"
     },
     "Transitions": {
       "NextAction": "lex-ivr",
       "Exceptions": [
         {"NextAction": "transfer-default", "Error": "Lambda.AccessDenied"},
         {"NextAction": "transfer-default", "Error": "Lambda.Timeout"}
       ]
     }},
    {"Identifier": "lex-ivr",
     "Type": "Action",
     "Parameters": {
       "BotAliasArn": "arn:aws:lex:us-east-1:123456789012:bot-alias/ABC123:DEF456",
       "Intent": "RouteCall",
       "Slots": {"department": null}
     },
     "Transitions": {"NextAction": "branch-on-department"}},
    {"Identifier": "branch-on-department",
     "Type": "Branch",
     "Parameters": {"ComparisonValue": "$.Lex.slots.department"},
     "Transitions": {
       "NextAction": "transfer-sales",
       "Conditions": [{"NextAction": "transfer-sales", "Condition": {"Operator": "Equals", "Value": "Sales"}},
                      {"NextAction": "transfer-support", "Condition": {"Operator": "Equals", "Value": "Support"}}]
     }},
    {"Identifier": "transfer-sales",
     "Type": "Transfer",
     "Parameters": {"QueueArn": "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID/queue/sales-queue-id"},
     "Transitions": {"NextAction": "end"}},
    {"Identifier": "transfer-support",
     "Type": "Transfer",
     "Parameters": {"QueueArn": "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID/queue/support-queue-id"},
     "Transitions": {"NextAction": "end"}},
    {"Identifier": "transfer-default",
     "Type": "Transfer",
     "Parameters": {"QueueArn": "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID/queue/default-queue-id"},
     "Transitions": {"NextAction": "end"}},
    {"Identifier": "end", "Type": "Terminal", "Parameters": {"Disconnect": true}}
  ]
}
EOF
)"
```

**Verify:**

```bash
aws connect describe-contact-flow --instance-id "$INSTANCE_ID" --contact-flow-id <flow-id>
aws connect start-test-contact-flow --instance-id "$INSTANCE_ID" --contact-flow-id <flow-id>
```

## Step 3 — Lambda function integration (InvokeLambda block)

Connect invokes Lambda functions via the `InvokeLambda` block in a
contact flow. The Lambda receives a Connect event with contact
attributes and returns a JSON response that updates contact
attributes.

**Lambda function (lookup customer by phone):**

```python
import json
import boto3

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Customers')

def lambda_handler(event, context):
    phone = event['Details']['ContactData']['CustomerEndpoint']['Address']
    response = table.get_item(Key={'phone': phone})
    customer = response.get('Item', {})
    return {
        'customer_id': customer.get('id', 'unknown'),
        'loyalty_tier': customer.get('tier', 'standard'),
        'Name': customer.get('name', 'Valued Customer')
    }
```

**Lambda resource policy (grant Connect invoke permission):**

```bash
aws lambda add-permission \
  --function-name lookup-customer \
  --statement-id connect-invoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com \
  --source-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID"
```

**Verify:**

```bash
aws lambda get-policy --function-name lookup-customer | grep connect.amazonaws.com
```

**Common mistake:** forgetting the Lambda resource policy. Without
it, the InvokeLambda block returns `Lambda.AccessDenied` at run time.

## Step 4 — Queues and quick-connect lists

Queues are routing targets. Each queue has an HoursOfOperation,
quick-connect list (for transfers), hold-flow configuration, and
outbound caller ID.

```bash
QUEUE_ID=$(aws connect create-queue \
  --instance-id "$INSTANCE_ID" \
  --name "sales-queue" \
  --description "Sales inbound queue" \
  --hours-of-operation-id <hours-of-operation-id> \
  --max-contacts 10 \
  --outbound-caller-id-number-id <phone-number-id> \
  --tags Project=sales \
  --query 'QueueId' --output text)
```

**Quick-connect (for transfer targets within the queue):**

```bash
aws connect create-quick-connect \
  --instance-id "$INSTANCE_ID" \
  --name "sales-escalation" \
  --quick-connect-config '{
    "QuickConnectType": "QUEUE",
    "QueueConfig": {"QueueId": "'"$QUEUE_ID"'", "ContactFlowId": "<escalation-flow-id>"}
  }'
```

**Verify:**

```bash
aws connect describe-queue --instance-id "$INSTANCE_ID" --queue-id "$QUEUE_ID"
```

## Step 5 — Routing profiles (skills, proficiency, queue associations)

A routing profile associates an agent with queues and (optionally)
defines skill requirements.

```bash
ROUTING_PROFILE_ID=$(aws connect create-routing-profile \
  --instance-id "$INSTANCE_ID" \
  --name "tier-1-sales-support" \
  --description "Tier-1 agents handling Sales and Support" \
  --default-outbound-queue-id "$QUEUE_ID" \
  --queue-configs '[{"QueueReference":{"QueueId":"'"$SALES_QUEUE_ID"'","Channel":"VOICE"},"Priority":1,"Delay":0},{"QueueReference":{"QueueId":"'"$SUPPORT_QUEUE_ID"'","Channel":"VOICE"},"Priority":2,"Delay":0}]' \
  --media-concurrencies '[{"Channel":"VOICE","Concurrency":1}]' \
  --tags Project=tier1 \
  --query 'RoutingProfileId' --output text)
```

**Skill requirements (defined per-contact via attributes or per-queue):**
Skills are defined at the instance level:

```bash
SALES_SKILL_ID=$(aws connect create-routing-profile ... ) # skills defined elsewhere
# Skills are managed via aws connect describe-instance / instance-store APIs
# Skill proficiency is set on the user via CreateUser / UpdateUserRoutingProfile
```

**Verify:**

```bash
aws connect describe-routing-profile --instance-id "$INSTANCE_ID" --routing-profile-id "$ROUTING_PROFILE_ID"
```

## Step 6 — Agent hierarchy

Agent hierarchy groups agents for routing and reporting (e.g., by
region, business unit, team).

```bash
HIERARCHY_GROUP_ID=$(aws connect create-user-hierarchy-group \
  --instance-id "$INSTANCE_ID" \
  --name "Sales - North America" \
  --parent-group-id <parent-group-id-or-omit> \
  --query 'HierarchyGroupId' --output text)
```

**Verify:**

```bash
aws connect describe-user-hierarchy-group --instance-id "$INSTANCE_ID" --hierarchy-group-id "$HIERARCHY_GROUP_ID"
```

## Step 7 — Phone number claim (toll-free, DID)

Connect supports claiming phone numbers via `claim-phone-number`
(take from AWS pool) or `create-task` for porting.

**Claim toll-free number:**

```bash
PHONE_NUMBER_ID=$(aws connect claim-phone-number \
  --instance-id "$INSTANCE_ID" \
  --target-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID" \
  --phone-number-description "Main inbound toll-free" \
  --phone-number-type TOLL_FREE \
  --phone-number +18005551234 \
  --tags Project=inbound \
  --query 'PhoneNumberId' --output text)
```

**Claim DID (Direct Inward Dialing):**

```bash
aws connect claim-phone-number \
  --instance-id "$INSTANCE_ID" \
  --target-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID" \
  --phone-number-type DID \
  --phone-number +12065551234
```

**Porting a number:** use the Connect console or
`aws connect create-task` to start the porting process. Porting
requires a Letter of Authorization (LOA) and may take 2-4 weeks.

**Verify:**

```bash
aws connect describe-phone-number --instance-id "$INSTANCE_ID" --phone-number-id "$PHONE_NUMBER_ID"
```

## Step 8 — Skills-based routing

Skills are defined at the instance level. Each user has skill
proficiencies (skill ID + proficiency level). Contacts specify
required skills via contact attributes or queue configuration.

| Element | Where it lives | Example |
|---|---|---|
| Skill | Instance (defined once) | "Sales", proficiency levels 1-5 |
| Skill proficiency | User (per-agent) | Agent A: Sales=5, Support=3 |
| Required skill | Contact (via SetAttributes or TransferToQueue) | Contact X: Sales, proficiency ≥ 4 |

**Create skill:**

```bash
# Skills are managed via the instance user-provisioning API
# (skill_id, name). The exact API surface depends on the
# Connect version — verify via aws connect describe-instance.
```

Skills are typically defined via the Connect console. Once defined,
agents are assigned proficiencies via `create-user` /
`update-user-routing-profile`.

## Step 9 — Amazon Lex bot integration (IVR)

Lex V2 bots are integrated via the InvokeAmazonLex block in the
contact flow. The bot elicits an intent and fills slots through
conversation, then returns intent + slots to the flow.

**Prerequisites:**
- Lex V2 bot exists with at least one published alias (not DRAFT).
- Bot's locale matches the Connect instance language.
- Lex bot has IAM permission for Connect to invoke (configured at
  integration time, often implicit).

**Sample Lex V2 bot invocation (in contact flow):**

```json
{
  "Identifier": "lex-ivr",
  "Type": "Action",
  "Parameters": {
    "BotAliasArn": "arn:aws:lex:us-east-1:123456789012:bot-alias/ABC123:DEF456",
    "Intent": "RouteCall",
    "Slots": {"department": null},
    "SessionAttributes": {"caller_id": "$.CustomerEndpoint.Address"}
  },
  "Transitions": {
    "NextAction": "branch-on-department",
    "Exceptions": [{"NextAction": "transfer-default", "Error": "Lex.Timeout"}]
  }
}
```

**Verify Lex bot:**

```bash
aws lexv2-models describe-bot-alias --bot-id <bot-id> --bot-alias-id <alias-id>
aws lexv2-runtime recognize-text --bot-id <bot-id> --bot-alias-id <alias-id> --locale-id en_US --text "I need sales help"
```

## Step 10 — Voice ID (speaker enrollment, fraud)

Amazon Connect Voice ID authenticates callers by voice biometrics.

**Prerequisites:**
- Voice ID domain created in the instance.
- Consent disclosure in the contact flow (legal requirement).
- Opt-in/opt-out handling for callers.

**Enable Voice ID in the flow:**

```json
{
  "Identifier": "voice-id-enroll",
  "Type": "Action",
  "Parameters": {
    "VoiceIdDomainId": "<domain-id>",
    "VoiceIdOperation": "ENROLL_OR_AUTHENTICATE"
  },
  "Transitions": {
    "NextAction": "branch-on-voice-id-result",
    "Conditions": [
      {"NextAction": "high-confidence", "Condition": {"VoiceIdResult": "AUTHENTICATED_HIGH"}},
      {"NextAction": "low-confidence", "Condition": {"VoiceIdResult": "AUTHENTICATED_LOW"}},
      {"NextAction": "fraud-risk", "Condition": {"VoiceIdResult": "FRAUD_RISK_DETECTED"}}
    ]
  }
}
```

**Verify:**

```bash
aws connect describe-instance --instance-id "$INSTANCE_ID" | grep -i voice
```

## Step 11 — Contact Lens (sentiment, transcription, redaction)

Contact Lens provides post-call and real-time analytics.

| Feature | Mode | Use case |
|---|---|---|
| Real-time sentiment | Real-time | Supervisor alerts on negative sentiment |
| Post-call transcription | Post-call | Searchable call transcripts |
| Post-call summary | Post-call | Auto-generated issue + outcome summary |
| Sensitive-data redaction | Post-call | Mask credit card / SSN in transcript |
| Categories | Both | Auto-tag contacts by keyword / sentiment pattern |

**Enable Contact Lens:**

```bash
aws connect update-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --association-id <association-id> \
  --resource-type CONTACT_LENS
```

**Real-time rules (post-call categories):**

```bash
aws connect create-contact-flow ... # (Contact Lens rules are configured in the console)
```

## Step 12 — Chat, voice, task channels

Connect supports three channels: VOICE, CHAT, TASK.

| Channel | Provisioning |
|---|---|
| VOICE | Phone number claimed + contact flow |
| CHAT | Chat widget configured on website / mobile; chat contact flow |
| TASK | Task template created; task contact flow |

**Create task template:**

```bash
aws connect create-task-template \
  --instance-id "$INSTANCE_ID" \
  --name "follow-up-task" \
  --description "Follow-up task after support call" \
  --contact-flow-id <task-flow-id> \
  --self-assign-flow-id <self-assign-flow-id> \
  --fields '[{"Description":"Reason for follow-up","Id":"reason","Type":"TEXT"}]' \
  --status ACTIVE
```

**Verify:**

```bash
aws connect describe-task-template --instance-id "$INSTANCE_ID" --task-template-id <id>
```

## Step 13 — S3 recording storage (KMS encryption)

Call recordings are stored in S3 with KMS encryption.

**S3 bucket with KMS encryption:**

```bash
aws s3api create-bucket \
  --bucket connect-recordings-123456789012 \
  --region us-east-1

aws s3api put-bucket-encryption \
  --bucket connect-recordings-123456789012 \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"arn:aws:kms:us-east-1:123456789012:key/abc123"}}]}'
```

**KMS key policy (grant Connect):**

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {"Service": "connect.amazonaws.com"},
      "Action": ["kms:Encrypt", "kms:Decrypt", "kms:ReEncrypt*", "kms:GenerateDataKey*", "kms:DescribeKey"],
      "Resource": "*",
      "Condition": {"StringEquals": {"aws:SourceAccount": "123456789012"}}
    }
  ]
}
```

**Associate storage config with instance:**

```bash
aws connect associate-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --resource-type CALL_RECORDINGS \
  --storage-config \
    '{"S3Config":{"BucketName":"connect-recordings-123456789012","BucketPrefix":"recordings","EncryptionConfig":{"EncryptionType":"KMS","KeyId":"arn:aws:kms:us-east-1:123456789012:key/abc123"}},"StorageType":"S3"}'
```

**Verify:**

```bash
aws connect list-instance-storage-configs --instance-id "$INSTANCE_ID"
```

## Step 14 — Real-time and historical metrics

| Metric type | Source | Latency |
|---|---|---|
| Real-time (ContactFlow, RoutingProfile, Queue, Agent) | Instance built-in | Seconds |
| Historical (ContactTraceRecord) | S3 export or console | Up to 24 months |
| Real-time custom metrics | Kinesis video / data stream | Seconds |

**Real-time metrics (built-in):**

```bash
aws connect get-contact-metrics \
  --instance-id "$INSTANCE_ID" \
  --filters '{"Queues":["'"$QUEUE_ID"'"],"Channels":["VOICE"]}'
```

**Historical metrics (CTR export):**

```bash
aws connect start-contact-recording ... # (CTR export via S3 batch)
```

## Step 15 — Recent features

**Recent AWS features (2023-2026):**

- **Amazon Q in Connect (2023-2026):** Generative AI assistant for
  agents — surfaces real-time suggested responses and knowledge base
  articles during calls. Integrated via Q connector blocks in
  contact flows.

- **Customer Profiles (2023-2024):** Unified customer profile store
  with event-triggered updates. Replaces DynamoDB-as-profile-store
  pattern.

- **Amazon Connect Cases (2023-2024):** Case management for complex
  multi-contact customer issues. Integrates with Tasks.

- **Voice ID generative improvements (2024-2025):** Reduced
  enrollment time, improved fraud-risk accuracy with deep learning
  models, multi-language support.

- **Contact Lens real-time summaries (2024-2025):** Generative AI
  contact summaries available in real-time, not just post-call.

- **Amazon Lex V2 generative AI (2024-2025):** Lex V2 with
  generative AI for open-ended intent elicitation and assisted slot
  filling.

- **WebRTC media streaming (2024-2025):** Direct browser-based voice
  via WebRTC, reducing PSTN costs for some scenarios.

## NEVER do these things

1. **NEVER author a contact flow without verifying referenced
   resources exist.** A flow with a dangling queue ARN, Lambda ARN,
   or Lex bot alias creates successfully but fails at run time when a
   contact hits the dangling reference. Always pre-flight check every
   referenced resource.

2. **NEVER invoke a Lambda function without a resource policy
   granting Connect.** Without the resource policy, the InvokeLambda
   block returns `Lambda.AccessDenied`. Add permission via
   `aws lambda add-permission --principal connect.amazonaws.com`.

3. **NEVER assume a routing profile without skills produces skills-
   based routing.** Without skill requirements, routing silently
   degrades to queue-priority routing. Verify skills are defined at
   the instance level and proficiencies are set on agents.

4. **NEVER use Lex V1 for new deployments.** Lex V1 is on a
   deprecation path. Use Lex V2 via the InvokeAmazonLex block. The
   block name and parameters differ between V1 and V2.

5. **NEVER claim a phone number in a region different from the
   instance.** Phone numbers are per-region. A US toll-free number
   does not work in EU instances. Match the phone number region to
   the instance region.

6. **NEVER enable Voice ID without consent disclosure in the flow.**
   Voice biometrics require caller consent (legal requirement in
   most jurisdictions). Add a prompt and opt-out path.

7. **NEVER store call recordings in S3 without KMS encryption.**
   Plain S3 recordings are unencrypted at rest. Always use SSE-KMS
   with a key policy granting Connect.

8. **NEVER use a DRAFT Lex bot alias in a production flow.** Connect
   invokes published aliases. DRAFT changes can break the flow
   silently. Use a versioned alias with controlled promotion.

9. **NEVER forget exceptions on InvokeLambda blocks.** Lambda can
   fail with AccessDenied, Timeout, or GenericError. Without
   exception transitions, the contact is trapped in the flow.

10. **NEVER assume instance alias is mutable.** Alias is set at
    instance creation and is immutable. Choose carefully.

## Output format

```text
CONNECT_INSTANCE: <instance-id> (<alias>, <identity-mode>)
VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING
CHECKLIST:
  [✓|✗] Instance: <instance-id> (<alias>)
  [✓|✗] Identity mode: SAML | CONNECT_MANAGED | EXISTING_DIRECTORY
  [✓|✗] Directory: <directory-id or N/A>
  [✓|✗] Contact flow: <flow-id> (<name>, <type>, <verified>)
  [✓|✗] Lambda integration: <function-arn> (resource policy grants Connect)
  [✓|✗] Queues: <queue-id list>
  [✓|✗] Routing profile: <profile-id> (queues, skills, concurrency)
  [✓|✗] Skill requirements: <skill-name:proficiency> | none (queue-priority only)
  [✓|✗] User hierarchy: <hierarchy-group-id>
  [✓|✗] Phone number: <E.164> (<toll-free | DID>, <region>)
  [✓|✗] Lex bot: <bot-alias-arn> (V2, published, locale matches)
  [✓|✗] Voice ID: <domain-id> (consent disclosure in flow) | disabled
  [✓|✗] Contact Lens: <real-time | post-call | both>
  [✓|✗] Channels: VOICE | CHAT | TASK
  [✓|✗] Recording storage: S3 (<bucket>, KMS <key-id>)
  [✓|✗] Tags: <key=value list>
VERIFICATION_COMMANDS:
  aws connect describe-instance --instance-id <instance-id>
  aws connect describe-contact-flow --instance-id <instance-id> --contact-flow-id <flow-id>
  aws connect describe-routing-profile --instance-id <instance-id> --routing-profile-id <profile-id>
  aws connect describe-phone-number --instance-id <instance-id> --phone-number-id <phone-number-id>
  aws connect list-instance-storage-configs --instance-id <instance-id>
```

### Worked example — SAML instance with Lambda-driven flow and Lex IVR

```text
CONNECT_INSTANCE: inst-abc123 (my-connect-cc, SAML)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Instance: inst-abc123 (my-connect-cc)
  [✓] Identity mode: SAML (Okta IdP)
  [✓] Directory: N/A
  [✓] Contact flow: flow-def456 (inbound-main-flow, CONTACT_FLOW, all referenced resources verified)
  [✓] Lambda integration: arn:aws:lambda:us-east-1:123456789012:function:lookup-customer (resource policy grants Connect)
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

## Error handling

### Contact flow fails at run time despite creating successfully
- A referenced resource (queue, Lambda, Lex bot) does not exist or
  the ARN is wrong. Pre-flight check every referenced resource via
  the relevant describe command before publishing the flow.

### Lambda invocations return AccessDenied
- The Lambda function lacks a resource policy granting
  `connect.amazonaws.com` invoke permission. Add permission via
  `aws lambda add-permission --principal connect.amazonaws.com
  --source-arn <instance-arn>`.

### Contacts route to wrong agents
- Routing profile lacks skill requirements. Without skills, routing
  is pure queue-priority. Define skills at the instance level and
  set proficiencies on agents.

### Phone number claim fails
- The number is in a different region from the instance, or the
  number is not available in the AWS pool. Match phone number region
  to instance region, or request a different number.

### Lex bot invocations time out
- The bot alias is DRAFT (not published), or the locale does not
  match the instance language. Publish a versioned alias and verify
  locale.

### Voice ID enrollment fails
- Caller did not provide consent (consent disclosure prompt missing
  in flow). Add a prompt and opt-out path before the Voice ID
  enrollment block.

### Recordings not appearing in S3
- KMS key policy does not grant Connect encrypt/decrypt permission,
  or the S3 bucket policy blocks Connect. Verify the KMS key policy
  includes `connect.amazonaws.com` and the S3 bucket policy allows
  Connect to put objects.

### Real-time metrics missing
- Instance was created before the real-time metrics feature was
  enabled, or the metric stream is not configured. Enable via the
  console or `update-instance-storage-config`.

## Domain

AWS CloudOps / Amazon Connect Contact Center Provisioning —
Instances, Contact Flows, Queues, Routing Profiles, Phone Numbers,
Voice ID, Contact Lens, Channels, Recording Storage, and Metrics.

## AWS documentation

- **Amazon Connect Administrator Guide** — https://docs.aws.amazon.com/connect/latest/adminguide/what-is-amazon-connect.html
- **Create instance (SAML, Connect directory, existing directory)** — https://docs.aws.amazon.com/connect/latest/adminguide/connect-launch.html
- **Contact flows (drag-and-drop, JSON)** — https://docs.aws.amazon.com/connect/latest/adminguide/contact-flows.html
- **Contact flow JSON schema** — https://docs.aws.amazon.com/connect/latest/adminguide/contact-flow-language.html
- **Lambda function invocation** — https://docs.aws.amazon.com/connect/latest/adminguide/connect-lambda-functions.html
- **Queues and routing profiles** — https://docs.aws.amazon.com/connect/latest/adminguide/queues-and-routing.html
- **Skills-based routing** — https://docs.aws.amazon.com/connect/latest/adminguide/skills.html
- **User hierarchy** — https://docs.aws.amazon.com/connect/latest/adminguide/user-hierarchy.html
- **Claim phone numbers** — https://docs.aws.amazon.com/connect/latest/adminguide Claim-phone-number.html
- **Amazon Lex integration** — https://docs.aws.amazon.com/connect/latest/adminguide/connect-lex-bots.html
- **Amazon Connect Voice ID** — https://docs.aws.amazon.com/connect/latest/voiceid/what-is-voice-id.html
- **Contact Lens for Amazon Connect** — https://docs.aws.amazon.com/connect/latest/adminguide/enable-analytics.html
- **Chat channels** — https://docs.aws.amazon.com/connect/latest/adminguide/chat.html
- **Task management** — https://docs.aws.amazon.com/connect/latest/adminguide/tasks.html
- **S3 recording storage with KMS** — https://docs.aws.amazon.com/connect/latest/adminguide/setup-data-storage.html
- **Real-time and historical metrics** — https://docs.aws.amazon.com/connect/latest/adminguide/metrics.html
- **Amazon Connect API reference** — https://docs.aws.amazon.com/connect/latest/APIReference/Welcome.html
- **Amazon Q in Connect** — https://docs.aws.amazon.com/connect/latest/adminguide/amazon-q.html
- **AWS End User Messaging (SMS for Connect)** — https://docs.aws.amazon.com/sms-voice/latest/userguide/what-is-sms-voice.html
