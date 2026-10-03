# Release review checklist

Before every release the platform team walks the same four gates:

1. **Latency.** "p99 under 200ms on the checkout path."
2. **Rollback.** "One command, under five minutes, no data loss."
3. **Access.** "No new scopes without a security sign-off."
4. **Comms.** "Status page drafted before the deploy starts."

The quoted bars come from the SRE handbook and have not changed since March.
