# Eval prompt: missing-required-fields

Design a deployment plan for a Pinpoint campaign. Emit the standard
VERDICT block.

Requirements:

- Campaign name: promo-blast
- The user wants to send a promotional message to their customers.

The user did not specify:

- Project ID (which Pinpoint project to deploy in)
- Channel (email / SMS / push / voice)
- Segment (which audience to target)
- Message template or inline message body
- Schedule (immediate or scheduled start time)
- Whether quiet time, frequency caps, or A/B testing is needed

The user expects the skill to identify what is missing and list the
required fields before producing a deployment plan.
