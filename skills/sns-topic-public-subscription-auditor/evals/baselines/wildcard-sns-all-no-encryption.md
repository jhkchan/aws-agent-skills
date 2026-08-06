# Baseline (no-skill) response: wildcard-sns-all-no-encryption

This file captures what a generic assistant produces WITHOUT the
sns-topic-public-subscription-auditor skill loaded — the contrast that proves
the skill adds structure (deterministic VERDICT, enumerated FINDINGS,
specific remediation, encryption-gap reasoning).

---

This SNS topic has a policy that grants sns:* to Principal "*", which is very
dangerous. Anyone can subscribe, publish, modify, or delete the topic. The
topic also does not have KMS encryption enabled, so messages are stored in
plaintext. There is no delivery status logging configured.

You should immediately restrict the topic policy to only allow access from
trusted accounts. You should also enable KMS encryption and set up delivery
logging.
