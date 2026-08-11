---
description: Provision an Amazon Connect instance, contact flow, queues, routing profile, phone number, and integrations (Lambda, Lex V2 IVR, Voice ID, Contact Lens, S3 recording with KMS) with production-grade defaults. Emits a READY_TO_DEPLOY checklist with verification commands.
nl_triggers:
  - "create connect instance"
  - "deploy connect instance"
  - "contact flow json"
  - "lambda invoke block"
  - "connect queue"
  - "connect routing profile"
  - "routing profile skill"
  - "connect skill proficiency"
  - "connect phone number"
  - "claim phone number toll-free"
  - "did porting"
  - "lex bot ivr"
  - "invokeamazonlex"
  - "voice id enrollment"
  - "contact lens sentiment"
  - "connect task"
  - "s3 recording kms"
  - "connect chat"
  - "agent hierarchy"
  - "saml identity connect"
routes_to: connect-instance-deployer
---

# /aws:deploy-connect-instance

Activate the `connect-instance-deployer` skill and produce a deployment
plan for a production-grade Amazon Connect instance with contact flows,
queues, routing profiles, phone numbers, and channel integrations.

## What it does

The skill walks the contact-center provisioning procedure and emits a
READY_TO_DEPLOY checklist:

1. Instance creation — three identity modes (SAML 2.0, Amazon Connect
   managed directory, existing AWS Directory Service directory)
2. Contact flow JSON — drag-and-drop in console OR programmatic via
   CLI/CloudFormation/Terraform; block categories (Action, Branch,
   Transfer, Terminal)
3. Lambda function integration — InvokeLambda block, FunctionARN,
   InvocationTimeLimitSeconds, exception handling (AccessDenied,
   Timeout, GenericError), Lambda resource policy granting
   connect.amazonaws.com
4. Queues and quick-connect lists — HoursOfOperation, hold-flow,
   outbound caller ID
5. Routing profiles — queue associations (priority, delay), media
   concurrencies per channel, skill requirements
6. Agent hierarchy — org structure (region / business unit / team)
7. Phone number claim — toll-free, DID, toll-free-DID; per-region
   matching; porting workflow
8. Skills-based routing — skill (instance level), proficiency (agent
   level), required skill (contact level); all three required for
   skills-based routing
9. Amazon Lex V2 bot integration for IVR — InvokeAmazonLex block,
   bot alias, intent elicitation, slot filling, locale matching
10. Voice ID — speaker enrollment, fraud-risk detection, consent
    disclosure in flow
11. Contact Lens — real-time sentiment, post-call transcription,
    sensitive-data redaction, contact summaries
12. Chat, voice, task channels — chat widget, task templates
13. S3 recording storage with KMS encryption — bucket policy, KMS
    key policy granting connect.amazonaws.com
14. Real-time and historical metrics — built-in real-time, Contact
    Trace Record (CTR) exports for historical
15. Recent features — Amazon Q in Connect, Customer Profiles,
    Connect Cases, generative AI summaries

## When to use

- You need to create a Connect instance.
- You are authoring a contact flow with Lambda invoke blocks.
- You are configuring a routing profile with skill requirements.
- You are claiming a phone number (toll-free, DID).
- You are integrating a Lex V2 bot for conversational IVR.
- You are enabling Voice ID or Contact Lens.
- You are setting up S3 recording storage with KMS encryption.

## When NOT to use

- **Amazon Chime SDK** — different service (real-time communications).
- **Amazon WorkSpaces** — different service (virtual desktops).
- **Standalone Amazon Lex bot deployment** — use Lex skills for bot
  authoring without Connect integration.
- **Auditing existing Connect instances** — use Connect audit skills.

## How to invoke

### Slash command

```
/aws:deploy-connect-instance
```

Then provide: instance alias and identity mode (SAML, Connect dir,
existing dir), contact flow spec (JSON or block description), Lambda
function ARNs, queue names and HoursOfOperation, routing profile
name with skill requirements, phone number to claim (or porting
request), Lex V2 bot alias ARN, Voice ID and Contact Lens decisions,
S3 recording bucket and KMS key, tags.

### Natural language

Any of these routes to the same skill:

- "create a Connect instance with SAML identity"
- "author a contact flow with a Lambda invoke block"
- "configure a routing profile with Sales and Support skills"
- "claim the toll-free number +18005551234"
- "integrate Lex V2 bot CustomerService for IVR"
- "enable Voice ID and Contact Lens"
- "set up S3 recording storage with KMS encryption"

### CLI routing

```bash
node cli/bin/cli.js route "create a connect contact flow"
```

## Pipeline integration

This skill operates in **Phase 1 (Deploy)** of the CloudOps pipeline.
The orchestrator routes to it when the user wants to create Connect
instances, contact flows, queues, routing profiles, or claim phone
numbers. The output checklist feeds into verification pipelines and
downstream audit skills.

## Example

```
You: /aws:deploy-connect-instance

     Create a Connect contact flow on instance inst-abc123 named
     inbound-main-flow. Invoke Lambda lookup-customer and branch
     on the returned department attribute. Handle AccessDenied
     and Timeout exceptions. Instance ARN
     arn:aws:connect:us-east-1:123456789012:instance/inst-abc123.

Skill:
  CONNECT_INSTANCE: inst-abc123 (my-connect-cc, SAML)
  VERDICT: READY_TO_DEPLOY
  CHECKLIST:
    [✓] Contact flow: inbound-main-flow (CONTACT_FLOW, all refs verified)
    [✓] Lambda integration: lookup-customer (resource policy grants Connect)
    [✓] Exceptions: AccessDenied → transfer-default; Timeout → transfer-default
  VERIFICATION_COMMANDS:
    aws connect describe-contact-flow --instance-id inst-abc123 --contact-flow-id <flow-id>
    aws lambda get-policy --function-name lookup-customer
```

## References

- Skill definition: `skills/connect-instance-deployer/SKILL.md`
- Contact flow JSON and Lambda guide: `skills/connect-instance-deployer/references/contact-flow-json-and-lambda.md`
- Routing and Lex integration guide: `skills/connect-instance-deployer/references/routing-and-lex-integration.md`
- Eval suite: `skills/connect-instance-deployer/evals/evals.json`
