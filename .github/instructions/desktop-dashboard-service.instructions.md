---
applyTo: "services/desktop_dashboard_service/**"
---

- Preserve the current DDD and hexagonal split: keep core models and ports in `domain`, orchestration in `application`, integrations in `adapters`, and wiring in `bootstrap`.
- Use test-first workflow for service changes: add or update a failing pytest, implement the change, then re-run the service test suite.
- When changing service structure, extension points, configuration, layout contracts, or MQTT output, update `services/desktop_dashboard_service/architecture/current-specification.md` and add or revise an ADR in `services/desktop_dashboard_service/architecture/`.
- Keep source plugins, renderer plugins, layout rendering, and publishing loosely coupled through the existing ports.
- Preserve compatibility with the firmware's retained MQTT bitmap contract unless the change explicitly updates the repository-level architecture documents as well.
