# Baseline (no-skill) — ecs-fargate-otel-python

> This is the response a model produces **without** the skill definition.
> It misses the ADOT Collector sidecar container definition, the OTel SDK
> setup (resource, span processor, exporter), the BotocoreInstrumentor
> patching, the custom sampling rule for the checkout endpoint, the
> annotation discipline, and the structured checklist.

---

You can enable tracing on your Flask app by installing the OpenTelemetry
packages:

```bash
pip install opentelemetry-instrumentation-flask
```

Then add the instrumentation to your app:

```python
from opentelemetry.instrumentation.flask import FlaskInstrumentor
FlaskInstrumentor().instrument_app(app)
```

For the collector, you can use the AWS Distro for OpenTelemetry. Set
up a sidecar container in your task definition.

You should also add some sampling rules in the X-Ray console.
