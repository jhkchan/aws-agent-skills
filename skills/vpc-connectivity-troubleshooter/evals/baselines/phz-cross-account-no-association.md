# Baseline (no-skill) response: phz-cross-account-no-association

---

Your application can't resolve `db.corp.example.internal` in account
222222222222. The Route 53 private hosted zone is in account
111111111111 and only associated with the source-owner VPC. To make
it resolve in the consumer account, you need to associate the hosted
zone with the consumer VPC, or set up a Route 53 Resolver FORWARD
rule that points at the source account's Resolver inbound endpoint.

Cross-account private hosted zone associations can be done via AWS
RAM sharing or via Resolver Rules.
