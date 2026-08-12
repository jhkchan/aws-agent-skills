# Baseline (no-skill) response: bus-mismatch-custom-default

---

Your EventBridge rule is not firing. PutEvents returns 200 and the
pattern matches. Maybe the issue is with the event bus. Check if the
event was put on the right bus. If the rule is on `custom.events-bus`,
make sure PutEvents also targets `custom.events-bus`. The default bus
is used if you don't specify one. You might also want to check the
target Lambda permissions.
