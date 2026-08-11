# Eval prompt: ddb-streams-lambda-filter-dlq

Design a deployment plan for a production EventBridge Pipe. Emit the
standard VERDICT block (PIPE_SPEC, VERDICT, ARCHITECTURE, CHECKLIST,
FINDINGS, DEPLOY_COMMANDS).

Requirements:

- Pipe name: prod-orders-pipe
- Source: DynamoDB Streams
  arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01T00:00:00.000
  (StreamStatus=ENABLED)
- Filter pattern: NewImage.status.S = CONFIRMED
- Enrichment: none
- Target: Lambda
  arn:aws:lambda:us-east-1:111111111111:function:orders-processor
  (state=Active; resource policy grants lambda:InvokeFunction to
  pipes.amazonaws.com)
- Batch: window 5s, size 100, retry 3, record age 3600s
- DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq (queue policy
  grants sqs:SendMessage to the pipe role)
- IAM: pipe role
  arn:aws:iam::111111111111:role/EventBridgePipes-prod-orders with
  trust policy scoped to SourceAccount=111111111111 and SourceArn
  arn:aws:pipes:us-east-1:111111111111:pipe/prod-orders-pipe

Existing-account context: the Orders table has streams enabled; the
Lambda function has a resource policy granting invoke to
pipes.amazonaws.com; the DLQ was created last week and its policy
already grants the pipe role. IAM principal holds pipes:CreatePipe,
StartPipe, DescribePipe.
