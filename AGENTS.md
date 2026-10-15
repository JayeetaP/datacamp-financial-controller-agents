# Repository instructions

## Purpose

This is a synthetic, educational financial-close agent. Code owns calculations, current evidence
owns facts, the model explains, and a human owns every accounting decision.

## Invariants

- Never add real financial, customer, employee, or credential data.
- Do not let model output replace deterministic calculations or data-quality gates.
- Historical knowledge may guide a search but cannot prove a current-period claim.
- The runtime may create an unposted draft adjustment; it may never post or approve one.
- Preserve separate data-admission, resolution, route, and human-decision statuses.
- Add or change behavior through a failing test or eval first.

## Commands

- `make data`: regenerate and validate synthetic data.
- `make test`: run deterministic and replay-safe tests.
- `make eval-replay`: run network-free behavioral evals.
- `make verify`: lint, test, and replay evals.
- `make demo-1`: run the live annual-software investigation through signed-in Codex.

## Skills

- Use `$implementation-strategy` before changing runtime boundaries or public contracts.
- Use `$eval-case-authoring` for a new behavior, failure, or regression.
- Use `$code-change-verification` before handing off a code change.
- Use `$demo-rehearsal` when preparing or validating the live session.

Read the relevant file under `specs/` for requirement changes. Keep `AGENTS.md` concise; put
workflow detail in skills and domain rules in `controls/`.
