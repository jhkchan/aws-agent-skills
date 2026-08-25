# Error handling — lex-bot-deployer

Error-handling deep dives, moved verbatim from SKILL.md for progressive disclosure. Load on demand.

## Error handling (moved from SKILL.md)

### Locale stuck in Building
- A prior build failed. Check `describe-bot-locale` for errors. Common
  causes: malformed utterances referencing undefined slots, slot types
  with no values, duplicate intent names.

### Code hook never fires
- The Lambda resource-based permission is missing or scoped to the wrong
  bot ARN. Verify with `aws lambda get-policy`. Re-run `add-permission`
  with the correct `--source-arn`.

### Runtime returns "Invalid bot alias"
- The alias does not exist or points at a non-Built version. Build the
  locale, create a version, then create or update the alias.

### Conversation logs not delivered
- The Lex service role lacks CloudWatch Logs permissions or the KMS key
  policy does not grant `lexv2.amazonaws.com`. Create the log group first.

### Slot elicitation order is wrong
- Slot priorities are not set or are duplicated. Re-run `update-slot`
  with distinct priorities (1, 2, 3...).

### Voice bot audio quality is poor
- The engine is `standard`. Switch to `neural` for Polly neural voices.
  Verify the phone provider is not transcoding to low-bitrate.
