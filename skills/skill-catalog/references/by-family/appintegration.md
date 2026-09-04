# AppIntegration skills (33)

Precise call: `@skills:gh:jhkchan/aws-agent-skills/skills/<name>` (swap `<name>` for a row below).

| Skill | Task type | What it does |
|---|---|---|
| `amazon-mq-broker-deployer` | deploy | Provisions Amazon MQ brokers (ActiveMQ or RabbitMQ) with production defaults: engine selection (ActiveMQ for JMS/OpenWire/STOMP/MQTT/AMQP/WS, RabbitMQ |
| `apigateway-5xx-troubleshooter` | troubleshoot | Diagnoses Amazon API Gateway 5xx errors (500 InternalServerError, 502 BadGateway, 503 ServiceUnavailable, 504 Timeout) through a systematic diagnostic |
| `apigateway-http-api-deployer` | deploy | Provisions production-grade API Gateway HTTP APIs (v2) with routes (ANY, GET, POST, {proxy+} greedy), integration targets (Lambda proxy AWS_PROXY, HTT |
| `apigateway-http-troubleshooter` | troubleshoot | Diagnoses Amazon API Gateway HTTP API failures through a ten-category diagnostic tree: 4xx routing errors ($default route, catch-all route priority, A |
| `apigateway-resource-policy-auditor` | audit | Audits AWS API Gateway REST/HTTP APIs for unauthenticated public methods (authorizationType NONE), API-key-as-auth misconceptions, cross-account resou |
| `apigateway-rest-deployer` | deploy | Provisions production-grade API Gateway REST APIs with correct resource/method models, AWS_PROXY Lambda integrations, IAM/Cognito/Lambda authorizers,  |
| `apigateway-throttle-optimizer` | optimize | Optimises AWS API Gateway throttle and cost across seven dimensions: API type selection (REST $3.50/M vs HTTP $1.00/M requests), stage and method- lev |
| `apigateway-websocket-deployer` | deploy | Provisions Amazon API Gateway WebSocket APIs with production defaults: route selection expression ($request.body.action), connection routes ($connect, |
| `appconfig-deployer` | deploy | Provisions AWS AppConfig resources with production defaults: application creation, environments, configuration profiles (free form, JSON, YAML), deplo |
| `connect-instance-deployer` | deploy | Provisions Amazon Connect instances, contact flows, queues, routing profiles, phone numbers, and integrations with production defaults. |
| `event-driven-automator` | automate | Designs and implements event-driven architectures on Amazon EventBridge. |
| `eventbridge-pipe-deployer` | deploy | Provisions production-grade Amazon EventBridge Pipes connecting sources (DynamoDB Streams, Kinesis, SQS, MSK, Amazon MQ, self-managed Kafka) to target |
| `eventbridge-rule-deployer` | deploy | Provisions Amazon EventBridge rules and targets correctly the first time. |
| `eventbridge-rule-not-firing-troubleshooter` | troubleshoot | Diagnoses Amazon EventBridge rules that fail to fire through a ten-category diagnostic tree: event pattern mismatch (source, detail-type, detail JSON  |
| `eventbridge-scheduler-deployer` | deploy | Provisions Amazon EventBridge Scheduler schedules with production defaults: schedule creation (rate-based vs cron-based), flexible time window (OFF vs |
| `pinpoint-campaign-deployer` | deploy | Provisions Amazon Pinpoint campaigns and engagement workflows — project creation, channels (email, SMS, push, voice), segments (demographic, dynamic,  |
| `pinpoint-journey-deployer` | deploy | Provisions Amazon Pinpoint journeys with production defaults: journey creation (activity-based vs segment-based entry), conditional activity (yes/no s |
| `ses-email-deployer` | deploy | Provisions Amazon SES email infrastructure — domain identity with DNS verification (DKIM CNAME, MX for bounce / complaint), configuration set with eve |
| `sns-delivery-troubleshooter` | troubleshoot | Diagnoses SNS delivery failures through a twelve-category diagnostic tree: HTTP/HTTPS endpoint delivery (subscription confirmation pending, signature  |
| `sns-subscription-operator` | operate | Operates AWS SNS subscription workflows end-to-end — subscription creation (HTTP/HTTPS/SQS/Lambda/email/sms/firehose), subscription confirmation (Pend |
| `sns-topic-deployer` | deploy | Provisions AWS SNS topics with production-grade configuration: correct topic type (Standard vs FIFO), subscriptions (HTTP/S, SQS, Lambda, Email, Fireh |
| `sns-topic-public-subscription-auditor` | audit | Audits AWS SNS topics for public subscription exposure (Principal:"*" with sns:Subscribe or sns:Publish in topic policy), missing KMS encryption (plai |
| `sqs-dead-letter-troubleshooter` | troubleshoot | Diagnoses Amazon SQS messages accumulating in dead-letter queues through a ten-category diagnostic tree: redrive policy maxReceiveCount too low, proce |
| `sqs-dlq-operator` | operate | Operates SQS dead-letter queue lifecycles safely: creates DLQs with correct type (Standard vs FIFO matching source), tunes redrive policy maxReceiveCo |
| `sqs-dlq-policy-auditor` | audit | Audits AWS SQS queues for dead-letter-queue (DLQ) configuration gaps, public access via Principal:* queue policies, encryption-at-rest status (SSE-SQS |
| `sqs-fifo-deployer` | deploy | Provisions Amazon SQS FIFO queues with production defaults: FIFO queue attributes (FifoQueue=true, ContentBasedDeduplication, DeduplicationScope, Thro |
| `sqs-queue-deployer` | deploy | Provisions AWS SQS queues with production-grade configuration: correct queue type (Standard vs FIFO), dead-letter queue with tuned maxReceiveCount, ri |
| `sqs-throughput-optimizer` | optimize | Optimises AWS SQS queue throughput and cost across seven dimensions: queue type selection (Standard vs FIFO), polling strategy (long vs short to elimi |
| `stepfunctions-execution-troubleshooter` | troubleshoot | Diagnoses AWS Step Functions execution failures across Standard and Express workflows. |
| `stepfunctions-express-deployer` | deploy | Provisions Step Functions Express Workflows with production defaults: Express-vs-Standard decision (5-min cap, at-least-once vs exactly-once, per-invo |
| `stepfunctions-map-state-deployer` | deploy | Deploys AWS Step Functions Map state configurations with production defaults: Inline Map (synchronous, max 5000 items, shares parent execution context |
| `stepfunctions-statemachine-auditor` | audit | Audits AWS Step Functions state machines for execution logging coverage (level ALL + includeExecutionData), X-Ray tracing enablement (including the Ex |
| `stepfunctions-statemachine-deployer` | deploy | Provisions production-grade AWS Step Functions state machines with correct type selection (Standard exactly-once up to 1 year vs Express at-least-once |
