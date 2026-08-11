# Eval: ec2-java-default-sampling

**Difficulty:** hard
**Branch:** READY_TO_DEPLOY — EC2 systemd, Java SDK v2, default sampling, annotations

## Prompt

Enable X-Ray distributed tracing on a Java Spring Boot application
named "orders-api" running on EC2 instances in us-east-1. The app
uses AWS SDK v2 (DynamoDB, S3, SQS). Instance profile role
ec2-orders-role. Deploy the X-Ray daemon 4.x via systemd. Use the
aws-xray-recorder-sdk-core and aws-xray-recorder-sdk-aws-sdk-v2
Maven packages. Default sampling rule (reservoir 1/s, rate 5%).
Annotations: order_id, environment=production, region=us-east-1.
Metadata: request_body_size. Enable CloudWatch ServiceLens.
Account: 123456789012.
