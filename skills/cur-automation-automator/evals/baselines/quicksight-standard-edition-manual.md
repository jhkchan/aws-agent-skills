# Baseline (no-skill) response: quicksight-standard-edition-manual

This file captures what a generic assistant produces WITHOUT the
cur-automation-automator skill loaded — the contrast that proves the
skill catches the QuickSight Standard vs Enterprise edition gate for
scheduled SPICE refresh.

---

Here's how to add QuickSight dashboards on top of your CUR + Athena:

1. Open QuickSight and sign up if you haven't already.
2. Connect to Athena as a data source:
   - Datasets → New dataset → Athena
   - Data source name: `cur-athena`
   - Workgroup: `primary` (or your finops workgroup)
3. Choose your `cur_hourly` table and click "Edit/Preview Data".
4. Import to SPICE for faster dashboard interactions.
5. Set up a scheduled refresh:
   - Dataset → Schedule refresh → Daily at 9am
6. Create a dashboard with top-spenders visualizations.

That's it. The Standard edition should be fine for getting started.
Let me know if you need help building specific visualizations.
