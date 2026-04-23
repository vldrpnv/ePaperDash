# Copilot instructions for ePaperDash

Before making changes, read:

1. `docs/architecture/README.md`
2. `/architecture/current-specification.md`
3. Relevant files in `docs/architecture/adr/`
4. Relevant files in `docs/architecture/design_decisions/`
5. Relevant files in `/architecture/` and `services/desktop_dashboard_service/architecture/` when the change affects the desktop service or repository-level contracts

## Required working style

- Capture the expected specification first.
  - Write or update acceptance criteria before changing behavior.
  - If the behavior is not yet clear, stop and clarify the contract instead of guessing.
- Prefer test-first development.
  - Add or update tests before implementation whenever the code can be tested.
  - If a change is hard to test because logic is embedded in hardware-facing code, first look for a small seam that can be extracted into testable logic.
  - If automated tests are still not practical, document the missing test seam and provide a concrete manual verification plan.
  - For desktop service behavior changes, write or update tests before implementation and run the existing pytest suite.
- Preserve architectural intent.
  - Keep the wake → connect → receive → compare → render → sleep lifecycle intact unless the change intentionally revises an ADR.
  - Treat battery use, bounded active time, and fail-safe recovery as primary constraints.
  - Preserve the current DDD and hexagonal split in `services/desktop_dashboard_service` unless the change intentionally updates the service architecture records.
- Preserve the existing data contract.
  - The dashboard payload is a raw 800 × 480 1-bit bitmap unless the specification and decision records are updated together.
  - Prefer minimal changes that preserve the firmware-to-service MQTT bitmap contract.
- Update the decision records when design intent changes.
  - Add or amend an ADR for architectural changes.
  - Add or amend a design decision record for implementation-level changes.
  - When a change affects repository-level behavior or integration contracts, update the relevant architecture directory in the same change.

## Harness state

- `docs/architecture/README.md` is the canonical navigation index for architecture context.
- Use the summary tables in that file to decide which ADRs and design decisions must be loaded for the current task.
- There is currently no committed automated test or CI harness for the firmware in this repository.
- The desktop service has a committed pytest suite and should keep using it.
- Until an automated firmware test harness exists, changes should include explicit acceptance criteria first and either:
  - tests added first when a seam exists, or
  - a documented missing test seam plus a concrete manual verification plan.

## Intended agent workflow

1. Load `docs/architecture/README.md`.
2. Load `/architecture/current-specification.md` and the service architecture docs when the task touches the desktop service or repository contracts.
3. Load only the ADRs and design-decision records whose scope matches the requested change.
4. Capture or refine the specification before editing behavior.
5. Prefer test-first changes; if not practical, document the missing seam and manual verification.
6. Keep changes small and update the relevant decision records whenever design intent changes.

## Repository-specific notes

- Favor small, explicit changes over broad abstraction.
- Keep configuration in `config.h` unless a documented decision changes that boundary.
