# Baseline (no-skill) response: content-filter-nested-depth

---

Your EventBridge rule is not firing even though the pattern seems to
match the event. Since `test-event-pattern` returns false, something in
the pattern is wrong. The deeply nested JSON path looks like it should
work, but maybe EventBridge has trouble with very deep nesting. Try
flattening your event structure and see if that helps. Or simplify the
pattern to test each level one at a time.
