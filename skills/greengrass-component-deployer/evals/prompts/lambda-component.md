# Eval: lambda-component

**Difficulty:** medium
**Branch:** READY_TO_DEPLOY — Lambda component with aws.lambda as HARD dependency, Lambda ARN cited, component created from function ARN

## Prompt

Create a Greengrass v2 component from Lambda function
arn:aws:lambda:us-east-1:123456789012:function:edge-data-processor:5
named com.example.EdgeDataProcessor version 1.0.0. Deploy to
thing group DataProcessors (2 devices) in us-east-1. The
component must depend on aws.lambda version 2.3.0 as a HARD
dependency. Tags: Environment=production, Runtime=lambda.
