# Active AI work claim

This is a small, overwrite-in-place coordination board for Codex and Claude.
It prevents concurrent sessions from editing the same release path. It is not
a historical log: replace this block when taking a task, and set status to
`clear` when handing off. A claim expires at its stated time so a crashed
session never blocks the company indefinitely.

Status: in-progress
Owner: Claude Code
Started: 2026-09-22 18:22 UTC
Lease expires: 2026-09-22 21:22 UTC
Scope: Owner made a deliberate creative-direction pivot: drop the
Thai-rooted identity pillar entirely (core/manifesto.md,
core/creator_bible.md, core/visual_identity.md all currently mandate it),
reposition toward a globally-appealing, highly memorable style with
kurzgesagt (youtube.com/@kurzgesagt) as the explicit reference point, and
strengthen content quality so the exact hollow-content failure found
earlier today (octopus episode: followed the narrative template shape but
never actually explained its own topic) can't recur. Owner said "develop
it right now."
Plan: (1) rewrite the Thai-rooted sections of the three core/*.md identity
docs into a global-first positioning, keeping AION's own already-built,
distinctive visual identity (translucent cyan being, colour-coded
computational states) since that IS a real asset, just no longer
Thai-anchored; (2) add a concrete, testable requirement to
StoryEpisodeStager's scene template -- a real "perspective-shift" ending
beat and an explicit requirement that the mechanism/answer to the
episode's own wonder_hook must appear in the narration -- closing the
exact gap that produced the octopus incident, not just a style tweak;
(3) full test suite green; (4) leave content/creator_series/*.json files
alone -- this changes the template for future episodes, not a retroactive
rewrite of existing ones.
Handoff: if this board still says in-progress after 2026-09-22 21:22 UTC,
the lease has expired -- check git log / this session's own log entry (if
any) for how far it got before picking it up. Unrelated, still open:
public/aion-release-readiness.json still shows aion-wonders-005-venus-
flytrap-counts as available (a real, already-published episode) --
root-caused to the private aion-memory-data repo's own queue record
likely never having had youtube.video_id written back after that
publish, not the counting-logic bug fixed yesterday. Needs a
reconcile-youtube-creator run from a context with real access to that
private repo (this local sandbox's memory/ symlink already shows it
correctly, which is why local checks didn't catch this).
