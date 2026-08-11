# Eval: missing-instance-id-prereq

**Difficulty:** easy
**Branch:** PREREQUISITES_MISSING — operator requests a contact flow but no instance ID is provided; flows are children of an instance

## Prompt

Create a contact flow named inbound-main-flow. The flow should
invoke Lambda function lookup-customer. No instance ID is
provided. Queues sales-queue and support-queue.
