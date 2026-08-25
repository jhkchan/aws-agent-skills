---
name: connect-instance-deployer
description: Provisions Amazon Connect instances, contact flows, queues, routing profiles, phone numbers, and integrations with production defaults. Instance creation with three identity modes (SAML federation, Connect directory, existing AWS Directory Service directory). Contact flows authored as JSON specs with Lambda invoke blocks (InvokeLambda), branching, queue transfers, and Lex bot integration (InvokeAmazonLex). Routing profiles with skill requirements (skill name + proficiency), queue associations, agent hierarchy. Phone number claim (toll-free, DID). Voice ID (speaker enrollment, fraud risk). Contact Lens (sentiment, transcription, redaction). Chat, voice, task channels. S3 recording storage with KMS encryption. Lex V2 for IVR. Real-time/historical metrics. Emits READY_TO_DEPLOY with verification commands. Use when creating a Connect instance, authoring a contact flow, configuring routing skills, claiming a phone number, integrating Lex for IVR, enabling Voice ID or Contact Lens, or setting up recording storage.
license: Apache-2.0
compatibility: 'Agent runtime that reads SKILL.md (Claude Code, Cursor, Windsurf, Codex, Gemini). For live deployment: AWS CLI v2 with connect access (and connect-contact-lens for Contact Lens, lexv2-runtime for Lex, s3 for recording storage, kms for key policy). Works with Terraform aws_connect_instance, aws_connect_contact_flow, aws_connect_queue, aws_connect_routing_profile, aws_connect_phone_number, aws_connect_user, aws_connect_user_hierarchy_group resources and CloudFormation AWS::Connect::* templates.'
metadata:
  domain: aws-cloudops
  complexity: high
  requires_llm: 'true'
  phase: '1'
  supports_pipeline: 'true'
  entry_point: 'false'
  family: AppIntegration
  task_type: deploy
  skill_class: capability
  lifecycle_status: active
  verdict_shape: READY_TO_DEPLOY | PREREQUISITES_MISSING
  version: 0.1.0
  author: Jacky Chan — AWS Community Builder
  tags: aws, connect, appintegration, deploy, contact-center, contact-flow, routing, voice
  dependencies: aws-orchestrator
  keywords: aws, connect, amazon connect, contact center, contact flow, lambda invoke, queue, routing profile, skill requirement, phone number, toll-free, did, saml, directory, voice id, contact lens, sentiment, transcription, chat, voice, task, lex bot, ivr, recording, s3, kms, real-time metrics, historical metrics
  when_to_use: Invoke when the user wants to create an Amazon Connect instance (SAML, Connect directory, or existing AWS Directory Service directory), author a contact flow with Lambda invoke blocks or Lex integration, configure a routing profile with skill requirements, claim a phone number (toll-free, DID), set up queues with quick- connect lists, integrate Amazon Lex V2 for IVR, enable Voice ID speaker enrollment, enable Contact Lens for sentiment / transcription / redaction, configure chat and voice channels, manage tasks, set up S3 recording storage with KMS encryption, or wire real-time and historical metrics. Do NOT invoke for Amazon Chime SDK, Amazon WorkSpaces, or standalone Amazon Lex bot deployment.
---

# Connect Instance Deployer

An AWS CloudOps agent skill that provisions Amazon Connect instances,
contact flows, queues, routing profiles, phone numbers, and channel
integrations with contact-center-best-practice defaults. The skill
walks identity-mode selection (SAML, Connect directory, existing AWS
Directory Service directory), contact-flow authoring (JSON spec with
Lambda invoke blocks, branching, queue transfers, Lex IVR), routing-
profile skill requirements (skill name + proficiency level), phone
number claim (toll-free, DID), Voice ID, Contact Lens, S3 recording
with KMS, and metrics. The skill surfaces the three expert
heuristics (contact flow JSON with Lambda invoke blocks, routing
profile skill requirements, Lex bot integration for IVR) and emits a
READY_TO_DEPLOY checklist with verification commands.

## Activation keywords

create Connect instance, SAML identity, contact flow JSON, Lambda
invoke block, queue and routing profile, routing profile skill,
claim phone number toll-free, DID porting, Lex bot IVR, Voice ID
enrollment, Contact Lens sentiment, Connect task, S3 recording KMS,
quick-connect, agent hierarchy, real-time metrics.

## STRICT output contract

When invoked with a Connect-provisioning request, the agent MUST
respond with the READY_TO_DEPLOY checklist defined below. This
contract is what assertion-based evals and downstream pipelines rely
on; deviating breaks automation silently.

### Required output structure

The model MUST emit output using these literal labels, in this order,
as the FIRST lines of the response (no prose, headings, or disclaimers
before them):

- `CONNECT_INSTANCE: <instance-id> (<alias>, <identity-mode>)` — first line
- `VERDICT: READY_TO_DEPLOY | PREREQUISITES_MISSING` — second line
- `CHECKLIST:` followed by `- [✓]` or `- [✗]` items (one row per dimension below)
- `CONTACT_FLOW_SNIPPET:` followed by a fenced JSON block (the actual flow, not a placeholder)
- `VERIFICATION_COMMANDS:` followed by a fenced block of copy-pasteable CLI

The CHECKLIST MUST cover every dimension, in this order: instance +
identity mode (SAML / CONNECT_MANAGED / EXISTING_DIRECTORY), directory
ID (or N/A), contact flow (flow ID + name + type + "all referenced
resources verified"), Lambda integration (function ARN + resource
policy grants `connect.amazonaws.com`), queues (queue IDs), routing
profile (profile ID + queues + skills + concurrency), skill
requirements (skill name + proficiency threshold), user hierarchy,
phone number (E.164 + toll-free/DID + region), Lex bot (bot alias ARN
+ V2 + published + locale), Voice ID (domain ID + consent disclosure),
Contact Lens (real-time / post-call / both), channels (VOICE / CHAT /
TASK), recording storage (S3 bucket + KMS key ID), and tags.

The CONTACT_FLOW_SNIPPET MUST be a real, runnable JSON block (not a
placeholder, not pseudocode) showing at minimum: Start, a CheckHoursOfOperation
branch, an InvokeLambda Action with Exception transitions, an
InvokeAmazonLex Action, a TransferToQueue Terminal, and a Disconnect
Terminal. Use concrete Identifier values and real ARNs consistent with
the CHECKLIST rows.

### Decision tree (determines VERDICT)

```text
Is the instance alias unique (no existing instance with same alias)?
├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Instance alias collision)
└── YES → Is the identity mode decided (SAML / CONNECT_MANAGED / EXISTING_DIRECTORY)?
          ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Identity mode)
          └── YES → If SAML, is the IdP metadata document available?
                    ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] SAML metadata)
                    └── YES → Does every contact-flow reference resolve (queue, Lambda, Lex)?
                              ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Dangling flow reference — name it)
                              └── YES → Does every Lambda have a resource policy granting connect.amazonaws.com?
                                        ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Lambda resource policy)
                                        └── YES → Is the Lex bot a published V2 alias (not DRAFT) with matching locale?
                                                  ├── NO  → VERDICT: PREREQUISITES_MISSING  ([✗] Lex bot alias)
                                                  └── YES → All prerequisites satisfied
                                                            → VERDICT: READY_TO_DEPLOY
```

### FORBIDDEN patterns (NEVER)

1. **NEVER preface the CHECKLIST** with prose, headings, or disclaimers — emit the block as the first lines of the response.
2. **NEVER omit the VERIFICATION_COMMANDS section**, even when every checklist item passes.
3. **NEVER use generic placeholders** (`<instance-id>`, `<your-flow>`, `<region>`) in a worked example — always use concrete instance IDs, real ARNs, actual queue/profile IDs, and specific CLI commands.
4. **NEVER mix verdict shapes** — if any prerequisite is `[✗]`, VERDICT MUST be `PREREQUISITES_MISSING` and `READY_TO_DEPLOY` MUST NOT also appear.
5. **NEVER skip a CHECKLIST row** — every dimension (instance, identity, directory, flow, Lambda, queues, routing profile, skills, hierarchy, phone number, Lex, Voice ID, Contact Lens, channels, recording, tags) gets a `[✓]` or `[✗]` line.
6. **NEVER emit a CONTACT_FLOW_SNIPPET that is pseudocode or a placeholder** — it MUST be valid JSON that `create-contact-flow --content` would accept.
7. **NEVER list a Lambda integration as `[✓]` without confirming the resource policy** grants `connect.amazonaws.com` invoke with the instance ARN as `SourceArn` — otherwise InvokeLambda returns AccessDenied at run time.
8. **NEVER list a Lex bot as `[✓]` if the alias is DRAFT** — Connect invokes published aliases only; DRAFT changes break the flow silently.
9. **NEVER list a routing profile as `[✓]` without skill requirements** if the scenario calls for skills-based routing — without skills, routing silently degrades to queue-priority.

### Perfect example — SAML instance with Lambda-driven flow and Lex V2 IVR

This is the EXACT shape the model emits for a positive scenario. The
CONTACT_FLOW_SNIPPET is a real JSON block (Start → CheckHours →
InvokeLambda → InvokeAmazonLex → branch → TransferToQueue / Disconnect).
Replace the concrete values with the scenario's values; do not
genericise them into placeholders.

```text
CONNECT_INSTANCE: inst-abc123def456 (my-connect-cc, SAML)
VERDICT: READY_TO_DEPLOY
CHECKLIST:
  [✓] Instance: inst-abc123def456 (alias my-connect-cc, us-east-1)
  [✓] Identity mode: SAML (Okta IdP, metadata document loaded)
  [✓] Directory: N/A (SAML federation, no Connect-managed directory)
  [✓] Contact flow: flow-def456789 (inbound-main-flow, CONTACT_FLOW, all referenced resources verified)
  [✓] Lambda integration: arn:aws:lambda:us-east-1:123456789012:function:lookup-customer (resource policy grants connect.amazonaws.com, SourceArn inst-abc123def456)
  [✓] Queues: sales-queue-id-111, support-queue-id-222, default-queue-id-333
  [✓] Routing profile: rp-xyz998877 (sales queue P1, support queue P2, VOICE concurrency 1)
  [✓] Skill requirements: Sales (proficiency ≥ 4), Support (proficiency ≥ 4)
  [✓] User hierarchy: Sales - North America (hg-sales-na)
  [✓] Phone number: +18005551234 (toll-free, us-east-1, claimed via pn-456789)
  [✓] Lex bot: arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod (V2, published alias Prod, locale en_US matches instance)
  [✓] Voice ID: disabled (consent disclosure not yet added to flow)
  [✓] Contact Lens: post-call (transcription + sentiment + redaction)
  [✓] Channels: VOICE, CHAT, TASK
  [✓] Recording storage: S3 connect-recordings-123456789012 (KMS key arn:aws:kms:us-east-1:123456789012:key/abc-123-def-456)
  [✓] Tags: Environment=production, Project=sales-cc, Owner=cc-ops
CONTACT_FLOW_SNIPPET:
{
  "Version": "1",
  "StartAction": "check-hours",
  "Actions": [
    {
      "Identifier": "check-hours",
      "Type": "CheckHoursOfOperation",
      "Transitions": {
        "NextAction": "invoke-lookup-customer",
        "Conditions": [
          {"NextAction": "play-closed", "Condition": {"Operator": "Equals", "Operand": "False"}}
        ]
      }
    },
    {
      "Identifier": "invoke-lookup-customer",
      "Type": "InvokeLambda",
      "Parameters": {
        "FunctionARN": "arn:aws:lambda:us-east-1:123456789012:function:lookup-customer",
        "InvocationTimeLimitSeconds": 5
      },
      "Transitions": {
        "NextAction": "play-greeting",
        "Exceptions": [
          {"NextAction": "transfer-default", "Error": "Lambda.AccessDenied"},
          {"NextAction": "transfer-default", "Error": "Lambda.Timeout"}
        ]
      }
    },
    {
      "Identifier": "play-greeting",
      "Type": "PlayPrompt",
      "Parameters": {"Text": "Thanks for calling. How can I help you today?"},
      "Transitions": {"NextAction": "invoke-lex-router"}
    },
    {
      "Identifier": "invoke-lex-router",
      "Type": "InvokeAmazonLex",
      "Parameters": {
        "BotAliasArn": "arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod",
        "Intent": "RouteCall",
        "Slots": {"department": null},
        "SessionAttributes": {"caller_id": "$.CustomerEndpoint.Address"}
      },
      "Transitions": {
        "NextAction": "branch-on-department",
        "Exceptions": [{"NextAction": "transfer-default", "Error": "Lex.Timeout"}]
      }
    },
    {
      "Identifier": "branch-on-department",
      "Type": "Branch",
      "Transitions": {
        "Conditions": [
          {"NextAction": "transfer-sales",    "Condition": {"Operator": "Equals", "Operand": "Sales",   "Reference": "$.Lex.Slots.department"}},
          {"NextAction": "transfer-support",  "Condition": {"Operator": "Equals", "Operand": "Support", "Reference": "$.Lex.Slots.department"}}
        ]
      }
    },
    {"Identifier": "transfer-sales",   "Type": "TransferToQueue", "Parameters": {"QueueId": "sales-queue-id-111"},   "Transitions": {}},
    {"Identifier": "transfer-support", "Type": "TransferToQueue", "Parameters": {"QueueId": "support-queue-id-222"}, "Transitions": {}},
    {"Identifier": "transfer-default", "Type": "TransferToQueue", "Parameters": {"QueueId": "default-queue-id-333"}, "Transitions": {}},
    {"Identifier": "play-closed",      "Type": "PlayPrompt",      "Parameters": {"Text": "We are closed. Please call back during business hours."}, "Transitions": {"NextAction": "disconnect"}},
    {"Identifier": "disconnect",       "Type": "Disconnect",      "Parameters": {}, "Transitions": {}}
  ]
}
VERIFICATION_COMMANDS:
  aws connect describe-instance --instance-id inst-abc123def456
  aws connect describe-contact-flow --instance-id inst-abc123def456 --contact-flow-id flow-def456789
  aws connect describe-routing-profile --instance-id inst-abc123def456 --routing-profile-id rp-xyz998877
  aws connect describe-phone-number --instance-id inst-abc123def456 --phone-number-id pn-456789
  aws lambda get-policy --function-name lookup-customer --query 'Policy' --output text | grep connect.amazonaws.com
  aws lexv2-models describe-bot-alias --bot-alias-id Prod --bot-id CustomerService
  aws connect list-instance-storage-configs --instance-id inst-abc123def456
```

If any prerequisite fails, emit the SAME shape with
`VERDICT: PREREQUISITES_MISSING`, the failing row marked `[✗]` with a
specific gap citation (e.g. `[✗] Lex bot alias: DRAFT alias is not
publishable — create a published alias`), the passing rows still listed,
the CONTACT_FLOW_SNIPPET still emitted (so the operator can see the
dangling reference), and VERIFICATION_COMMANDS showing the command that
would confirm the gap.

## Quick navigation

| Section | When to read |
|---|---|
| Prerequisites | Always — verify before provisioning |
| Step 1 — Instance creation (SAML, Connect dir, existing dir) | Identity mode |
| Step 2 — Contact flow JSON | Authoring flows |
| Step 3 — Lambda function integration (InvokeLambda block) | Dynamic IVR logic |
| Step 4 — Queues and quick-connect lists | Routing targets |
| Step 5 — Routing profiles (skills, proficiency) | Agent routing |
| Step 6 — Agent hierarchy | Org structure |
| Step 7 — Phone number claim (toll-free, DID) | Inbound numbers |
| Step 8 — Skills-based routing | Skill matching |
| Step 9 — Amazon Lex bot integration (IVR) | Conversational IVR |
| Step 10 — Voice ID | Caller authentication |
| Step 11 — Contact Lens | Quality analytics |
| Step 12 — Chat, voice, task channels | Channel coverage |
| Step 13 — S3 recording storage (KMS) | Call recordings |
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
functions invoked from the flow provide dynamic IVR logic. Routing
profiles match agents to contacts via skills (skill name +
proficiency level). Lex bots handle conversational IVR inside the
flow.

Three misconceptions dominate Connect misdesign:

- **"A contact flow is just an IVR menu."** It is not. A contact
  flow is a JSON spec DAG of typed blocks: Action (PlayPrompt,
  InvokeLambda, TransferToQueue, InvokeAmazonLex), Branch
  (CheckHoursOfOperation, Compare, EvaluateAttribute), Terminal
  (Disconnect). The drag-and-drop console edits this JSON;
  programmatic deployments author it directly. Treating it as a
  flat menu misses Lambda-driven dynamic routing and Lex-driven
  conversational IVR.

- **"A routing profile is just a queue assignment."** It is not. A
  routing profile associates an agent with queues AND specifies
  the SKILL REQUIREMENTS that determine which contacts the agent
  handles. Without skills, routing is pure queue-and-priority.
  With skills, contacts route to the agent with the highest
  proficiency matching the contact's required skill. Misdesigning
  skill requirements produces "the contact routed to the wrong
  agent" tickets.

- **"IVR means pressing 1 or 2."** Modern IVR is conversational
  via Amazon Lex V2. The InvokeAmazonLex block invokes a Lex bot
  to elicit an intent and fill slots through natural-language
  conversation. The bot returns an intent and slots to the flow,
  which branches on those values. Treating IVR as touch-tone only
  misses the conversational IVR pattern.

## Configuration dependency graph

Connect configurations are NOT independent. Instance before flows;
flows reference queues and Lambda functions; routing profiles
reference queues and skills; phone numbers are claimed at instance
level.

| Configuration | Hard dependencies (silent failure without) | Silent failure / immutability | Enables downstream |
|---|---|---|---|
| Instance | Identity mode selected | Alias immutable; identity mode set at creation | flows, queues, routing profiles, phone numbers, users |
| Contact flow | Instance; flow JSON valid; referenced queues/Lambda exist | flow with dangling refs creates at API but fails at run time | inbound contact handling |
| Lambda function | Function deployed in same region; resource policy grants Connect invoke | without resource policy, Lambda invocations fail AccessDenied | dynamic IVR logic |
| Queue | Instance; HoursOfOperation defined | queue with no agents via routing profile holds contacts indefinitely | routing target |
| Routing profile | Instance; queues defined; skills defined (if used) | agent without routing profile cannot log in to CCP | agent routing |
| Skill | Instance; skill name unique | proficiency is set on the agent, not the skill | skills-based routing |
| User (agent) | Instance; routing profile + security profile assigned | SAML users managed in IdP; Connect-dir users via CreateUser | login to CCP, handle contacts |
| Phone number | Instance claimed via ClaimedPhoneNumber or porting | per-region; toll-free vs DID affects inbound | inbound voice |
| Lex bot (V2) | Dialect ID set; bot published; Connect integrated via InvokeAmazonLex | Lex V1 deprecated path | conversational IVR |
| Voice ID | Instance; domain created; consent disclosure in flow | enrollment requires caller consent | authentication, fraud |
| Contact Lens | Instance; language model; sentiment/redaction settings | post-call vs real-time (different features) | sentiment, transcription |
| Recording (S3+KMS) | S3 bucket with KMS; KMS key policy grants Connect | recordings encrypted with KMS | call recording storage |
| Real-time metrics | Instance | built-in; custom via Kinesis | operations |
| Historical metrics | Instance; CTR export configured | CTRs available 24 months; longer needs S3 | analytics |

**The contact-flow-block-references row is the one a baseline model
misses.** A model that authors a flow JSON without verifying
referenced queues, Lambda functions, and Lex bots will produce a
flow that creates at the API but fails at run time when a contact
hits the dangling reference.

**Cross-dependency gotchas:**
- A flow referencing a non-existent queue (or wrong queue ARN)
  creates successfully but every contact fails at TransferToQueue.
- A Lambda without a resource policy granting `connect.amazonaws.com`
  returns AccessDenied when the flow runs.
- A routing profile without skill requirements produces pure queue-
  priority routing (no skills-based matching).
- Phone numbers are per-region. US toll-free does not work in EU.
- Amazon Lex V1 is on a deprecation path; use Lex V2 via
  InvokeAmazonLex.

## Expert heuristic: contact flow JSON with Lambda invoke blocks

A baseline model treats the flow as a touch-tone IVR. The correct
heuristic recognizes the flow as a DAG of typed blocks and the
InvokeLambda block as the integration point for dynamic IVR logic.

```text
Sample flow DAG:
  Start → CheckHoursOfOperation
            ├── (Open) → InvokeLambda(lookup_customer)
            │             ├── Return → PlayPrompt(greeting) → InvokeAmazonLex(route_call)
            │             │                              ├── intent=Sales    → TransferToQueue(Sales)
            │             │                              └── intent=Support  → TransferToQueue(Support)
            │             └── Error → TransferToQueue(Default)
            └── (Closed) → PlayPrompt(closed) → Disconnect

InvokeLambda block (JSON):
  Identifier: "lookup_customer", Type: "Action"
  Parameters: { FunctionARN, InvocationTimeLimitSeconds: 5 }
  Transitions: {
    NextAction: "play_greeting",
    Exceptions: [
      { NextAction: "transfer_default", Error: "Lambda.AccessDenied" },
      { NextAction: "transfer_default", Error: "Lambda.Timeout" }
    ]
  }
```

**Key implication:** Lambda invocations from Connect flows MUST
handle exceptions (AccessDenied, Timeout, GenericError). Without
exceptions, a Lambda failure traps the contact. The Lambda
resource policy MUST grant `connect.amazonaws.com` invoke with the
instance ARN as source.

## Expert heuristic: routing profile skill requirements

A baseline model treats routing profiles as queue priorities. The
correct heuristic recognizes that skill requirements (skill name +
proficiency) determine which contacts route to which agents.

```text
Routing profile with skill requirements:
  Queues: Sales (priority 1), Support (priority 2)

  Agent A: Sales=5, Support=3
  Agent B: Support=5

Contact X (required skill: Sales, proficiency ≥ 4):
  → Agent A (Sales=5 ≥ 4)
  → Agent B INELIGIBLE (no Sales skill)

Contact Y (required skill: Support, proficiency ≥ 4):
  → Agent B (Support=5 ≥ 4)
  → Agent A INELIGIBLE for this contact (Support=3 < 4)
```

**Key implication:** skills are defined at the instance level,
proficiency is set on each agent per skill, and contacts specify
the required skill + proficiency via the contact flow. Without all
three, skills-based routing silently degrades to queue-priority.

## Expert heuristic: Lex bot integration for IVR

A baseline model treats IVR as touch-tone menus. The correct
heuristic recognizes the InvokeAmazonLex block as the integration
point for conversational IVR.

```text
Flow with Lex IVR:
  Start → PlayPrompt("How can I help you?")
       → InvokeAmazonLex(bot=CustomerService, intent=RouteCall, slot=department)
            ├── Lex elicits slot via conversation:
            │     "Are you calling about Sales or Support?"
            │     Caller: "Sales" → slot filled {department: "Sales"}
            └── Lex returns intent=RouteCall, slots={department: Sales}
       → Branch on slot value:
            ├── department == "Sales"   → TransferToQueue(Sales)
            ├── department == "Support" → TransferToQueue(Support)
            └── unknown → loop back to InvokeAmazonLex
```

**Key implication:** the Lex bot must be a published alias (not
DRAFT) and the locale must match the Connect instance language.
Bot responses can be slow on cold paths; set session timeouts and
Lambda fallbacks.

## Prerequisites (verify before provisioning)

| Prerequisite | Why | How to verify |
|---|---|---|
| Instance alias unique | Alias is immutable once set | `aws connect list-instances` |
| Identity mode decided | Set at instance creation | Confirm via planning |
| SAML metadata (if SAML) | SAML federation needs IdP metadata | Verify metadata document |
| Directory ID (if existing dir) | Existing-dir mode needs directory ID | `aws ds describe-directories` |
| Service-linked role | Connect needs AWSServiceRoleForAmazonConnect (auto-created) | `aws iam get-role` |
| Lambda functions deployed (if referenced) | Dangling refs fail at run time | `aws lambda get-function` |
| Lambda resource policy grants Connect | Without it, InvokeLambda fails AccessDenied | `aws lambda get-policy` (look for connect.amazonaws.com) |
| Lex V2 bot published (if used) | Connect invokes published alias | `aws lexv2-models describe-bot-alias` |
| S3 bucket for recordings with KMS | Recording storage requires S3 + KMS | `aws s3api get-bucket-encryption` + `aws kms describe-key` |
| KMS key policy grants Connect | Without policy, recordings cannot be encrypted | `aws kms get-key-policy` |
| IAM permissions | Operator needs connect:CreateInstance, CreateContactFlow, etc. | Check attached policies |
| Phone number quota | Each instance has a quota (soft limit) | `aws service-quotas get-service-quota` |

If any prerequisite is missing, output
`VERDICT: PREREQUISITES_MISSING` and cite the specific gap.

## Step 1 — Instance creation (SAML, Connect directory, existing directory)

| Mode | Identity source | Use case |
|---|---|---|
| `SAML` | External IdP via SAML 2.0 (Okta, Azure AD) | Enterprise SSO |
| `CONNECT_MANAGED` | Amazon Connect directory (built-in user pool) | Standalone; small teams |
| `EXISTING_DIRECTORY` | Existing AWS Directory Service directory | AD-integrated enterprises |

```bash
INSTANCE_ID=$(aws connect create-instance \
  --instance-name "my-connect-cc" \
  --IdentityManagementType SAML \
  --InboundCallsEnabled --OutboundCallsEnabled \
  --ClientToken "unique-token-1" \
  --query 'Id' --output text)
aws connect describe-instance --instance-id "$INSTANCE_ID"
```

For `CONNECT_MANAGED`, omit `--DirectoryId`. For
`EXISTING_DIRECTORY`, pass `--DirectoryId d-1234567890`.

## Step 2 — Contact flow JSON

Contact flows are JSON specs. Block categories: Action (PlayPrompt,
InvokeLambda, InvokeAmazonLex, TransferToQueue, SetAttributes,
SetRecordingBehavior), Branch (CheckHoursOfOperation, Compare,
EvaluateAttribute, GetCustomerInput, Loop), Transfer
(TransferToQueue, TransferToFlow), Terminal (Disconnect).

```bash
aws connect create-contact-flow \
  --instance-id "$INSTANCE_ID" \
  --name "inbound-main-flow" \
  --type CONTACT_FLOW \
  --content "$(cat flow.json)"
```

The flow JSON has `Version`, `StartAction`, and `Actions[]`. Each
action has `Identifier`, `Type`, `Parameters`, and `Transitions`
(`NextAction`, optional `Conditions` or `Exceptions`). See
`references/contact-flow-json-and-lambda.md` for the full schema,
sample flow, and Terraform example.

Verify: `aws connect describe-contact-flow` and
`start-test-contact-flow`.

## Step 3 — Lambda function integration (InvokeLambda block)

Connect invokes Lambda via the InvokeLambda block. The Lambda
receives a Connect event (with `Details.ContactData.CustomerEndpoint.
Address` for the caller phone) and returns JSON that updates
contact attributes (retrievable via `$.External.<key>` in
subsequent blocks).

```bash
# Grant Connect invoke permission (CRITICAL — without this, InvokeLambda returns AccessDenied)
aws lambda add-permission \
  --function-name lookup-customer \
  --statement-id connect-invoke \
  --action lambda:InvokeFunction \
  --principal connect.amazonaws.com \
  --source-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID"
```

Lambda response example (Python):

```python
def lambda_handler(event, context):
    phone = event['Details']['ContactData']['CustomerEndpoint']['Address']
    customer = lookup_customer(phone)
    return {'customer_id': customer['id'], 'department': route_call(customer)}
```

The InvokeLambda block MUST handle exceptions (AccessDenied,
Timeout, GenericError); see
`references/contact-flow-json-and-lambda.md` for the full anatomy.

## Step 4 — Queues and quick-connect lists

Queues are routing targets. Each queue has HoursOfOperation,
quick-connect list (for transfers), hold-flow, and outbound caller
ID.

```bash
QUEUE_ID=$(aws connect create-queue \
  --instance-id "$INSTANCE_ID" \
  --name "sales-queue" \
  --hours-of-operation-id <hours-of-operation-id> \
  --outbound-caller-id-number-id <phone-number-id> \
  --query 'QueueId' --output text)
```

Quick-connect (transfer target):

```bash
aws connect create-quick-connect --instance-id "$INSTANCE_ID" \
  --name "sales-escalation" \
  --quick-connect-config '{"QuickConnectType":"QUEUE","QueueConfig":{"QueueId":"'"$QUEUE_ID"'","ContactFlowId":"<flow-id>"}}'
```

## Step 5 — Routing profiles (skills, proficiency, queue associations)

```bash
ROUTING_PROFILE_ID=$(aws connect create-routing-profile \
  --instance-id "$INSTANCE_ID" \
  --name "tier-1-sales-support" \
  --default-outbound-queue-id "$QUEUE_ID" \
  --queue-configs '[
    {"QueueReference":{"QueueId":"'"$SALES_QUEUE_ID"'","Channel":"VOICE"},"Priority":1,"Delay":0},
    {"QueueReference":{"QueueId":"'"$SUPPORT_QUEUE_ID"'","Channel":"VOICE"},"Priority":2,"Delay":0}]' \
  --media-concurrencies '[{"Channel":"VOICE","Concurrency":1}]' \
  --query 'RoutingProfileId' --output text)
```

Queue priority: lower = higher priority. Media concurrency: VOICE
typically 1, CHAT 3-5, TASK 5-10. Skill requirements and the
three-component model (skill/proficiency/required-skill) are
detailed in `references/routing-and-lex-integration.md`.

## Step 6 — Agent hierarchy

```bash
HIERARCHY_GROUP_ID=$(aws connect create-user-hierarchy-group \
  --instance-id "$INSTANCE_ID" \
  --name "Sales - North America" \
  --parent-group-id <parent-group-id-or-omit> \
  --query 'HierarchyGroupId' --output text)
```

## Step 7 — Phone number claim (toll-free, DID)

```bash
PHONE_NUMBER_ID=$(aws connect claim-phone-number \
  --instance-id "$INSTANCE_ID" \
  --target-arn "arn:aws:connect:us-east-1:123456789012:instance/$INSTANCE_ID" \
  --phone-number-description "Main inbound toll-free" \
  --phone-number-type TOLL_FREE \
  --phone-number +18005551234 \
  --query 'PhoneNumberId' --output text)
```

For DID: `--phone-number-type DID`. Porting: use the console or
`create-task` to start; requires a Letter of Authorization and may
take 2-4 weeks. Match phone number region to instance region.

## Step 8 — Skills-based routing

Three components must all be configured:

| Component | Where | Example |
|---|---|---|
| Skill | Instance (defined once) | "Sales", proficiency levels 1-5 |
| Skill proficiency | User (per-agent) | Agent A: Sales=5, Support=3 |
| Required skill | Contact (via SetAttributes or TransferToQueue) | Contact X: Sales, proficiency ≥ 4 |

Skills are typically defined via the Connect console. Once defined,
agents are assigned proficiencies via `create-user` /
`update-user-routing-profile`. Contacts specify required skills via
contact attributes set in the flow. See
`references/routing-and-lex-integration.md` for the routing-match
algorithm.

## Step 9 — Amazon Lex bot integration (IVR)

Lex V2 bots are integrated via the InvokeAmazonLex block. The bot
elicits an intent and fills slots via conversation, then returns
intent + slots to the flow.

Prerequisites: Lex V2 bot with at least one published alias (NOT
DRAFT); bot locale matches the Connect instance language.

```json
{
  "Identifier": "lex-ivr", "Type": "Action",
  "Parameters": {
    "BotAliasArn": "arn:aws:lex:us-east-1:123456789012:bot-alias/CustomerService:Prod",
    "Intent": "RouteCall", "Slots": {"department": null},
    "SessionAttributes": {"caller_id": "$.CustomerEndpoint.Address"}
  },
  "Transitions": {
    "NextAction": "branch-on-department",
    "Exceptions": [{"NextAction": "transfer-default", "Error": "Lex.Timeout"}]
  }
}
```

Verify: `aws lexv2-models describe-bot-alias` and
`aws lexv2-runtime recognize-text`. Lex V1 is on a deprecation
path — use Lex V2 for all new deployments.

## Step 10 — Voice ID (speaker enrollment, fraud)

Amazon Connect Voice ID authenticates callers by voice biometrics.

Prerequisites: Voice ID domain created; consent disclosure in the
flow (legal requirement); opt-in/opt-out handling.

```json
{
  "Identifier": "voice-id-enroll", "Type": "Action",
  "Parameters": {"VoiceIdDomainId": "<domain-id>", "VoiceIdOperation": "ENROLL_OR_AUTHENTICATE"},
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

## Step 11 — Contact Lens (sentiment, transcription, redaction)

| Feature | Mode | Use case |
|---|---|---|
| Real-time sentiment | Real-time | Supervisor alerts on negative sentiment |
| Post-call transcription | Post-call | Searchable call transcripts |
| Post-call summary | Post-call | Auto-generated issue + outcome summary |
| Sensitive-data redaction | Post-call | Mask credit card / SSN in transcript |
| Categories | Both | Auto-tag contacts by keyword / sentiment pattern |

```bash
aws connect update-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --association-id <association-id> \
  --resource-type CONTACT_LENS
```

## Step 12 — Chat, voice, task channels

| Channel | Provisioning |
|---|---|
| VOICE | Phone number claimed + contact flow |
| CHAT | Chat widget on website / mobile; chat contact flow |
| TASK | Task template created; task contact flow |

```bash
aws connect create-task-template \
  --instance-id "$INSTANCE_ID" \
  --name "follow-up-task" \
  --contact-flow-id <task-flow-id> \
  --fields '[{"Description":"Reason","Id":"reason","Type":"TEXT"}]' \
  --status ACTIVE
```

## Step 13 — S3 recording storage (KMS encryption)

```bash
aws s3api put-bucket-encryption \
  --bucket connect-recordings-123456789012 \
  --server-side-encryption-configuration \
    '{"Rules":[{"ApplyServerSideEncryptionByDefault":{"SSEAlgorithm":"aws:kms","KMSMasterKeyID":"arn:aws:kms:us-east-1:123456789012:key/abc123"}}]}'

aws connect associate-instance-storage-config \
  --instance-id "$INSTANCE_ID" \
  --resource-type CALL_RECORDINGS \
  --storage-config \
    '{"S3Config":{"BucketName":"connect-recordings-123456789012","BucketPrefix":"recordings","EncryptionConfig":{"EncryptionType":"KMS","KeyId":"arn:aws:kms:us-east-1:123456789012:key/abc123"}},"StorageType":"S3"}'
```

KMS key policy MUST grant `connect.amazonaws.com` Encrypt/Decrypt/
GenerateDataKey with `aws:SourceAccount` condition. Plain S3
recordings are unencrypted at rest — always use SSE-KMS.

## Step 14 — Real-time and historical metrics

| Type | Source | Latency |
|---|---|---|
| Real-time (ContactFlow, RoutingProfile, Queue, Agent) | Instance built-in | Seconds |
| Historical (ContactTraceRecord) | S3 export or console | Up to 24 months |
| Custom real-time metrics | Kinesis stream | Seconds |

```bash
aws connect get-contact-metrics --instance-id "$INSTANCE_ID" \
  --filters '{"Queues":["'"$QUEUE_ID"'"],"Channels":["VOICE"]}'
```

## Step 15 — Recent features

- **Amazon Q in Connect (2023-2026):** generative AI assistant for
  agents — real-time suggested responses and KB articles.
- **Customer Profiles (2023-2024):** unified profile store with
  event-triggered updates.
- **Amazon Connect Cases (2023-2024):** case management for
  multi-contact issues; integrates with Tasks.
- **Voice ID generative improvements (2024-2025):** reduced
  enrollment time, improved fraud-risk accuracy, multi-language.
- **Contact Lens real-time summaries (2024-2025):** generative AI
  summaries in real-time, not just post-call.
- **Amazon Lex V2 generative AI (2024-2025):** open-ended intent
  elicitation and assisted slot filling.
- **WebRTC media streaming (2024-2025):** browser-based voice
  reducing PSTN costs.

## NEVER do these things

1. **NEVER author a contact flow without verifying referenced
   resources.** A flow with a dangling queue/Lambda/Lex ARN
   creates successfully but fails at run time.
2. **NEVER invoke a Lambda without a resource policy granting
   Connect.** Without it, InvokeLambda returns AccessDenied. Add
   via `aws lambda add-permission --principal connect.amazonaws.com`.
3. **NEVER assume a routing profile without skills produces
   skills-based routing.** Without skill requirements, routing
   silently degrades to queue-priority.
4. **NEVER use Lex V1 for new deployments.** Lex V1 is on a
   deprecation path. Use Lex V2 via InvokeAmazonLex.
5. **NEVER claim a phone number in a region different from the
   instance.** US toll-free does not work in EU instances.
6. **NEVER enable Voice ID without consent disclosure.** Voice
   biometrics require caller consent (legal requirement).
7. **NEVER store call recordings in S3 without KMS encryption.**
   Always use SSE-KMS with a key policy granting Connect.
8. **NEVER use a DRAFT Lex bot alias in production.** Connect
   invokes published aliases. DRAFT changes can break the flow
   silently.
9. **NEVER forget exceptions on InvokeLambda blocks.** Handle
   AccessDenied, Timeout, GenericError — otherwise the contact is
   trapped.
10. **NEVER assume instance alias is mutable.** Alias is set at
    instance creation and is immutable.

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
  [✓] Contact Lens: post-call (transcription, sentiment, redaction)
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

- **Flow fails at run time despite creating:** referenced resource
  (queue/Lambda/Lex) does not exist or ARN is wrong. Pre-flight
  check every referenced resource.
- **Lambda invocations return AccessDenied:** Lambda lacks a
  resource policy granting `connect.amazonaws.com`. Add via
  `aws lambda add-permission --principal connect.amazonaws.com
  --source-arn <instance-arn>`.
- **Contacts route to wrong agents:** routing profile lacks skill
  requirements → routing is pure queue-priority.
- **Phone number claim fails:** different region from instance, or
  not available in AWS pool.
- **Lex bot invocations time out:** alias is DRAFT (not published),
  or locale does not match instance language.
- **Voice ID enrollment fails:** caller did not provide consent
  (consent disclosure prompt missing in flow).
- **Recordings not in S3:** KMS key policy or S3 bucket policy
  blocks Connect. Verify both grant `connect.amazonaws.com`.
- **Real-time metrics missing:** instance created before the
  feature was enabled, or stream not configured.

## Domain

AWS CloudOps / Amazon Connect Contact Center Provisioning —
Instances, Contact Flows, Queues, Routing Profiles, Phone Numbers,
Voice ID, Contact Lens, Channels, Recording Storage, Metrics.

## AWS documentation

- **Amazon Connect Administrator Guide** — https://docs.aws.amazon.com/connect/latest/adminguide/what-is-amazon-connect.html
- **Create instance (SAML, Connect dir, existing dir)** — https://docs.aws.amazon.com/connect/latest/adminguide/connect-launch.html
- **Contact flows (drag-and-drop, JSON)** — https://docs.aws.amazon.com/connect/latest/adminguide/contact-flows.html
- **Contact flow JSON schema** — https://docs.aws.amazon.com/connect/latest/adminguide/contact-flow-language.html
- **Lambda function invocation** — https://docs.aws.amazon.com/connect/latest/adminguide/connect-lambda-functions.html
- **Queues, routing profiles, skills-based routing** — https://docs.aws.amazon.com/connect/latest/adminguide/queues-and-routing.html
- **Claim phone numbers** — https://docs.aws.amazon.com/connect/latest/adminguide/claim-phone-number.html
- **Amazon Lex integration / Voice ID** — https://docs.aws.amazon.com/connect/latest/adminguide/connect-lex-bots.html
- **Contact Lens for Amazon Connect** — https://docs.aws.amazon.com/connect/latest/adminguide/enable-analytics.html
- **Chat / Task channels** — https://docs.aws.amazon.com/connect/latest/adminguide/chat.html
- **S3 recording storage with KMS** — https://docs.aws.amazon.com/connect/latest/adminguide/setup-data-storage.html
- **Real-time and historical metrics** — https://docs.aws.amazon.com/connect/latest/adminguide/metrics.html
- **API reference / Amazon Q in Connect** — https://docs.aws.amazon.com/connect/latest/APIReference/Welcome.html