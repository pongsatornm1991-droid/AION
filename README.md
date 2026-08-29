# AION

AION is a Python prototype for a persistent cognitive loop:

1. build context from identity and memory;
2. generate and evaluate a self-reflection;
3. correct low-quality output; and
4. store experiences and lessons for later cycles.

It also provides a structured decision mode that separates facts,
inferences, and uncertainties before auditing a proposed conclusion.

## Setup

Install the dependencies and create a `.env` file from `.env.example`.
Set `GEMINI_API_KEY` before using reflection mode.

## Providers

`reflect` uses whichever provider `AI_PROVIDER` in `.env` names (default: `gemini`). `decide`/`history`/`verify` never touch a provider at all, so neither provider's SDK is required to use them.

- `AI_PROVIDER=gemini` (default) -- needs `GEMINI_API_KEY`. Already
  covered by `requirements.txt`.
- `AI_PROVIDER=claude` -- needs `ANTHROPIC_API_KEY` in `.env`, plus
  `pip install anthropic` (not in `requirements.txt` by default, since
  most setups only need one provider). Check the current model id at
  https://docs.claude.com/en/docs/about-claude/models before relying on
  the `ANTHROPIC_MODEL` default in `.env.example` -- model ids are
  periodically retired.

## Commands

Generate a reflection:

```powershell
python main.py reflect
```

Run a decision and audit without calling Gemini:

```powershell
python main.py decide `
  --question "Should the rollout proceed?" `
  --conclusion "Proceed with the limited rollout." `
  --option "Proceed" `
  --option "Delay" `
  --fact "The test plan covers the intended scope." `
  --inference "A limited rollout is appropriate." `
  --uncertainty "Demand may vary after release."
```

Each `--fact`, `--inference`, `--uncertainty`, and `--option` argument can
be repeated. Only a decision with `LOW` audit risk and no audit flags is
stored as `ACCEPTED` in `memory/decisions_accepted.md`. All other results are
stored as `NEEDS_VERIFICATION` in
`memory/decisions_pending_verification.md`. Use `--no-save` to preview the
report without changing memory.

View decision history:

```powershell
python main.py history --status all --limit 10
```

Re-audit a pending decision with new facts. Use the `ID` displayed by
`history` (a stable id, not the timestamp — two decisions can be recorded
in the same second); promotion occurs only if the new audit is `LOW` risk
and has no flags.

```powershell
python main.py verify `
  --id "a1b2c3d4e5f6" `
  --fact "The rollback procedure is documented." `
  --fact "The release owner is assigned."
```

## Offline verification

Single deterministic command (unit tests + both offline benchmarks; never
calls Gemini, so it needs no API key and costs no quota):

```powershell
python run_tests.py
```

Exits non-zero if unit tests fail or either benchmark drops below 100%.
The individual pieces can still be run on their own:

```powershell
python -m unittest discover -s tests -p "test_*.py"
python tests\offline_benchmark.py
python tests\correction_benchmark.py
```

`tests\run_benchmark.py` is separate: it calls the live Gemini API, is not
deterministic, and is excluded from `run_tests.py` on purpose.
