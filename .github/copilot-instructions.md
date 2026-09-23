# Copilot Project Instructions

This repository is a Python backend project focused on domain models before any UI work.

## Project structure

- Use a `src/` layout for the application package.
- Keep domain models under `src/one_credit/models/`.
- Keep tests under `tests/unit/`.
- Do not implement frontend code at this stage.

## Priorities

1. Establish the project configuration and package layout.
2. Implement core domain models first: `Agent`, `Resource`, `Request`, and `Proposal`.
3. Add unit tests covering the happy path and validation failures for each model.
4. Keep the implementation simple, typed, and testable.

## Standards

- Use Python 3.11+
- Use `pytest` for unit tests.
- Prefer `pydantic` models for validation and serialization.
- Keep model logic lightweight and domain-focused.
