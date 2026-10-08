## Latest
- Branch `main` (only remote branch on disk). Last commit 2025-08-02: "Use Poetry for dependency management".

## Purpose
A private FastAPI backend for a teacher and school directory with an approval workflow. A shared approval state machine gates which teachers appear in donor-facing browse views. It is not a data-science artifact.

## Stack
Python, FastAPI (`app/main.py`), Poetry (per the last commit), a services-per-domain layout under `app/services/`.

## Key modules
- `/home/user/hithero-api-v2/app/services/shared/approval_state_machine.py` — teacher approval status transitions, valid-transition sets, and validation rules.
- `/home/user/hithero-api-v2/app/services/shared/status_transition_service.py` — applies transitions.
- `/home/user/hithero-api-v2/app/services/shared/profile_validator.py` — profile completeness checks.
- `/home/user/hithero-api-v2/app/services/teacher_browse_service/router.py` — browse endpoints.

## Reusable for dsdk
- D3 — `/home/user/hithero-api-v2/app/services/shared/approval_state_machine.py` — explicit, enumerable transition table with validation; a typed state-machine pattern. Not checked against tests.

## Evidence quality
- Not assessed. Test coverage was not inspected and the repo was not run.

## Open questions
- Does the state machine have tests that enforce its transition table?
- Should this private repo be in the dsdk inventory at all?
