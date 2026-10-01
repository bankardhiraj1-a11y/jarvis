---
name: Manual order intent
description: Manual strategy requests are per-order permissions, not authorization to replace or enable automatic strategies
---

Keep manual strategy execution distinct from automatic strategy selection and approval.

**Why:** The creator interrupted an automatic-strategy replacement to request a specific paper order, then requested manual entry across supported market segments. Those requests authorize explicit manual paper orders, not a silent replacement of the automatic strategy or enabling previously disabled automatic agents.

**How to apply:** Preserve the current automatic strategy while accepting user-defined manual entries through their own workflow. A manual signal/session exception must remain attached to that order; retain genuine quote checks, risk limits, rollover/intraday safeguards and paper-only execution. Clearly distinguish submitted, pending, filled and closed states.

Manual Gold strategy exits must not inherit the automatic experiment's elapsed-time holding cap. Manual Indian-market bounded holds remain separate.

**Why:** The creator explicitly rejected an automatic time-based exit for a manually specified M15 strategy and requested its original paper entry be preserved.

**How to apply:** Manage manual Gold by its stop/targets, retaining the disclosed rollover/session safeguard. A correction of an earlier timed paper close must retain the prior close in an audit record, preserve the genuine original entry fields, replay available real price observations, and label adjusted results as strategy-corrected paper—not uninterrupted forward evidence. Never backdate a new fill or silently erase a real recorded close.