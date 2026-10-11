# AGENTS.md — Repository Guidance for Odin and Hermes/Raven Agents

## Repository Context
- **Repository**: `ponder/book-utils`
- **Application**: Book-Utils — Automated E-Book Converter & Malformed EPUB Repair Utility.
- **Primary Language & Stack**: Python 3.11, Calibre CLI (`ebook-convert`), epubcheck (Java), schedule.

## Architecture & Layout
- `converter.py`: Main processing script that monitors book folders, converts non-EPUBs, validates with epubcheck, and repairs corrupt files.
- `tests/`: Automated unit and integration test suite (`pytest`).
- `Dockerfile` & `docker-compose.yml`: Homelab container deployment.

## Absolute Guardrails & Constraints
1. **Idempotence & Safety**: File processing must never delete original books unless a successful conversion/repair is verified.
2. **Error Isolation**: Malformed files that fail repair must be logged cleanly without crashing the daemon loop.
3. **Testing Integrity**: All unit tests must pass via `pytest` before submitting pull requests.

## Git & PR Conventions
- Default base branch is `main`.
- Features/fixes are pushed to `huginn/issue-<ID>` or `muninn/issue-<ID>` and submitted as Pull Requests against `main`.
