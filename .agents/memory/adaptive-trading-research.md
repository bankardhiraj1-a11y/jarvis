---
name: Adaptive trading research
description: Evidence limits when comparing more strategy families or trading sessions on the same development history
---

Treat additional strategy and session searches on reused development data as one accumulating selection process, not independent confirmations.

**Why:** The project has repeatedly expanded its research to pursue higher accuracy and more daily calls. Reusing the same fit/inner-validation partitions can favor chance results even when the final holdout remains untouched.

**How to apply:** Record the combined search scope, freeze each experiment before replay, and distinguish “best among tested” from “validated.” Use genuinely new forward paper observations or a preserved final holdout for independent confirmation; never retune a held-out period.

Keep market availability, named market-session conventions, and strategy entry windows separate.

**Why:** The inherited 16:00–23:00 UTC entry restriction was mistaken for spot gold’s market opening time. Europe/US session clocks also change with daylight saving and do not define OANDA instrument tradeability.

**How to apply:** State the named time zones and local-clock conventions in session comparisons, convert each historical date with daylight-saving rules, and require genuine provider tradeability independently of the strategy window.