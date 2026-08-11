# Eval prompt: enrichment-lambda-transformation

Design a deployment plan for a production EventBridge Pipe with an
enrichment stage. Emit the standard VERDICT block.

Requirements:

- Pipe name: prod-orders-enriched
- Source: DynamoDB Streams
  arn:aws:dynamodb:us-east-1:111111111111:table/Orders/stream/2026-08-01T00:00:00.000
  (StreamStatus=ENABLED)
- Filter pattern: NewImage.status.S = CONFIRMED
- Enrichment: Lambda
  arn:aws:lambda:us-east-1:111111111111:function:orders-enrich
  (state=Active; the function joins customer profile data from a
  CustomerService API and returns a transformed batch payload;
  resource policy grants lambda:InvokeFunction to pipes.amazonaws.com)
- Target: Step Functions
  arn:aws:states:us-east-1:111111111111:stateMachine:OrderWorkflow
  (status=ACTIVE, type=STANDARD)
- Batch: window 10s, size 50, retry 3, record age 7200s
- DLQ: arn:aws:sqs:us-east-1:111111111111:prod-pipe-dlq
- IAM: pipe role trust policy scoped to SourceAccount=111111111111
  and SourceArn for prod-orders-enriched. Permissions include
  dynamodbstreams:GetRecords, dynamodbstreams:GetShardIterator,
  dynamodbstreams:DescribeStream, lambda:InvokeFunction on
  orders-enrich, states:StartExecution on OrderWorkflow,
  sqs:SendMessage on prod-pipe-dlq.

The user wants the enrichment Lambda to receive the full batched
payload, join customer data, and return a transformed batch that
Step Functions consumes as input.
