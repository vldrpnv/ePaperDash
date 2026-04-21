# Copilot instructions

- Read `/architecture/current-specification.md` and the relevant ADRs before changing behaviour or architecture.
- When a change affects repository-level behaviour or integration contracts, update the relevant architecture directory in the same change.
- Prefer minimal changes that preserve the firmware-to-service MQTT bitmap contract.
- For desktop service behaviour changes, write or update tests before implementation and run the existing pytest suite.
