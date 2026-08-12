# Eval: instance-id-target-association

**Difficulty:** medium
**Branch:** OPERATION_COMPLETED — static instance-ID targeting, cron(0 0 3 ? * SUN *) schedule, integer rate control (1/1 for one-at-a-time)

## Prompt

Create an SSM State Manager association named
HardenPetServers in us-east-1. Use custom document
Custom-HardenBaseline (default version). Target instance IDs
i-aaa111bb222 and i-ccc333dd444. Schedule cron(0 0 3 ? * SUN *)
(03:00 UTC every Sunday). Run on creation. Integer rate control:
max-concurrency=1, max-errors=1. Route output to
s3://my-ssm-output/ssm-output/ (SSE-KMS enabled). Parameters:
Mode=Strict.
