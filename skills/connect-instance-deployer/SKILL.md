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

The three misconceptions in full (contact flow is a JSON DAG, routing profile carries skill requirements, IVR is conversational Lex) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before designing the deployment.

## Configuration dependency graph

The full dependency table (instance → flow → queue/routing/Lambda/Lex → phone/Voice ID/Contact Lens/recording/metrics) and cross-dependency gotchas moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand before sequencing the deployment.

## Expert heuristic: contact flow JSON with Lambda invoke blocks

Contact-flow DAG walkthrough (CheckHours → InvokeLambda → Lex → branch → TransferToQueue), InvokeLambda JSON anatomy, and the resource-policy implication moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when authoring flows.

## Expert heuristic: routing profile skill requirements

Skills-based routing worked scenario (Agent A/B eligibility by proficiency) and the three-component model moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when configuring routing.

## Expert heuristic: Lex bot integration for IVR

Conversational-IVR walkthrough (intent elicitation, slot filling, branch-on-slot, unknown-intent loop) and published-alias requirement moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when wiring Lex.

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

Step 1 create-instance CLI (SAML / CONNECT_MANAGED / EXISTING_DIRECTORY variants) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when provisioning the instance.

## Step 2 — Contact flow JSON

Step 2 block-category catalog, create-contact-flow CLI, JSON schema notes, and verify commands moved verbatim to [references/contact-flow-json-and-lambda.md](references/contact-flow-json-and-lambda.md).
Load on demand when authoring the flow.

## Step 3 — Lambda function integration (InvokeLambda block)

Step 3 add-permission CLI (connect.amazonaws.com principal + SourceArn), Python handler example, and exception-handling requirement moved verbatim to [references/contact-flow-json-and-lambda.md](references/contact-flow-json-and-lambda.md).
Load on demand when integrating Lambda.

## Step 4 — Queues and quick-connect lists

Step 4 create-queue and create-quick-connect CLI moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when creating queues.

## Step 5 — Routing profiles (skills, proficiency, queue associations)

Step 5 create-routing-profile CLI (queue configs, priorities, media concurrencies) and queue-priority guidance moved verbatim to [references/routing-and-lex-integration.md](references/routing-and-lex-integration.md).
Load on demand when creating routing profiles.

## Step 6 — Agent hierarchy

Step 6 create-user-hierarchy-group CLI moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when building the hierarchy.

## Step 7 — Phone number claim (toll-free, DID)

Step 7 claim-phone-number CLI, DID/porting notes, and region-matching rule moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when claiming numbers.

## Step 8 — Skills-based routing

Step 8 three-component table (skill on instance, proficiency on agent, required skill on contact) and configuration notes moved verbatim to [references/routing-and-lex-integration.md](references/routing-and-lex-integration.md).
Load on demand when configuring skills-based routing.

## Step 9 — Amazon Lex bot integration (IVR)

Lex V2 bots are integrated via the InvokeAmazonLex block. The bot
elicits an intent and fills slots via conversation, then returns
intent + slots to the flow.

Prerequisites: Lex V2 bot with at least one published alias (NOT
DRAFT); bot locale matches the Connect instance language.

Step 9 InvokeAmazonLex block JSON (BotAliasArn, Intent, Slots, SessionAttributes, Lex.Timeout exception) moved verbatim to [references/routing-and-lex-integration.md](references/routing-and-lex-integration.md).
Load on demand when wiring Lex IVR.

Verify: `aws lexv2-models describe-bot-alias` and
`aws lexv2-runtime recognize-text`. Lex V1 is on a deprecation
path — use Lex V2 for all new deployments.

## Step 10 — Voice ID (speaker enrollment, fraud)

Step 10 Voice ID prerequisites (domain, consent disclosure) and block JSON (enroll/authenticate, result branches) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when enabling Voice ID.

## Step 11 — Contact Lens (sentiment, transcription, redaction)

Step 11 Contact Lens feature table (real-time vs post-call) and storage-config CLI moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when enabling Contact Lens.

## Step 12 — Chat, voice, task channels

Step 12 channel table (VOICE/CHAT/TASK provisioning) and create-task-template CLI moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when covering channels.

## Step 13 — S3 recording storage (KMS encryption)

Step 13 put-bucket-encryption + associate-instance-storage-config CLI and the KMS key-policy requirement moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when configuring recordings.

## Step 14 — Real-time and historical metrics

Step 14 metrics table (real-time, historical CTR, Kinesis custom) and get-contact-metrics CLI moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand when wiring metrics.

## Step 15 — Recent features

Step 15 recent features (Amazon Q in Connect, Customer Profiles, Cases, Voice ID improvements, real-time summaries, Lex generative AI, WebRTC) moved verbatim to [references/advanced-patterns.md](references/advanced-patterns.md).
Load on demand for latest capabilities.

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

Worked example — SAML instance with Lambda-driven flow and Lex IVR (READY_TO_DEPLOY checklist + verification commands) moved verbatim to [references/worked-examples.md](references/worked-examples.md).
Load on demand for the filled-in output shape.

## Error handling

Error handling (dangling flow refs, Lambda AccessDenied, wrong-agent routing, phone-claim failures, Lex timeouts, Voice ID consent, missing recordings, metrics) moved verbatim to [references/error-handling.md](references/error-handling.md).
Load on demand when diagnosing failures.

## References (load on demand)

- [references/advanced-patterns.md](references/advanced-patterns.md) — Mindset misconceptions, configuration dependency graph, expert heuristics, Step 1/4/6/7/10-15 provisioning recipes, and recent features moved from SKILL.md.
- [references/worked-examples.md](references/worked-examples.md) — the checklist-form worked example moved from SKILL.md.
- [references/error-handling.md](references/error-handling.md) — error handling for flows, Lambda, routing, phone claims, Lex, Voice ID, recordings, and metrics moved from SKILL.md.
- [references/contact-flow-json-and-lambda.md](references/contact-flow-json-and-lambda.md) — now also holds the Step 2 flow-JSON detail and Step 3 Lambda-integration detail moved from SKILL.md.
- [references/routing-and-lex-integration.md](references/routing-and-lex-integration.md) — now also holds the Step 5 routing-profile CLI, Step 8 skills components, and Step 9 InvokeAmazonLex JSON moved from SKILL.md.

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