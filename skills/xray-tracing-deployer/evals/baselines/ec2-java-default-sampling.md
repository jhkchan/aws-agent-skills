# Baseline (no-skill) — ec2-java-default-sampling

> This is the response a model produces **without** the skill definition.
> It produces a basic daemon setup but misses the AWS SDK v2
> instrumentation (TracingHandler), the GetSamplingRules + GetSamplingTargets
> permissions, the annotation vs metadata distinction, the systemd
> service configuration, and the structured checklist.

---

To enable X-Ray tracing on your Java Spring Boot app, you need to:

1. Download the X-Ray daemon and run it on your EC2 instances.
2. Add the aws-xray-sdk dependency to your pom.xml.
3. Configure your instance profile to allow X-Ray access.

```xml
<dependency>
  <groupId>com.amazonaws</groupId>
  <artifactId>aws-xray-recorder-sdk-core</artifactId>
</dependency>
```

You can download the daemon from the AWS S3 bucket and run it as a
background process.

For sampling, just use the default rule in the console.
