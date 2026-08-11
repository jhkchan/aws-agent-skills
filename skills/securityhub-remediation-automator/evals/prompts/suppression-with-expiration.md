# Eval prompt: suppression-with-expiration

Design a Security Hub suppression rule for the following accepted-risk
finding. Emit the standard REMEDIATION block including the suppression
rule with expiration date.

Design reference: suppression-with-expiration
Account: 111111111111
Region: us-east-1

Standard: CIS AWS Foundations Benchmark
Finding type: 2.1 (SQS queue without SSE)
Severity: MEDIUM
Sample finding resource: arn:aws:sqs:us-east-1:111111111111:legacy-events-queue
Business justification: Legacy queue being decommissioned in Q4 2026.
Suppression expiration: 2026-12-01.

Configure the suppression via batch-update-findings with an expiration
note and include the daily evaluator Lambda pattern for re-evaluation.
