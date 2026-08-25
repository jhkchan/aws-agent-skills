# Worked Examples (load on demand) — Connect Instance Deployer

Secondary worked examples and full CLI payloads moved verbatim from SKILL.md. Loaded on demand.

---

## Worked example — SAML instance with Lambda-driven flow and Lex IVR (checklist form) (moved from SKILL.md)

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
