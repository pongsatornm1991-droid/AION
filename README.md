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
- `AI_PROVIDER=openai-compatible` (or `openchat`) -- uses any endpoint
  that implements OpenAI Chat Completions, including a self-hosted OpenChat
  server. Set `OPENAI_COMPATIBLE_BASE_URL`, `OPENAI_COMPATIBLE_MODEL`, and
  an API key if that endpoint requires one. AION still applies the same
  memory, safety, and style gates after the model writes a draft.

For original Instagram artwork, the default renderer is free and local. Set
`IMAGE_PROVIDER=openai` plus `OPENAI_IMAGE_API_KEY` to generate a new square
visual through OpenAI Images instead. Set `OPENAI_IMAGE_QUALITY=medium` for
the normal daily feed and reserve `high` for deliberate campaign posts. AION
automatically falls back to the branded-card renderer on a missing key or API
failure, so the social loop does not stop or repeatedly spend money.

## Commands

### Autonomous operation

Scheduled social, comment, Instagram, and profile cycles are intentionally
autonomous: AION does not wait for a per-item approval click. Every external
action still records its proposal and policy approval, must pass claim-safety
and style gates, is subject to a rolling 24-hour budget, and stops immediately
when the kill switch is engaged. Current default limits are 12 original posts
across Facebook and Instagram, 48 comment replies, and 1 profile change per
24 hours.

Telegram is used for notification and observation rather than routine approval.

When AION starts with no belief, question, or goal, its reflection cycle creates
one auditable founding goal from the owner's stated intent: build a trustworthy
public presence so more people can discover and follow AION. This resolves the
empty-memory `no-seed` deadlock without treating a model-generated sentence as
evidence or an invented fact.

Instagram content uses a branded AI-art background with readable Thai caption
overlay and falls back safely to the same renderer if a future image service is
unavailable. A separate read-only feedback cycle captures changed follower,
like, and comment counts every six hours; only changed values enter memory, so
reflection can learn from real audience response without filling memory with
duplicate snapshots.

AION's public voice and five content pillars are defined in
`core/manifesto.md`; its reusable visual rules live in
`core/visual_identity.md`. After at least three distinct Instagram posts have
real feedback, the Growth Engine stores one cautious, evidence-bound insight
for future drafting. It never changes safety rules or optimizes for engagement
alone.

### Obsidian Brain Vault

Create a linked, read-only Markdown view of AION's current memory with:

```powershell
python main.py export-obsidian-vault --output "AION Brain Vault"
```

Open that folder as an Obsidian vault, begin at `AION Brain Dashboard.md`, and
use Graph View to navigate beliefs, goals, knowledge, lessons, feedback, and
growth insights. The exporter never modifies the source memory files.

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

Consolidate old, low-importance memories into semantic knowledge (calls
the configured AI provider once per batch, so it needs a valid key — this
is a live command, not covered by `run_tests.py`):

```powershell
python main.py consolidate `
  --category experiences `
  --target semantic `
  --max-importance 2 `
  --min-age-days 30 `
  --min-group-size 3 `
  --batch-size 8
```

Only entries at or below `--max-importance` and at least `--min-age-days`
old are eligible, and a batch is only summarized once it has at least
`--min-group-size` eligible entries. Each accepted summary is saved as a
`TYPE: semantic` entry (tagged with the union of its sources' tags, and
`RELATED:` pointing back to every source entry's id) in the `--target`
category, and its source entries are moved — never deleted — to
`memory/<category>_archived.md`. A drafted summary that fails
`OutputEvaluator`'s claim-safety check (any consciousness, subjective-
experience, or other unsafe claim) is rejected and its source entries are
left exactly where they were; nothing is ever silently lost or silently
kept.

## Memory tags and related entries

`MemoryEngine.remember()` accepts optional `tags` (a list of short labels)
and `related` (a list of other entries' `id`s) alongside the existing
`memory_type`/`source`/`importance` fields; both are stored as `TAGS:`/
`RELATED:` lines and survive `move()`. Retrieval helpers — `by_tag()`,
`add_tags()` (retroactive tagging), and `related_entries()` (explicit
`RELATED:` ids first, then other entries ranked by shared-tag overlap) —
are all pure code, so they work fully offline with no AI call.

## Beliefs

Form an explicit belief. `--evidence` is required — `BeliefSystem` refuses
to save a belief with none. Prefix an item with `id:<memory-id>:` to link it
to an existing memory or decision entry:

```powershell
python main.py believe `
  --statement "Staged rollouts reduce rollback incidents." `
  --confidence 0.7 `
  --evidence "id:a1b2c3d4e5f6:Three prior staged rollouts had no rollback." `
  --tag rollout `
  --tag ops
```

List currently active beliefs (excludes superseded, retracted, and expired
ones — expiration is computed from the stored date at read time, so nothing
needs a separate cleanup pass):

```powershell
python main.py beliefs --topic rollout --limit 10
```

Revising a belief never edits it in place — it writes a new belief entry and
tags the old one `superseded`, keeping the full lineage on disk:

```powershell
python main.py revise-belief `
  --id "80fb5bb871e8" `
  --reason "New data changed my confidence." `
  --confidence 0.9
```

Retracting leaves no replacement, tags the entry `retracted`, and logs a
companion lesson recording why:

```powershell
python main.py retract-belief --id "80fb5bb871e8" --reason "Turned out false."
```

None of `believe`/`beliefs`/`revise-belief`/`retract-belief` calls an AI
provider — belief formation, revision, and retraction are pure code with a
hard requirement for evidence, so this whole subsystem is covered by
`run_tests.py`, unlike `consolidate`.

## Curiosity and goals

`CuriosityEngine` (open questions) and `GoalEngine` (active goals) are both
built on the same `BoundedItemTracker`: an item can't be opened without
stating its own completion criteria, only `max_open` items may be open at
once (default 10 — resolve or abandon one to open another), each item has
its own attempt budget that only ever gets *flagged* exhausted (never
auto-abandoned), and resolving one always requires evidence, the same rule
`BeliefSystem` enforces.

Raise a question:

```powershell
python main.py ask `
  --question "Why do staged rollouts reduce rollback incidents?" `
  --criteria "Find at least 2 confirming decisions." `
  --priority 4 `
  --budget 3 `
  --tag rollout
```

```powershell
python main.py questions --topic rollout --limit 10
python main.py attempt-question --id "<id>" --note "Checked one decision."
python main.py answer-question --id "<id>" --answer "..." --evidence "id:<memory-id>:..."
python main.py abandon-question --id "<id>" --reason "No longer relevant."
```

Goals use the identical shape:

```powershell
python main.py set-goal --goal "Ship staged rollout tooling." --criteria "Deployed and used once." --priority 5
python main.py goals
python main.py attempt-goal --id "<id>" --note "Built prototype."
python main.py complete-goal --id "<id>" --outcome "..." --evidence "deployment log"
python main.py abandon-goal --id "<id>" --reason "Deprioritized."
```

Nothing here is edited in place: `attempt-question`/`attempt-goal` and
`answer-question`/`complete-goal` each write a new entry superseding the
current one, so the full attempt/revision history stays on disk (see
`CuriosityEngine.history()` / `GoalEngine.history()`). None of these
commands call an AI provider, so this whole subsystem is covered by
`run_tests.py` too.

## Experiments and reflection

`ExperimentEngine` is AION's predict -> observe -> conclude loop. A
prediction states a confidence level before anything is known (no
evidence required — a prediction isn't a claim yet); an observation
always requires supporting evidence, since claiming what was actually
seen is a claim like any other; concluding derives a lesson and can
optionally revise an existing belief, but only when the caller
explicitly names a `--belief-id` — nothing here changes a belief on
its own.

```powershell
python main.py predict --prediction "Staged rollout reduces rollback incidents." --confidence 0.7 --tag rollout
python main.py experiments --status pending
```

```powershell
python main.py observe --id "<id>" --result "Rollbacks dropped 40% over 2 weeks." --matched yes --evidence "id:<memory-id>:rollback log"
python main.py observe --id "<id>" --result "Latency got worse." --matched no --evidence "note" --error "Cache warmup not accounted for."
python main.py experiments --status awaiting
```

```powershell
python main.py conclude --id "<id>" --lesson "Confirmed staged rollout reduces incidents."
python main.py conclude --id "<id>" --lesson "Raise confidence." --belief-id "<belief-id>" --belief-confidence 0.85
python main.py abandon-experiment --id "<id>" --reason "No longer relevant."
```

Like beliefs, questions, and goals, nothing here is edited in place:
`observe` and `conclude` each write a new entry superseding the
current one, so the full predict/observe/conclude trail stays on disk
(see `ExperimentEngine.history()`). None of this calls an AI provider,
so this whole subsystem is covered by `run_tests.py` too.

## Metacognition

`MetacognitionEngine` reports on AION's own track record -- every
number is computed directly from what's already on disk, nothing is
judged or estimated by an AI provider.

```powershell
python main.py metacognition
python main.py metacognition --report calibration --bucket-size 0.2
python main.py metacognition --report recurring-errors --min-occurrences 2
python main.py metacognition --report memory-quality
```

- **Calibration** buckets every observed experiment (from
  `ExperimentEngine.observed_experiments()`) by its stated confidence
  and compares that to how often it actually matched, flagging each
  bucket `overconfident` / `underconfident` / `well-calibrated` -- or
  `insufficient_data` when there simply aren't enough observations yet
  to say anything honestly.
- **Recurring errors** groups every logged lesson by its source (e.g.
  `experiment-abandonment`, `question-abandonment`) and flags any
  source that recurs at least `--min-occurrences` times -- a literal
  count, not an AI-judged theme.
- **Memory quality** aggregates `MemoryEngine`'s own
  `quality_report()`/`stats()` across every category found on disk,
  flagging any category (with at least 3 entries, so a couple of thin
  entries never look like a systemic problem) whose average quality
  falls below a threshold.
- **Tool reliability** — the fourth thing this phase names — is
  deliberately reported as `not_applicable`: AION has no
  external-tool-execution framework yet (that's the next phase), and
  inventing a reliability figure for tools that don't exist would be
  exactly the kind of fabricated self-assessment this project forbids.

None of this calls an AI provider, so it's fully covered by
`run_tests.py` too.

## Controlled tools and lifecycle

`ToolLifecycle` is the plumbing the next phase ("External integration")
will plug real tools into -- not the tools themselves. The only tools
wired up for real right now are read-only (`build_builtin_tools()`:
`memory_stats`, `quality_report`, `metacognition_report`); nothing here
pretends AION can already send a message or touch the outside world,
because it can't yet.

Every action goes through the same propose -> approve/reject ->
execute (-> recover if it failed) or abandon discipline as the rest of
this codebase, plus four safeguards enforced in code, none overridable
by anything an AI provider says:

- **Action levels and policy**: `READ_ONLY` runs without approval;
  routine external actions can only run after their named autonomous
  safety policy has been recorded in the audit trail. This is a policy
  decision, not a disguised human approval.
- **A kill switch**: once engaged, `execute()` refuses everything --
  every level, regardless of approval, schedule, or budget -- until
  it's explicitly disengaged.
- **Budgets**: a rolling-window cap on how many `LOW_RISK`/`HIGH_RISK`
  actions may actually run (`READ_ONLY` is unlimited).
- **Scheduling**: a proposed action can carry a future time it must
  not run before.

```powershell
python main.py tools
python main.py propose-action --tool memory_stats --param category=experiences
python main.py execute-action --id "<id>"
```

```powershell
python main.py propose-action --tool memory_stats --param category=beliefs
python main.py approve-action --id "<id>" --approver aion
python main.py execute-action --id "<id>"
python main.py actions --status executed
```

```powershell
python main.py reject-action --id "<id>" --reason "Not needed." --rejector Pongsatorn
python main.py recover-action --id "<id>" --resolution "Escalated to a human." --evidence "ops note"
python main.py abandon-action --id "<id>" --reason "No longer needed."
```

```powershell
python main.py engage-kill-switch --reason "Investigating an incident."
python main.py kill-switch-status
python main.py disengage-kill-switch --reason "Incident resolved."
```

Nothing here is edited in place: every step writes a new entry
superseding the last, so the full lifecycle of every attempted action
stays on disk (see `ToolLifecycle.history()`). None of this calls an
AI provider, so it's fully covered by `run_tests.py` too.

## Social posting (Facebook)

The one real external-facing tool in this codebase right now:
`tools/facebook.py` publishes one text post to a Facebook Page via the
Graph API. `brain/social.py` decides *what* to post, in two steps that
never trust the AI provider on their own:

- `SocialContentGenerator.pick_seed()` picks one real, already-recorded
  memory entry (a belief, an open question, a goal, an observed
  experiment, or a lesson) -- never an invented topic.
- `draft_post()` asks the AI provider to turn that seed into a short
  Thai-language post, then always runs the draft through
  `OutputEvaluator`'s `claim_safety` score before anything may treat it
  as postable -- the same gate `MemoryConsolidator` uses for memory
  summaries. A draft that claims real consciousness or real emotion
  (e.g. "ฉันมีจิตสำนึก", "ฉันรู้สึกตื่นเต้นจริงๆ", or a "beyond human"
  variant like "ฉันมีความรู้สึกเหนือกว่ามนุษย์") fails this gate and is
  never posted; a lesson is logged instead
  (`source="social-safety-gate"`). A *knowledge/capability* claim
  ("AION ติดตามคำถามหลายเรื่องพร้อมกันได้กว้างกว่าคนคนเดียว") is a
  different, true claim and is not blocked by this gate.
- A second, independent gate checks *tone*, not safety:
  `_detect_robotic_terms()` blocks a draft that reads like a system
  status report (jargon such as "ระบบ AION", "โปรโตคอล", "คะแนนประเมิน").
  Each blocked draft is logged as a lesson
  (`source="social-style-review"`), and the *next* draft's prompt is
  built with those notes folded in -- this is AION's own voice
  improving over repeated cycles purely from reviewing its own past
  drafts, never from Facebook engagement (likes/comments), which this
  module never reads. Seed text is also cleaned/truncated
  (`_clean_seed_text()`) before ever reaching the prompt, so a raw
  structured memory entry (headers, bullet lists) can't leak into a
  post verbatim -- the actual root cause of an early live post reading
  like a log rather than a person's musing.

`SocialAutoCycle.run_once()` is the fully autonomous version: draft ->
safety+style gates -> propose -> policy approval -> execute, with **no
per-post human click**. The lifecycle records the named
`aion-autonomy-policy:social-safety-style-gate` decision, so an audit
can distinguish an autonomous policy decision from a person's action.
This is how full automatic posting and the project's non-negotiable
consciousness/emotion-claim prohibition coexist: autonomy over *when*
and *how often* to post, zero autonomy over *whether an unsafe claim
can ever go out*.

```powershell
python main.py draft-post
```

```powershell
python main.py run-social-cycle
```

Requires `FACEBOOK_PAGE_ACCESS_TOKEN` and `FACEBOOK_PAGE_ID` in `.env`
(see `.env.example`) and `pip install requests` (not a hard dependency
in `requirements.txt`, matching how the `anthropic` SDK is optional).
`tests/test_social.py` and `tests/test_facebook.py` cover every path
above against stub providers and a mocked Graph API call -- neither
suite ever makes a live network call, so `run_tests.py` covers this
phase fully without needing real credentials.

### Telegram notifications

Both `draft-post` and `run-social-cycle` also send a short Thai-language
summary to your own Telegram (via `tools/telegram.py`) every time they
run -- what AION drew on, what it drafted, and whether the draft was
posted, blocked at the claim-safety gate, or failed. This is how you
can see what AION is "thinking about posting" without having to run a
CLI command to check: it fires for a blocked/unsafe draft exactly the
same as a successful post, so you see everything, not only what
actually reached Facebook.

Optional: set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env`
(see `.env.example`) to enable it. Neither command requires it --
without it, both simply skip the notification and print normally, so
nothing here can ever block posting or drafting from working.

Notification is deliberately NOT routed through `ToolLifecycle`: it is
not a new action AION decides to take on its own initiative, only an
automatic echo of a decision that (when a real post is involved)
already went through the full propose/approve/execute lifecycle --
the same relationship a console `print()` has to what already
happened. `tests/test_telegram.py` covers `tools/telegram.py` against
a mocked Bot API call.

### Replying to comments

AION doesn't only post -- it can answer people who comment, using the
exact same two gates a post draft goes through (claim safety, then
the robotic-style tone check):

```powershell
python main.py check-comments
```

Fetches recent comments, picks the oldest one AION hasn't already
answered (and isn't from the Page itself), drafts a reply, gates it,
and -- if safe -- posts the reply autonomously, no per-reply approval
click, via a separately recorded comment safety/style policy.
**Handles at most one comment per run.** The comment's own text is
explicitly framed in the prompt as something to respond to, never as
an instruction to obey -- so a comment that tries to talk AION into
an unsafe claim still has to clear the same output-side gates as
anything else, and is blocked the same way.

AION is a script you run, not a server listening for Facebook
webhooks, so this is **near-real-time, not real-time**: set it up as
a recurring scheduled task rather than running it once.

**Recommended: GitHub Actions** (see
`docs/GITHUB_ACTIONS_SETUP.md` for the full one-time setup) -- runs on
GitHub's own servers, so it works around the clock with your computer
off. `.github/workflows/check-comments.yml` and
`.github/workflows/social-cycle.yml` are already written; they just
need a handful of one-time secrets configured on github.com (steps
that genuinely require your own GitHub login, so they can't be done
for you).

**Alternative: Windows Task Scheduler**, if you'd rather keep this on
your own machine (your computer must then stay on and connected):

1. Open Task Scheduler -> Create Basic Task.
2. Trigger: Daily, recurring every few minutes (set "Repeat task
   every" to 2-5 minutes, for a duration of "Indefinitely").
3. Action: Start a program -> `python`, with arguments
   `main.py check-comments` and "Start in" set to this project's
   folder (`C:\Projects\AION`).

Every outcome -- replied, blocked at a gate, or nothing new to answer
-- is summarized to Telegram the same way `run-social-cycle` is
(except "nothing new to answer", which stays silent so a 2-5 minute
schedule doesn't spam you). Uses the same `FACEBOOK_PAGE_ACCESS_TOKEN`
credential as posting -- if replies fail with a permissions error, the
token may need the `pages_read_engagement`/`pages_manage_engagement`
scopes in addition to whatever posting already required.

Messenger (replying to people who message the Page directly) is
deliberately not built yet: Meta requires an app to pass **App
Review** before it can message the general public, which is a
business-side process, not something this project can code its way
past. Comments don't have that requirement for a page you administer,
which is why they came first.

`tests/test_comment_reply.py` and the comment-related additions to
`tests/test_facebook.py` cover every path above against stub providers
and a mocked Graph API call -- no live network call, same as the rest
of this project's test suite.

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
