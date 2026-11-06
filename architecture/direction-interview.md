# Direction interview: decisions and open questions

Date: 2026-11-06. Captures the user's answers following the [direction review](direction-review.md). These are requirements clarified in conversation; implementation and ADR changes remain to be designed.

## Confirmed requirements

| Topic | User's decision |
| --- | --- |
| Multiple dashboards | Support both screens in different places and different scheduled views on the same screen. |
| Scheduling | Each screen has an independent schedule, with weekday/weekend rules and time-of-day rules within each. View selection is automated. |
| Data-dependent rendering | Source data and rendering can change content within an assigned block. That does not change the block's geometry, layout, or panel assignment. Data-driven layout reprioritization is outside the stated requirement. |
| Shared sources | One source can supply data used differently by multiple views. Each view can select a different subset and render it differently. Scheduled views can change both the subset and layout. |
| Cache freshness | The source decides whether the last fetch is recent enough to reuse cached data or whether it must fetch again. Screens do not control source freshness. |
| Fetch failure | Prefer an unavailable state in most cases. Allow source-specific exceptions that use cached data, such as train schedules, with a clear indication that it is stale. |

## Concrete examples

**Room temperatures:** one source supplies temperatures for all rooms. The first-floor screen normally shows first-floor rooms; the second-floor screen shows second-floor rooms. At a scheduled time, one screen can switch to a different layout showing all rooms.

**Trash collection:** marking collection as done changes what the source/renderer displays within the existing block. It does not remove or reassign the block or cause surrounding content to reflow. The completion action and its storage were not designed in this interview.

## Questions still open

- What invokes a source's freshness check: a data request, a background timer, or both? Source ownership of freshness does not settle this.
- How often are dashboards composed and published, and what triggers those operations?
- For each source, what are the cache duration, maximum acceptable stale age, and exact unavailable/stale presentation?
- Are all target screens the same resolution and bitmap format?
- How should editing, realistic preview, activation/reload, and rollback work?
- Where does user-maintained state, such as “trash taken out,” live, and how is it changed?

The next interview can resume with source invocation and dashboard composition triggers. No runtime changes were made.

Review method: conversation-to-requirements fidelity check completed using the existing FPF/protocol basis recorded in the direction review. Confirmed answers and unresolved implementation choices are kept separate.
